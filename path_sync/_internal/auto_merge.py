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


def enable_auto_merge(repo_path: Path, pr_ref: str, config: AutoMergeConfig) -> None:
    cmd = ["gh", "pr", "merge", "--auto", f"--{config.method}", pr_ref]
    if config.delete_branch:
        cmd.append("--delete-branch")
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(f"Auto-merge enable failed for {pr_ref}: {result.stderr.strip()}")
    else:
        logger.info(f"Enabled auto-merge ({config.method}) for {pr_ref}")


def get_pr_checks(repo_path: Path, pr_ref: str) -> list[CheckRun]:
    cmd = ["gh", "pr", "checks", pr_ref, "--json", "name,state"]
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(f"Failed to get checks for {pr_ref}: {result.stderr.strip()}")
        return []
    return [CheckRun.model_validate(c) for c in json.loads(result.stdout)]


def get_pr_state(repo_path: Path, pr_ref: str) -> PRState:
    cmd = ["gh", "pr", "view", pr_ref, "--json", "state", "-q", ".state"]
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(f"Failed to get PR state for {pr_ref}: {result.stderr.strip()}")
        return PRState.OPEN
    return PRState(result.stdout.strip())


def get_pr_url(repo_path: Path, pr_ref: str) -> str:
    cmd = ["gh", "pr", "view", pr_ref, "--json", "url", "-q", ".url"]
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
    if result.returncode != 0:
        return pr_ref
    return result.stdout.strip() or pr_ref


def wait_for_merge(repo_path: Path, pr_ref: str, config: AutoMergeConfig, dest_name: str = "") -> PRMergeResult:
    pr_url = get_pr_url(repo_path, pr_ref)
    deadline = time.monotonic() + config.timeout_seconds

    while time.monotonic() < deadline:
        state = get_pr_state(repo_path, pr_ref)
        if state == PRState.MERGED:
            return PRMergeResult(dest_name=dest_name, pr_url=pr_url, branch=pr_ref, state=PRState.MERGED)
        if state == PRState.CLOSED:
            checks = get_pr_checks(repo_path, pr_ref)
            return PRMergeResult(dest_name=dest_name, pr_url=pr_url, branch=pr_ref, state=PRState.CLOSED, checks=checks)
        time.sleep(config.poll_interval_seconds)

    checks = get_pr_checks(repo_path, pr_ref)
    logger.warning(f"Timeout waiting for {pr_ref} after {config.timeout_seconds}s")
    return PRMergeResult(dest_name=dest_name, pr_url=pr_url, branch=pr_ref, state=PRState.OPEN, checks=checks)


def handle_auto_merge(
    pr_refs: list[PRRef],
    config: AutoMergeConfig,
    no_wait: bool = False,
) -> list[PRMergeResult]:
    if not pr_refs:
        return []

    pending_refs: list[PRRef] = []
    for ref in pr_refs:
        state = get_pr_state(ref.repo_path, ref.branch_or_url)
        if state == PRState.MERGED:
            logger.info(f"{ref.dest_name}: already merged")
            continue
        enable_auto_merge(ref.repo_path, ref.branch_or_url, config)
        pending_refs.append(ref)

    if no_wait:
        logger.info("--no-wait: skipping merge polling")
        return []

    results: list[PRMergeResult] = []
    for ref in pending_refs:
        logger.info(f"Waiting for {ref.dest_name} to merge...")
        result = wait_for_merge(ref.repo_path, ref.branch_or_url, config, dest_name=ref.dest_name)
        results.append(result)

    _log_summary(results)
    return results


def _log_summary(results: list[PRMergeResult]) -> None:
    if not results:
        return
    max_name = max(len(r.dest_name) for r in results)
    header = f"{'Repo':<{max_name}}  State    Failed Checks"
    logger.info(header)
    logger.info("-" * len(header))
    for r in results:
        failed = ", ".join(c.name for c in r.failed_checks)
        logger.info(f"{r.dest_name:<{max_name}}  {r.state:<8} {failed}")
