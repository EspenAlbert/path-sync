from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import typer

from path_sync._internal import git_ops
from path_sync._internal.models import Destination, find_repo_root
from path_sync._internal.models_dep import (
    DepConfig,
    OnFailStrategy,
    UpdateEntry,
    VerifyConfig,
    resolve_dep_config_path,
)
from path_sync._internal.typer_app import app
from path_sync._internal.yaml_utils import load_yaml_model

logger = logging.getLogger(__name__)

MAX_STDERR_LINES = 20


class Status(StrEnum):
    PASSED = "passed"
    SKIPPED = "skipped"
    WARN = "warn"
    NO_CHANGES = "no_changes"
    FAILED = "failed"


@dataclass
class StepFailure:
    step: str
    returncode: int
    stderr: str
    on_fail: OnFailStrategy

    @classmethod
    def from_error(cls, step: str, e: subprocess.CalledProcessError, on_fail: OnFailStrategy) -> StepFailure:
        stderr = _truncate_stderr(e.stderr or "", MAX_STDERR_LINES)
        return cls(step=step, returncode=e.returncode, stderr=stderr, on_fail=on_fail)


@dataclass
class RepoResult:
    dest: Destination
    repo_path: Path
    status: Status
    failures: list[StepFailure] = field(default_factory=list)


def _truncate_stderr(text: str, max_lines: int) -> str:
    lines = text.strip().splitlines()
    if len(lines) <= max_lines:
        return text.strip()
    skipped = len(lines) - max_lines
    return f"... ({skipped} lines skipped)\n" + "\n".join(lines[-max_lines:])


@app.command()
def dep_update(
    name: str = typer.Option(..., "-n", "--name", help="Config name"),
    dest_filter: str = typer.Option("", "-d", "--dest", help="Filter destinations (comma-separated)"),
    work_dir: str = typer.Option("", "--work-dir", help="Directory for cloning repos"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without creating PRs"),
    skip_verify: bool = typer.Option(False, "--skip-verify", help="Skip verification steps"),
    src_root_opt: str = typer.Option("", "--src-root", help="Source repo root"),
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

    results = _update_and_validate(config, destinations, src_root, work_dir, skip_verify)
    _create_prs(config, results, dry_run)

    if any(r.status == Status.SKIPPED for r in results):
        raise typer.Exit(1)


def _update_and_validate(
    config: DepConfig,
    destinations: list[Destination],
    src_root: Path,
    work_dir: str,
    skip_verify: bool,
) -> list[RepoResult]:
    results: list[RepoResult] = []

    for dest in destinations:
        result = _process_single_repo(config, dest, src_root, work_dir, skip_verify)

        if result.status == Status.FAILED:
            logger.error(f"{dest.name}: Verification failed, stopping")
            raise typer.Exit(1)

        if result.status != Status.NO_CHANGES:
            results.append(result)

    return results


def _process_single_repo(
    config: DepConfig,
    dest: Destination,
    src_root: Path,
    work_dir: str,
    skip_verify: bool,
) -> RepoResult:
    logger.info(f"Processing {dest.name}...")
    repo_path = _resolve_repo_path(dest, src_root, work_dir)
    repo = _ensure_repo(dest, repo_path)
    git_ops.prepare_copy_branch(repo, dest.default_branch, config.pr.branch, from_default=True)

    if failure := _run_updates(config.updates, repo_path):
        logger.warning(f"{dest.name}: Update failed with exit code {failure.returncode}")
        return RepoResult(dest, repo_path, Status.SKIPPED, failures=[failure])

    if not git_ops.has_changes(repo):
        logger.info(f"{dest.name}: No changes, skipping")
        return RepoResult(dest, repo_path, Status.NO_CHANGES)

    git_ops.commit_changes(repo, config.pr.title)

    if skip_verify:
        return RepoResult(dest, repo_path, Status.PASSED)

    return _verify_repo(repo, repo_path, config.verify, dest)


def _run_updates(updates: list[UpdateEntry], repo_path: Path) -> StepFailure | None:
    """Returns StepFailure on failure, None on success."""
    try:
        for update in updates:
            _run_command(update.command, repo_path / update.workdir)
        return None
    except subprocess.CalledProcessError as e:
        return StepFailure.from_error(e.cmd, e, OnFailStrategy.SKIP)


def _verify_repo(repo, repo_path: Path, verify: VerifyConfig, dest: Destination) -> RepoResult:
    status, failures = _run_verify_steps(repo, repo_path, verify)
    return RepoResult(dest, repo_path, status, failures)


def _create_prs(config: DepConfig, results: list[RepoResult], dry_run: bool) -> None:
    for result in results:
        if result.status == Status.SKIPPED:
            continue

        if dry_run:
            logger.info(f"[DRY RUN] Would create PR for {result.dest.name}")
            continue

        repo = git_ops.get_repo(result.repo_path)
        git_ops.push_branch(repo, config.pr.branch, force=True)

        body = _build_pr_body(result.failures)
        git_ops.create_or_update_pr(
            result.repo_path,
            config.pr.branch,
            config.pr.title,
            body,
            config.pr.labels or None,
            auto_merge=config.pr.auto_merge,
        )
        logger.info(f"{result.dest.name}: PR created/updated")


def _resolve_repo_path(dest: Destination, src_root: Path, work_dir: str) -> Path:
    if dest.dest_path_relative:
        return (src_root / dest.dest_path_relative).resolve()
    if not work_dir:
        raise typer.BadParameter(f"No dest_path_relative for {dest.name}, --work-dir required")
    return Path(work_dir) / dest.name


def _ensure_repo(dest: Destination, repo_path: Path):
    if repo_path.exists() and git_ops.is_git_repo(repo_path):
        return git_ops.get_repo(repo_path)
    if not dest.repo_url:
        raise ValueError(f"Dest {dest.name} not found at {repo_path} and no repo_url configured")
    return git_ops.clone_repo(dest.repo_url, repo_path)


def _run_command(cmd: str, cwd: Path) -> None:
    logger.info(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        logger.error(f"Command failed '{cmd}' in {cwd}: {stderr}")
        raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=stderr)


def _run_verify_steps(
    repo,
    repo_path: Path,
    verify: VerifyConfig,
) -> tuple[Status, list[StepFailure]]:
    failures: list[StepFailure] = []

    for step in verify.steps:
        on_fail = step.on_fail or verify.on_fail

        try:
            _run_command(step.run, repo_path)
        except subprocess.CalledProcessError as e:
            failure = StepFailure.from_error(step.run, e, on_fail)
            match on_fail:
                case OnFailStrategy.FAIL:
                    return (Status.FAILED, [failure])
                case OnFailStrategy.SKIP:
                    return (Status.SKIPPED, [failure])
                case OnFailStrategy.WARN:
                    failures.append(failure)
                    continue

        if step.commit:
            git_ops.stage_and_commit(repo, step.commit.add_paths, step.commit.message)

    return (Status.WARN if failures else Status.PASSED, failures)


def _build_pr_body(failures: list[StepFailure]) -> str:
    body = "Automated dependency update."
    if not failures:
        return body

    body += "\n\n---\n## Verification Issues\n"
    for f in failures:
        body += f"\n### `{f.step}` (strategy: {f.on_fail})\n"
        body += f"**Exit code:** {f.returncode}\n"
        if f.stderr:
            body += f"\n```\n{f.stderr}\n```\n"
    return body
