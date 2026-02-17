from __future__ import annotations

import glob
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import typer
from pydantic import BaseModel

from path_sync import sections
from path_sync._internal import cmd_options, git_ops, header, prompt_utils, verify
from path_sync._internal.auto_merge import PRRef, handle_auto_merge
from path_sync._internal.file_utils import ensure_parents_write_text
from path_sync._internal.log_capture import capture_log
from path_sync._internal.models import (
    Destination,
    PathMapping,
    SrcConfig,
    SyncMode,
    find_repo_root,
    pr_already_synced,
    resolve_config_path,
)
from path_sync._internal.typer_app import app
from path_sync._internal.verify import StepFailure, VerifyResult, VerifyStatus
from path_sync._internal.yaml_utils import load_yaml_model

logger = logging.getLogger(__name__)

EXIT_NO_CHANGES = 0
EXIT_CHANGES = 1
EXIT_ERROR = 2


@dataclass
class SyncResult:
    content_changes: int = 0
    orphans_deleted: int = 0
    synced_paths: set[Path] = field(default_factory=set)

    @property
    def total(self) -> int:
        return self.content_changes + self.orphans_deleted


class CopyOptions(BaseModel):
    dry_run: bool = False
    force_overwrite: bool = False
    no_checkout: bool = False
    checkout_from_default: bool = False
    skip_commit: bool = False
    no_prompt: bool = False
    no_pr: bool = False
    skip_orphan_cleanup: bool = False
    skip_verify: bool = False
    no_wait: bool = False
    no_auto_merge: bool = False
    pr_title: str = ""
    labels: list[str] | None = None
    reviewers: list[str] | None = None
    assignees: list[str] | None = None


@app.command()
def copy(
    name: str = typer.Option("", "-n", "--name", help="Config name (used with src-root to find config)"),
    config_path_opt: str = typer.Option(
        "",
        "-c",
        "--config-path",
        help="Full path to config file (alternative to --name)",
    ),
    src_root_opt: str = typer.Option(
        "",
        "--src-root",
        help="Source repo root (default: find git root from cwd)",
    ),
    dest_filter: str = typer.Option("", "-d", "--dest", help="Filter destinations (comma-separated)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing"),
    force_overwrite: bool = typer.Option(
        False,
        "--force-overwrite",
        help="Overwrite files even if header removed (opted out)",
    ),
    detailed_exit_code: bool = typer.Option(
        False,
        "--detailed-exit-code",
        help="Exit 0=no changes, 1=changes, 2=error",
    ),
    no_checkout: bool = typer.Option(
        False,
        "--no-checkout",
        help="Skip branch switching before sync",
    ),
    checkout_from_default: bool = typer.Option(
        False,
        "--checkout-from-default",
        help="Reset to origin/default before sync (for CI)",
    ),
    skip_commit: bool = typer.Option(
        False,
        "--skip-commit",
        "--local",
        help="No git operations after sync (no commit/push/PR)",
    ),
    no_prompt: bool = typer.Option(
        False,
        "-y",
        "--no-prompt",
        help="Skip confirmations (for CI)",
    ),
    no_pr: bool = typer.Option(
        False,
        "--no-pr",
        help="Push but skip PR creation",
    ),
    pr_title: str = typer.Option(
        "",
        "--pr-title",
        help="Override PR title (supports {name}, {dest_name})",
    ),
    pr_labels: str = cmd_options.pr_labels_option(),
    pr_reviewers: str = cmd_options.pr_reviewers_option(),
    pr_assignees: str = cmd_options.pr_assignees_option(),
    skip_orphan_cleanup: bool = typer.Option(
        False,
        "--skip-orphan-cleanup",
        help="Skip deletion of orphaned synced files",
    ),
    skip_verify: bool = typer.Option(
        False,
        "--skip-verify",
        help="Skip verification steps after syncing",
    ),
    no_wait: bool = typer.Option(
        False,
        "--no-wait",
        help="Enable auto-merge but skip polling for merge completion",
    ),
    no_auto_merge: bool = typer.Option(
        False,
        "--no-auto-merge",
        help="Skip auto-merge even when configured",
    ),
) -> None:
    """Copy files from SRC to DEST repositories."""
    if name and config_path_opt:
        logger.error("Cannot use both --name and --config-path")
        raise typer.Exit(EXIT_ERROR if detailed_exit_code else 1)
    if not name and not config_path_opt:
        logger.error("Either --name or --config-path is required")
        raise typer.Exit(EXIT_ERROR if detailed_exit_code else 1)

    src_root = Path(src_root_opt) if src_root_opt else find_repo_root(Path.cwd())
    config_path = Path(config_path_opt) if config_path_opt else resolve_config_path(src_root, name)

    if not config_path.exists():
        logger.error(f"Config not found: {config_path}")
        raise typer.Exit(EXIT_ERROR if detailed_exit_code else 1)

    config = load_yaml_model(config_path, SrcConfig)

    opts = CopyOptions(
        dry_run=dry_run,
        force_overwrite=force_overwrite,
        no_checkout=no_checkout,
        checkout_from_default=checkout_from_default,
        skip_commit=skip_commit,
        no_prompt=no_prompt,
        no_pr=no_pr,
        skip_orphan_cleanup=skip_orphan_cleanup,
        skip_verify=skip_verify,
        no_wait=no_wait,
        no_auto_merge=no_auto_merge,
        pr_title=pr_title or config.pr_defaults.title,
        labels=cmd_options.split_csv(pr_labels) or config.pr_defaults.labels,
        reviewers=cmd_options.split_csv(pr_reviewers) or config.pr_defaults.reviewers,
        assignees=cmd_options.split_csv(pr_assignees) or config.pr_defaults.assignees,
    )

    try:
        total_changes = _run_copy(config, src_root, dest_filter, opts)
    except Exception as e:
        if detailed_exit_code:
            logger.error(f"Copy failed: {e}")
            raise typer.Exit(EXIT_ERROR)
        raise

    if detailed_exit_code:
        raise typer.Exit(EXIT_CHANGES if total_changes > 0 else EXIT_NO_CHANGES)


def _run_copy(config: SrcConfig, src_root: Path, dest_filter: str, opts: CopyOptions) -> int:
    src_repo = git_ops.get_repo(src_root)
    current_sha = git_ops.get_current_sha(src_repo)
    commit_ts = git_ops.get_commit_timestamp(src_repo)
    src_repo_url = git_ops.get_remote_url(src_repo, config.git_remote)

    destinations = config.destinations
    if dest_filter:
        filter_names = [n.strip() for n in dest_filter.split(",")]
        destinations = [d for d in destinations if d.name in filter_names]

    total_changes = 0
    pr_refs: list[PRRef] = []
    for dest in destinations:
        with capture_log(dest.name) as read_log:
            changes, pr_ref = _sync_destination(
                config, dest, src_root, current_sha, commit_ts, src_repo_url, opts, read_log
            )
        total_changes += changes
        if pr_ref:
            pr_refs.append(pr_ref)

    if config.auto_merge and pr_refs and not opts.no_auto_merge:
        handle_auto_merge(pr_refs, config.auto_merge, no_wait=opts.no_wait)

    return total_changes


def _close_stale_pr(dest_root: Path, copy_branch: str, opts: CopyOptions, config: SrcConfig) -> None:
    if opts.dry_run or opts.skip_commit or opts.no_pr or config.keep_pr_on_no_changes:
        return
    if git_ops.has_open_pr(dest_root, copy_branch):
        git_ops.close_pr(dest_root, copy_branch, "Closing: source and destination are in sync, no changes needed")


def _skip_already_synced(
    dest_name: str, dest_root: Path, copy_branch: str, commit_ts: str, opts: CopyOptions, config: SrcConfig
) -> bool:
    if opts.skip_commit or opts.dry_run or opts.no_pr or config.force_resync:
        return False
    existing_body = git_ops.get_pr_body(dest_root, copy_branch)
    if metadata := pr_already_synced(existing_body, commit_ts):
        logger.info(
            f"{dest_name}: open PR already synced from {metadata.sha[:8]} ({metadata.ts} >= {commit_ts}), skipping"
        )
        return True
    return False


def _sync_destination(
    config: SrcConfig,
    dest: Destination,
    src_root: Path,
    current_sha: str,
    commit_ts: str,
    src_repo_url: str,
    opts: CopyOptions,
    read_log: Callable[[], str],
) -> tuple[int, PRRef | None]:
    dest_root = (src_root / dest.dest_path_relative).resolve()

    if opts.dry_run and not dest_root.exists():
        raise ValueError(f"Destination repo not found: {dest_root}. Clone it first or run without --dry-run.")

    dest_repo = _ensure_dest_repo(dest, dest_root, opts.dry_run)
    copy_branch = dest.resolved_copy_branch(config.name)

    if _skip_already_synced(dest.name, dest_root, copy_branch, commit_ts, opts, config):
        return 0, None

    if not opts.no_checkout and prompt_utils.prompt_confirm(f"Switch {dest.name} to {copy_branch}?", opts.no_prompt):
        git_ops.prepare_copy_branch(
            repo=dest_repo,
            default_branch=dest.default_branch,
            copy_branch=copy_branch,
            from_default=opts.checkout_from_default,
        )
    result = _sync_paths(config, dest, src_root, dest_root, opts)
    _print_sync_summary(dest, result)

    if result.total == 0:
        logger.info(f"{dest.name}: No changes")
        _close_stale_pr(dest_root, copy_branch, opts, config)
        return 0, None

    should_skip_commit = opts.skip_commit or opts.dry_run
    if not should_skip_commit and prompt_utils.prompt_confirm(f"Commit changes to {dest.name}?", opts.no_prompt):
        sync_commit_msg = f"chore: sync {config.name} from {current_sha[:8]}"
        git_ops.commit_changes(dest_repo, sync_commit_msg)

    verify_result = VerifyResult()
    effective_verify = dest.resolve_verify(config.verify)
    if not opts.skip_verify and effective_verify.steps:
        verify_result = verify.run_verify_steps(
            dest_repo, dest_root, effective_verify, dry_run=opts.dry_run, skip_commit=opts.skip_commit
        )
        verify.log_verify_summary(dest.name, verify_result)

        if verify_result.status == VerifyStatus.FAILED:
            logger.error(f"{dest.name}: Verification failed, stopping")
            raise typer.Exit(EXIT_ERROR)

        if verify_result.status == VerifyStatus.SKIPPED:
            logger.warning(f"{dest.name}: Verification skipped due to failure")
            return result.total, None

    pr_ref = _push_and_pr(
        config, dest_repo, dest_root, dest, current_sha, commit_ts, src_repo_url, opts, read_log, verify_result
    )
    return result.total, pr_ref


def _print_sync_summary(dest: Destination, result: SyncResult) -> None:
    typer.echo(f"\nSyncing to {dest.name}...", err=True)
    if result.content_changes > 0:
        typer.echo(f"  [{result.content_changes} files synced]", err=True)
    if result.orphans_deleted > 0:
        typer.echo(f"  [-] {result.orphans_deleted} orphans deleted", err=True)
    if result.total > 0:
        typer.echo(f"\n{result.total} changes ready.", err=True)


def _ensure_dest_repo(dest: Destination, dest_root: Path, dry_run: bool):
    if not dest_root.exists():
        if dry_run:
            raise ValueError(f"Destination repo not found: {dest_root}. Clone it first or run without --dry-run.")
        if not dest.repo_url:
            raise ValueError(f"Dest {dest.name} not found and no repo_url configured")
        git_ops.clone_repo(dest.repo_url, dest_root)
    return git_ops.get_repo(dest_root)


def _sync_paths(
    config: SrcConfig,
    dest: Destination,
    src_root: Path,
    dest_root: Path,
    opts: CopyOptions,
) -> SyncResult:
    result = SyncResult()
    for mapping in config.resolve_paths(dest):
        changes, paths = _sync_path(
            mapping,
            src_root,
            dest_root,
            dest,
            config.name,
            opts.dry_run,
            opts.force_overwrite,
            config.wrap_synced_files,
        )
        result.content_changes += changes
        result.synced_paths.update(paths)

    if not opts.skip_orphan_cleanup:
        result.orphans_deleted = _cleanup_orphans(dest_root, config.name, result.synced_paths, opts.dry_run)
    return result


def _iter_sync_files(
    mapping: PathMapping,
    src_root: Path,
    dest_root: Path,
):
    src_pattern = src_root / mapping.src_path

    if "*" in mapping.src_path:
        glob_prefix = mapping.src_path.split("*")[0].rstrip("/")
        dest_base = mapping.dest_path or glob_prefix
        matches = glob.glob(str(src_pattern), recursive=True)
        if not matches:
            logger.warning(f"Glob matched no files: {mapping.src_path}")
        for src_file in matches:
            src_path = Path(src_file)
            if src_path.is_file() and not mapping.is_excluded(src_path):
                rel = src_path.relative_to(src_root / glob_prefix)
                dest_key = str(Path(dest_base) / rel)
                yield src_path, dest_key, dest_root / dest_base / rel
    elif src_pattern.is_dir():
        dest_base = mapping.resolved_dest_path()
        for src_file in src_pattern.rglob("*"):
            if src_file.is_file() and not mapping.is_excluded(src_file):
                rel = src_file.relative_to(src_pattern)
                dest_key = str(Path(dest_base) / rel)
                yield src_file, dest_key, dest_root / dest_base / rel
    elif src_pattern.is_file():
        dest_base = mapping.resolved_dest_path()
        yield src_pattern, dest_base, dest_root / dest_base
    else:
        logger.warning(f"Source not found: {mapping.src_path}")


def _sync_path(
    mapping: PathMapping,
    src_root: Path,
    dest_root: Path,
    dest: Destination,
    config_name: str,
    dry_run: bool,
    force_overwrite: bool,
    wrap_synced_files: bool = False,
) -> tuple[int, set[Path]]:
    changes = 0
    synced: set[Path] = set()

    should_wrap = mapping.should_wrap(wrap_synced_files)
    for src_path, dest_key, dest_path in _iter_sync_files(mapping, src_root, dest_root):
        if dest.is_skipped(dest_key):
            continue
        changes += _copy_file(
            src_path,
            dest_path,
            dest,
            dest_key,
            config_name,
            mapping.sync_mode,
            dry_run,
            force_overwrite,
            should_wrap,
        )
        synced.add(dest_path)

    return changes, synced


def _copy_file(
    src: Path,
    dest_path: Path,
    dest: Destination,
    dest_key: str,
    config_name: str,
    sync_mode: SyncMode,
    dry_run: bool,
    force_overwrite: bool = False,
    should_wrap: bool = False,
) -> int:
    try:
        src_content = header.remove_header(src.read_text())
    except UnicodeDecodeError:
        return _copy_binary_file(src, dest_path, sync_mode, dry_run)

    match sync_mode:
        case SyncMode.SCAFFOLD:
            return _handle_scaffold(src_content, dest_path, dry_run)
        case SyncMode.REPLACE:
            return _handle_replace(src_content, dest_path, dry_run)
        case SyncMode.SYNC:
            skip_list = dest.skip_sections.get(dest_key, [])
            return _handle_sync(src_content, dest_path, skip_list, config_name, dry_run, force_overwrite, should_wrap)


def _copy_binary_file(src: Path, dest_path: Path, sync_mode: SyncMode, dry_run: bool) -> int:
    src_bytes = src.read_bytes()
    match sync_mode:
        case SyncMode.SCAFFOLD:
            if dest_path.exists():
                return 0
        case SyncMode.REPLACE | SyncMode.SYNC:
            if dest_path.exists() and dest_path.read_bytes() == src_bytes:
                return 0
    return _write_binary_file(dest_path, src_bytes, dry_run)


def _write_binary_file(dest_path: Path, content: bytes, dry_run: bool) -> int:
    if dry_run:
        logger.info(f"[DRY RUN] Would write binary: {dest_path}")
        return 1
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(content)
    logger.info(f"Wrote binary: {dest_path}")
    return 1


def _handle_scaffold(content: str, dest_path: Path, dry_run: bool) -> int:
    if dest_path.exists():
        return 0
    return _write_file(dest_path, content, dry_run)


def _handle_replace(content: str, dest_path: Path, dry_run: bool) -> int:
    if dest_path.exists() and dest_path.read_text() == content:
        return 0
    return _write_file(dest_path, content, dry_run)


def _handle_sync(
    src_content: str,
    dest_path: Path,
    skip_list: list[str],
    config_name: str,
    dry_run: bool,
    force_overwrite: bool,
    should_wrap: bool = False,
) -> int:
    if not header.has_known_comment_prefix(dest_path):
        logger.warning(f"No comment config for {dest_path.suffix!r}, cannot sync sections/headers for: {dest_path}")
        return 0

    if sections.has_sections(src_content, dest_path):
        return _handle_sync_sections(src_content, dest_path, skip_list, config_name, dry_run, force_overwrite)

    if should_wrap:
        wrapped = sections.wrap_in_synced_section(src_content, dest_path)
        return _handle_sync_sections(wrapped, dest_path, skip_list, config_name, dry_run, force_overwrite)

    if dest_path.exists():
        existing = dest_path.read_text()
        has_hdr = header.has_header(existing)
        if not has_hdr and not force_overwrite:
            logger.info(f"Skipping {dest_path} (header removed - opted out)")
            return 0
        if header.remove_header(existing) == src_content and has_hdr:
            return 0

    new_content = header.add_header(src_content, dest_path, config_name)
    return _write_file(dest_path, new_content, dry_run)


def _write_file(dest_path: Path, content: str, dry_run: bool) -> int:
    if dry_run:
        logger.info(f"[DRY RUN] Would write: {dest_path}")
        return 1
    ensure_parents_write_text(dest_path, content)
    logger.info(f"Wrote: {dest_path}")
    return 1


def _handle_sync_sections(
    src_content: str,
    dest_path: Path,
    skip_list: list[str],
    config_name: str,
    dry_run: bool,
    force_overwrite: bool,
) -> int:
    src_sections = sections.parse_sections(src_content, dest_path)

    if dest_path.exists():
        existing = dest_path.read_text()
        if not header.has_header(existing) and not force_overwrite:
            logger.info(f"Skipping {dest_path} (header removed - opted out)")
            return 0
        dest_body = header.remove_header(existing)
        new_body = sections.replace_sections(dest_body, src_sections, dest_path, skip_list)
    elif skip_list:
        filtered = [s for s in src_sections if s.id not in skip_list]
        new_body = sections.build_sections_content(filtered, dest_path)
    else:
        new_body = src_content

    new_content = header.add_header(new_body, dest_path, config_name)

    if dest_path.exists() and dest_path.read_text() == new_content:
        return 0

    return _write_file(dest_path, new_content, dry_run)


def _cleanup_orphans(
    dest_root: Path,
    config_name: str,
    synced_paths: set[Path],
    dry_run: bool,
) -> int:
    deleted = 0
    for path in _find_files_with_config(dest_root, config_name):
        if path not in synced_paths:
            if dry_run:
                logger.info(f"[DRY RUN] Would delete orphan: {path}")
            else:
                path.unlink()
                logger.info(f"Deleted orphan: {path}")
            deleted += 1
    return deleted


def _find_files_with_config(dest_root: Path, config_name: str) -> list[Path]:
    result = []
    for path in dest_root.rglob("*"):
        if ".git" in path.parts:
            continue
        if header.file_get_config_name(path) == config_name:
            result.append(path)
    return result


def _push_and_pr(
    config: SrcConfig,
    repo,
    dest_root: Path,
    dest: Destination,
    sha: str,
    commit_ts: str,
    src_repo_url: str,
    opts: CopyOptions,
    read_log: Callable[[], str],
    verify_result: VerifyResult,
) -> PRRef | None:
    if opts.skip_commit or opts.dry_run:
        logger.info("Skipping push/PR (--skip-commit or --dry-run)")
        return None

    copy_branch = dest.resolved_copy_branch(config.name)

    if git_ops.has_changes(repo):
        if not prompt_utils.prompt_confirm(f"Commit remaining changes to {dest.name}?", opts.no_prompt):
            return None
        commit_msg = f"chore: post-sync changes for {config.name}"
        git_ops.commit_changes(repo, commit_msg)
        typer.echo(f"  Committed: {commit_msg}", err=True)

    if not prompt_utils.prompt_confirm(f"Push {dest.name} to origin?", opts.no_prompt):
        return None

    git_ops.push_branch(repo, copy_branch, force=True)
    typer.echo(f"  Pushed: {copy_branch} (force)", err=True)

    if opts.no_pr or not prompt_utils.prompt_confirm(f"Create PR for {dest.name}?", opts.no_prompt):
        return None

    sync_log = read_log()
    pr_body = config.pr_defaults.format_body(
        src_repo_url=src_repo_url,
        src_sha=sha,
        sync_log=sync_log,
        dest_name=dest.name,
        src_commit_ts=commit_ts,
    )

    if verify_result.failures:
        pr_body = _append_verify_warnings(pr_body, verify_result.failures)

    title = opts.pr_title.format(name=config.name, dest_name=dest.name)
    pr_url = git_ops.create_or_update_pr(
        dest_root,
        copy_branch,
        title,
        pr_body,
        opts.labels,
        opts.reviewers,
        opts.assignees,
    )
    if pr_url:
        typer.echo(f"  Created PR: {pr_url}", err=True)

    branch_or_url = pr_url or copy_branch
    return PRRef(dest_name=dest.name, repo_path=dest_root, branch_or_url=branch_or_url)


def _append_verify_warnings(body: str, failures: list[StepFailure]) -> str:
    body += "\n\n---\n## Verification Warnings\n"
    for f in failures:
        body += f"\n- `{f.step}` failed (exit code {f.returncode}, strategy: {f.on_fail})"
    return body
