from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import typer

from path_sync._internal import git_ops
from path_sync._internal.models import Destination, find_repo_root
from path_sync._internal.models_dep import (
    DepConfig,
    OnFailStrategy,
    VerifyConfig,
    resolve_dep_config_path,
)
from path_sync._internal.typer_app import app
from path_sync._internal.yaml_utils import load_yaml_model

logger = logging.getLogger(__name__)

StatusType = Literal["passed", "skipped", "warn"]


@dataclass
class RepoResult:
    dest: Destination
    repo_path: Path
    status: StatusType
    warnings: list[str] = field(default_factory=list)


@app.command(name="dep-update")
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

    results = _phase1_update_and_validate(config, destinations, src_root, work_dir, skip_verify)
    _phase2_create_prs(config, results, dry_run)

    if any(r.status == "skipped" for r in results):
        raise typer.Exit(1)


def _phase1_update_and_validate(
    config: DepConfig,
    destinations: list[Destination],
    src_root: Path,
    work_dir: str,
    skip_verify: bool,
) -> list[RepoResult]:
    results: list[RepoResult] = []

    for dest in destinations:
        logger.info(f"Processing {dest.name}...")
        repo_path = _resolve_repo_path(dest, src_root, work_dir)

        repo = _ensure_repo(dest, repo_path)
        git_ops.prepare_copy_branch(repo, dest.default_branch, config.pr.branch, from_default=True)

        try:
            for update in config.updates:
                _run_command(update.command, repo_path / update.workdir)
        except subprocess.CalledProcessError as e:
            logger.warning(f"{dest.name}: Update failed, skipping: {e}")
            results.append(RepoResult(dest, repo_path, "skipped"))
            continue

        if not git_ops.has_changes(repo):
            logger.info(f"{dest.name}: No changes, skipping")
            continue

        git_ops.commit_changes(repo, config.pr.title)

        if skip_verify:
            results.append(RepoResult(dest, repo_path, "passed"))
            continue

        status, warnings = _run_verify_steps(repo, repo_path, config.verify)
        if status == "failed":
            logger.error(f"{dest.name}: Verification failed, stopping")
            raise typer.Exit(1)

        results.append(RepoResult(dest, repo_path, status, warnings))

    return results


def _phase2_create_prs(config: DepConfig, results: list[RepoResult], dry_run: bool) -> None:
    for result in results:
        if result.status == "skipped":
            continue

        if dry_run:
            logger.info(f"[DRY RUN] Would create PR for {result.dest.name}")
            continue

        repo = git_ops.get_repo(result.repo_path)
        git_ops.push_branch(repo, config.pr.branch, force=True)

        body = _build_pr_body(result.warnings)
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
        logger.error(f"Command failed: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, cmd)


def _run_verify_steps(
    repo,
    repo_path: Path,
    verify: VerifyConfig,
) -> tuple[Literal["passed", "skipped", "warn", "failed"], list[str]]:
    warnings: list[str] = []

    for step in verify.steps:
        on_fail = step.on_fail or verify.on_fail

        try:
            _run_command(step.run, repo_path)
        except subprocess.CalledProcessError as e:
            match on_fail:
                case OnFailStrategy.FAIL:
                    return ("failed", [])
                case OnFailStrategy.SKIP:
                    return ("skipped", [])
                case OnFailStrategy.WARN:
                    warnings.append(f"`{step.run}` failed: {e}")
                    continue

        if step.commit:
            git_ops.stage_and_commit(repo, step.commit.add_paths, step.commit.message)

    return ("warn" if warnings else "passed", warnings)


def _build_pr_body(warnings: list[str]) -> str:
    body = "Automated dependency update."
    if warnings:
        body += "\n\n---\n**Warning:** Some verification steps failed:\n"
        body += "\n".join(f"- {w}" for w in warnings)
    return body
