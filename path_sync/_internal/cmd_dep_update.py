from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import typer
from git import Repo

from path_sync._internal import cmd_options, git_ops, verify
from path_sync._internal.auto_merge import PRRef, handle_auto_merge
from path_sync._internal.log_capture import capture_log
from path_sync._internal.models import Destination, OnFailStrategy, find_repo_root
from path_sync._internal.models_dep import (
    DepConfig,
    UpdateEntry,
    resolve_dep_config_path,
)
from path_sync._internal.repo_utils import ensure_repo, resolve_repo_path
from path_sync._internal.typer_app import app
from path_sync._internal.verify import StepFailure, VerifyStatus
from path_sync._internal.yaml_utils import load_yaml_model

logger = logging.getLogger(__name__)


class Status(StrEnum):
    PASSED = "passed"
    SKIPPED = "skipped"
    WARN = "warn"
    NO_CHANGES = "no_changes"
    FAILED = "failed"

    @classmethod
    def from_verify_status(cls, vs: VerifyStatus) -> Status:
        return cls(vs.value)


@dataclass
class RepoResult:
    dest: Destination
    repo_path: Path
    status: Status
    failures: list[StepFailure] = field(default_factory=list)
    log_content: str = ""


@dataclass
class DepUpdateOptions:
    dry_run: bool = False
    skip_verify: bool = False
    no_wait: bool = False
    no_auto_merge: bool = False
    reviewers: list[str] | None = None
    assignees: list[str] | None = None


@app.command()
def dep_update(
    name: str = typer.Option(..., "-n", "--name", help="Config name"),
    dest_filter: str = typer.Option("", "-d", "--dest", help="Filter destinations (comma-separated)"),
    work_dir: str = typer.Option("", "--work-dir", help="Clone repos here (overrides dest_path_relative)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without creating PRs"),
    skip_verify: bool = typer.Option(False, "--skip-verify", help="Skip verification steps"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Enable auto-merge but skip polling for merge completion"),
    no_auto_merge: bool = typer.Option(False, "--no-auto-merge", help="Skip auto-merge even when configured"),
    src_root_opt: str = typer.Option("", "--src-root", help="Source repo root"),
    pr_reviewers: str = cmd_options.pr_reviewers_option(),
    pr_assignees: str = cmd_options.pr_assignees_option(),
) -> None:
    """Run dependency updates across repositories."""
    src_root = Path(src_root_opt) if src_root_opt else find_repo_root(Path.cwd())
    config_path = resolve_dep_config_path(src_root, name)
    if not config_path.exists():
        logger.error(f"Config not found: {config_path}")
        raise typer.Exit(1)

    config = load_yaml_model(config_path, DepConfig)
    destinations = config.load_destinations(src_root)

    if dest_filter:
        filter_names = [n.strip() for n in dest_filter.split(",")]
        destinations = [d for d in destinations if d.name in filter_names]

    opts = DepUpdateOptions(
        dry_run=dry_run,
        skip_verify=skip_verify,
        no_wait=no_wait,
        no_auto_merge=no_auto_merge,
        reviewers=cmd_options.split_csv(pr_reviewers) or config.pr.reviewers,
        assignees=cmd_options.split_csv(pr_assignees) or config.pr.assignees,
    )

    results = _update_and_validate(config, destinations, src_root, work_dir, opts)
    pr_refs = _create_prs(config, results, opts)

    if config.auto_merge and pr_refs and not opts.no_auto_merge:
        handle_auto_merge(pr_refs, config.auto_merge, no_wait=opts.no_wait)

    if any(r.status == Status.SKIPPED for r in results):
        raise typer.Exit(1)


def _update_and_validate(
    config: DepConfig,
    destinations: list[Destination],
    src_root: Path,
    work_dir: str,
    opts: DepUpdateOptions,
) -> list[RepoResult]:
    results: list[RepoResult] = []

    for dest in destinations:
        result = _process_single_repo(config, dest, src_root, work_dir, opts)

        if result.status == Status.FAILED:
            logger.error(f"{dest.name}: Verification failed, stopping")
            raise typer.Exit(1)

        if result.status == Status.NO_CHANGES:
            if (
                not opts.dry_run
                and not config.keep_pr_on_no_changes
                and git_ops.has_open_pr(result.repo_path, config.pr.branch)
            ):
                git_ops.close_pr(result.repo_path, config.pr.branch, "Closing: no dependency changes needed")
            continue

        results.append(result)

    return results


def _process_single_repo(
    config: DepConfig,
    dest: Destination,
    src_root: Path,
    work_dir: str,
    opts: DepUpdateOptions,
) -> RepoResult:
    with capture_log(dest.name) as read_log:
        result = _process_single_repo_inner(config, dest, src_root, work_dir, opts)
        result.log_content = read_log()
    return result


def _process_single_repo_inner(
    config: DepConfig,
    dest: Destination,
    src_root: Path,
    work_dir: str,
    opts: DepUpdateOptions,
) -> RepoResult:
    logger.info(f"Processing {dest.name}...")
    repo_path = resolve_repo_path(dest, src_root, work_dir)
    repo = ensure_repo(dest, repo_path)
    git_ops.prepare_copy_branch(repo, dest.default_branch, config.pr.branch, from_default=True)

    if failure := _run_updates(config.updates, repo_path):
        logger.warning(f"{dest.name}: Update failed with exit code {failure.returncode}")
        return RepoResult(dest=dest, repo_path=repo_path, status=Status.SKIPPED, failures=[failure])

    if not git_ops.has_changes(repo):
        logger.info(f"{dest.name}: No changes, skipping")
        return RepoResult(dest=dest, repo_path=repo_path, status=Status.NO_CHANGES)

    git_ops.commit_changes(repo, config.pr.title)

    if opts.skip_verify:
        return RepoResult(dest=dest, repo_path=repo_path, status=Status.PASSED)

    return _verify_repo(repo, repo_path, config.verify, dest)


def _run_updates(updates: list[UpdateEntry], repo_path: Path) -> StepFailure | None:
    try:
        for update in updates:
            verify.run_command(update.command, repo_path / update.workdir)
        return None
    except subprocess.CalledProcessError as e:
        return StepFailure(step=e.cmd, returncode=e.returncode, on_fail=OnFailStrategy.SKIP)


def _verify_repo(repo: Repo, repo_path: Path, fallback_verify: verify.VerifyConfig, dest: Destination) -> RepoResult:
    effective_verify = dest.resolve_verify(fallback_verify)
    result = verify.run_verify_steps(repo, repo_path, effective_verify)
    status = Status.from_verify_status(result.status)
    return RepoResult(dest=dest, repo_path=repo_path, status=status, failures=result.failures)


def _create_prs(config: DepConfig, results: list[RepoResult], opts: DepUpdateOptions) -> list[PRRef]:
    pr_refs: list[PRRef] = []
    for result in results:
        if result.status == Status.SKIPPED:
            continue

        if opts.dry_run:
            logger.info(f"[DRY RUN] Would create PR for {result.dest.name}")
            continue

        repo = git_ops.get_repo(result.repo_path)
        body = _build_pr_body(result.log_content, result.failures)

        if not git_ops.push_branch(repo, config.pr.branch, force=True):
            git_ops.update_pr_body(result.repo_path, config.pr.branch, body)
            continue

        pr_url = git_ops.create_or_update_pr(
            result.repo_path,
            config.pr.branch,
            config.pr.title,
            body,
            config.pr.labels or None,
            reviewers=opts.reviewers,
            assignees=opts.assignees,
        )
        logger.info(f"{result.dest.name}: PR created/updated")
        branch_or_url = pr_url or config.pr.branch
        pr_refs.append(PRRef(dest_name=result.dest.name, repo_path=result.repo_path, branch_or_url=branch_or_url))
    return pr_refs


def _build_pr_body(log_content: str, failures: list[StepFailure]) -> str:
    body = "Automated dependency update."

    if log_content.strip():
        body += "\n\n## Command Output\n\n```\n" + log_content.strip() + "\n```"

    if failures:
        body += "\n\n---\n## Verification Issues\n"
        for f in failures:
            body += f"\n- `{f.step}` failed (exit code {f.returncode}, strategy: {f.on_fail})"

    return body
