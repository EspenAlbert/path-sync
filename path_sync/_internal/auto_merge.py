from __future__ import annotations

import json
import logging
import subprocess
import time
from enum import StrEnum
from pathlib import Path
from typing import NamedTuple

from pydantic import BaseModel, Field

from path_sync._internal.models import AutoMergeConfig

logger = logging.getLogger(__name__)


class PRState(StrEnum):
    MERGED = "MERGED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class AutoMergeEnableResult(StrEnum):
    OK = "ok"
    DRAFT = "draft"
    FAILED = "failed"


NO_BRANCH_CHECKS_GRACE_SECONDS = 30


FAILED_CHECK_STATES: frozenset[str] = frozenset(
    {
        "FAILURE",
        "ERROR",
        "TIMED_OUT",
        "STARTUP_FAILURE",
        "STALE",
        "ACTION_REQUIRED",
    }
)

COMPLETED_CHECK_STATES: frozenset[str] = frozenset(FAILED_CHECK_STATES | {"SUCCESS", "NEUTRAL", "SKIPPED", "CANCELLED"})


class CheckRun(BaseModel):
    name: str
    state: str
    workflow: str = ""
    link: str = ""

    @property
    def failed(self) -> bool:
        return self.state in FAILED_CHECK_STATES

    @property
    def pending(self) -> bool:
        return self.state not in COMPLETED_CHECK_STATES


class PRRef(NamedTuple):
    dest_name: str
    repo_path: Path
    branch_or_url: str


class PRMergeResult(BaseModel):
    dest_name: str
    pr_url: str
    branch: str
    state: PRState
    checks: list[CheckRun] = Field(default_factory=list)

    @property
    def failed_checks(self) -> list[CheckRun]:
        return [c for c in self.checks if c.failed]

    @property
    def pending_checks(self) -> list[CheckRun]:
        return [c for c in self.checks if c.pending]


def _is_draft_error(stderr: str) -> bool:
    return "draft" in stderr.lower()


def enable_auto_merge(
    repo_path: Path,
    pr_ref: str,
    config: AutoMergeConfig,
    dest_name: str = "",
) -> AutoMergeEnableResult:
    label = dest_name or pr_ref
    cmd = ["gh", "pr", "merge", "--auto", f"--{config.method}", pr_ref]
    if config.delete_branch:
        cmd.append("--delete-branch")
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if _is_draft_error(stderr):
            logger.warning(f"  {label}: auto-merge enable failed: {stderr}")
            return AutoMergeEnableResult.DRAFT
        logger.warning(f"  {label}: auto-merge enable failed: {stderr}")
        return AutoMergeEnableResult.FAILED
    logger.info(f"  {label}: enabled auto-merge ({config.method})")
    return AutoMergeEnableResult.OK


def mark_pr_ready(repo_path: Path, pr_ref: str, dest_name: str = "") -> bool:
    label = dest_name or pr_ref
    result = subprocess.run(
        ["gh", "pr", "ready", pr_ref],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.warning(f"  {label}: mark ready failed: {result.stderr.strip()}")
        return False
    logger.info(f"  {label}: marked ready for review")
    return True


def get_pr_checks(repo_path: Path, pr_ref: str) -> list[CheckRun]:
    cmd = ["gh", "pr", "checks", pr_ref, "--json", "name,state,workflow,link"]
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.warning(f"Failed to get checks for {pr_ref}: {result.stderr.strip()}")
        return []
    return [CheckRun.model_validate(c) for c in json.loads(result.stdout)]


def get_pr_state(repo_path: Path, pr_ref: str) -> PRState:
    cmd = ["gh", "pr", "view", pr_ref, "--json", "state", "-q", ".state"]
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.warning(f"Failed to get PR state for {pr_ref}: {result.stderr.strip()}")
        return PRState.OPEN
    return PRState(result.stdout.strip())


def get_pr_merge_commit(repo_path: Path, pr_ref: str) -> str:
    cmd = ["gh", "pr", "view", pr_ref, "--json", "mergeCommit", "-q", ".mergeCommit.oid"]
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.warning(f"Failed to get merge commit for {pr_ref}: {result.stderr.strip()}")
        return ""
    return result.stdout.strip()


def get_remote_branch_sha(repo_path: Path, branch: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", f"origin/{branch}"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _fetch_origin(repo_path: Path) -> None:
    subprocess.run(
        ["git", "fetch", "origin"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )


def _repo_slug(repo_path: Path) -> str:
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.warning(f"Failed to resolve repo slug: {result.stderr.strip()}")
        return ""
    return result.stdout.strip()


def _check_run_state(status: str, conclusion: str | None) -> str:
    if status != "completed":
        return status.upper()
    return (conclusion or "success").upper()


def get_commit_checks(repo_path: Path, sha: str) -> list[CheckRun]:
    slug = _repo_slug(repo_path)
    if not slug:
        return []
    cmd = ["gh", "api", f"repos/{slug}/commits/{sha}/check-runs"]
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.warning(f"Failed to get checks for {sha}: {result.stderr.strip()}")
        return []
    check_runs = json.loads(result.stdout).get("check_runs", [])
    return [
        CheckRun(
            name=check_run["name"],
            state=_check_run_state(check_run.get("status", ""), check_run.get("conclusion")),
        )
        for check_run in check_runs
        if check_run.get("name")
    ]


def wait_for_branch_checks(
    repo_path: Path,
    branch: str,
    config: AutoMergeConfig,
    dest_name: str = "",
    merge_sha: str = "",
) -> list[CheckRun]:
    label = dest_name or branch
    deadline = time.monotonic() + config.timeout_seconds
    grace_deadline = time.monotonic() + NO_BRANCH_CHECKS_GRACE_SECONDS
    poll_count = 0
    sha_label = merge_sha[:7] if merge_sha else branch

    while time.monotonic() < deadline:
        if merge_sha:
            sha = merge_sha
        else:
            _fetch_origin(repo_path)
            sha = get_remote_branch_sha(repo_path, branch)
            if not sha:
                logger.warning(f"{label}: could not resolve origin/{branch}")
                break

        checks = get_commit_checks(repo_path, sha)
        if checks:
            pending = [c for c in checks if c.pending]
            failed = [c for c in checks if c.failed]
            if not pending:
                if failed:
                    failed_names = ", ".join(c.name for c in failed)
                    logger.warning(f"{label}: {len(failed)} check(s) failed on {sha_label}: {failed_names}")
                else:
                    logger.info(f"{label}: all {len(checks)} check(s) passed on {sha_label}")
                return checks

            poll_count += 1
            elapsed = int(config.timeout_seconds - (deadline - time.monotonic()))
            pending_names = ", ".join(c.name for c in pending)
            logger.info(
                f"{label}: waiting for {sha_label} CI (poll #{poll_count}, {elapsed}s, pending: {pending_names})"
            )
        elif time.monotonic() >= grace_deadline:
            logger.info(f"{label}: no CI checks found on {sha_label}, proceeding")
            return []
        else:
            poll_count += 1
            elapsed = int(config.timeout_seconds - (deadline - time.monotonic()))
            logger.info(f"{label}: waiting for {sha_label} CI to start (poll #{poll_count}, {elapsed}s)")

        time.sleep(config.poll_interval_seconds)

    sha = merge_sha or get_remote_branch_sha(repo_path, branch)
    checks = get_commit_checks(repo_path, sha) if sha else []
    logger.warning(f"Timeout waiting for {label} {sha_label} CI after {config.timeout_seconds}s")
    return checks


def get_pr_url(repo_path: Path, pr_ref: str) -> str:
    cmd = ["gh", "pr", "view", pr_ref, "--json", "url", "-q", ".url"]
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.warning(f"Failed to get PR URL for {pr_ref}: {result.stderr.strip()}")
        return pr_ref
    return result.stdout.strip() or pr_ref


def wait_for_merge(repo_path: Path, pr_ref: str, config: AutoMergeConfig, dest_name: str = "") -> PRMergeResult:
    pr_url = get_pr_url(repo_path, pr_ref)
    deadline = time.monotonic() + config.timeout_seconds
    label = dest_name or pr_ref
    poll_count = 0

    while time.monotonic() < deadline:
        state = get_pr_state(repo_path, pr_ref)
        if state == PRState.MERGED:
            logger.info(f"{label}: merged ({pr_url})")
            return PRMergeResult(dest_name=dest_name, pr_url=pr_url, branch=pr_ref, state=PRState.MERGED)
        if state == PRState.CLOSED:
            checks = get_pr_checks(repo_path, pr_ref)
            logger.warning(f"{label}: PR closed without merging ({pr_url})")
            return PRMergeResult(dest_name=dest_name, pr_url=pr_url, branch=pr_ref, state=PRState.CLOSED, checks=checks)
        poll_count += 1
        elapsed = int(config.timeout_seconds - (deadline - time.monotonic()))
        logger.info(f"{label}: still open (poll #{poll_count}, {elapsed}s elapsed)")
        time.sleep(config.poll_interval_seconds)

    checks = get_pr_checks(repo_path, pr_ref)
    logger.warning(f"Timeout waiting for {label} after {config.timeout_seconds}s ({pr_url})")
    return PRMergeResult(dest_name=dest_name, pr_url=pr_url, branch=pr_ref, state=PRState.OPEN, checks=checks)


SEPARATOR_WIDTH = 40


def handle_auto_merge(
    pr_refs: list[PRRef],
    config: AutoMergeConfig,
    no_wait: bool = False,
) -> list[PRMergeResult]:
    if not pr_refs:
        return []

    line = "─" * SEPARATOR_WIDTH
    logger.info(f"\n{line}")
    logger.info(" Auto-merge")
    logger.info(line)

    pending_refs: list[PRRef] = []
    for ref in pr_refs:
        state = get_pr_state(ref.repo_path, ref.branch_or_url)
        if state == PRState.MERGED:
            logger.info(f"  {ref.dest_name}: already merged")
            continue
        enable_auto_merge(ref.repo_path, ref.branch_or_url, config, dest_name=ref.dest_name)
        pending_refs.append(ref)

    if no_wait:
        logger.info("  --no-wait: skipping merge polling")
        return []

    results: list[PRMergeResult] = []
    for ref in pending_refs:
        logger.info(f"  Waiting for {ref.dest_name} to merge...")
        result = wait_for_merge(ref.repo_path, ref.branch_or_url, config, dest_name=ref.dest_name)
        results.append(result)

    _log_summary(results)
    return results


def _log_summary(results: list[PRMergeResult]) -> None:
    if not results:
        return
    max_name = max(len(r.dest_name) for r in results)
    max_url = max(len(r.pr_url) for r in results)
    header = f"{'Repo':<{max_name}}  {'PR':<{max_url}}  State    Failed Checks"
    logger.info(header)
    logger.info("-" * len(header))
    for r in results:
        failed = ", ".join(c.name for c in r.failed_checks)
        logger.info(f"{r.dest_name:<{max_name}}  {r.pr_url:<{max_url}}  {r.state:<8} {failed}")
