from __future__ import annotations

import fnmatch
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

import typer
from git import Repo
from pydantic import BaseModel, Field

from path_sync import sections
from path_sync._internal import git_ops, header, prompt_utils
from path_sync._internal.cmd_copy import _iter_sync_files
from path_sync._internal.dest_only import DestOnlyFile, collect_dest_only_files, is_opted_out
from path_sync._internal.file_utils import ensure_parents_write_text
from path_sync._internal.models import (
    Destination,
    SrcConfig,
    SyncMode,
    find_repo_root,
    resolve_config_path,
)
from path_sync._internal.repo_utils import resolve_repo_path
from path_sync._internal.typer_app import app
from path_sync._internal.yaml_utils import load_yaml_model

logger = logging.getLogger(__name__)

_EMPTY_STR_LIST: list[str] = []
_INCLUDE_OPTION = typer.Option(_EMPTY_STR_LIST, "-i", "--include", help="Keep paths matching pattern")
_EXCLUDE_OPTION = typer.Option(_EMPTY_STR_LIST, "-e", "--exclude", help="Drop paths matching pattern")


class PullKind(StrEnum):
    SECTIONS = "sections"
    WHOLE = "whole"
    BINARY = "binary"


class PullOptions(BaseModel):
    dry_run: bool = False
    dest_only: bool = False
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


@dataclass
class PullCandidate:
    src_path: Path
    dest_path: Path
    dest_key: str
    kind: PullKind
    section_ids: list[str]
    dest_ts: int | None
    src_ts: int | None
    skip_sections: list[str]
    dest_only: bool = False


def _validate_dest_name(dest: str) -> str:
    if not dest.strip():
        raise ValueError("Missing destination: -d is required")
    if "," in dest:
        raise ValueError("Exactly one destination required; comma-separated list not supported")
    return dest.strip()


def _format_unix(ts: int) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")


def _managed_section_map(content: str, path: Path, skip: list[str]) -> dict[str, str]:
    body = header.remove_header(content)
    extracted = sections.extract_sections(body, path)
    return {k: v for k, v in extracted.items() if k not in skip}


def _diff_section_ids(dest_map: dict[str, str], src_map: dict[str, str]) -> list[str]:
    ids = set(dest_map) | set(src_map)
    return sorted(i for i in ids if dest_map.get(i) != src_map.get(i))


def _collect_mapped_candidates(
    config: SrcConfig,
    dest: Destination,
    src_root: Path,
    dest_root: Path,
    src_repo: Repo,
    dest_repo: Repo,
) -> list[PullCandidate]:
    candidates: list[PullCandidate] = []
    for mapping in config.resolve_paths(dest):
        for src_path, dest_key, dest_path in _iter_sync_files(mapping, src_root, dest_root):
            if dest.is_skipped(dest_key):
                continue
            if not dest_path.exists():
                logger.warning(f"Dest not found: {dest_path}")
                continue
            if not src_path.exists():
                continue
            if mapping.sync_mode == SyncMode.SCAFFOLD:
                continue

            skip_list = dest.skip_sections.get(dest_key, [])
            candidate = _candidate_for_path(
                src_path,
                dest_path,
                dest_key,
                mapping.sync_mode,
                skip_list,
                src_repo,
                dest_repo,
            )
            if candidate:
                candidates.append(candidate)
    return candidates


def _dest_only_candidate(row: DestOnlyFile) -> PullCandidate:
    try:
        row.dest_path.read_text()
    except UnicodeDecodeError:
        kind = PullKind.BINARY
    else:
        kind = PullKind.WHOLE
    return PullCandidate(
        src_path=row.src_path,
        dest_path=row.dest_path,
        dest_key=row.dest_key,
        kind=kind,
        section_ids=[],
        dest_ts=None,
        src_ts=None,
        skip_sections=[],
        dest_only=True,
    )


def _collect_dest_only_candidates(
    config: SrcConfig,
    dest: Destination,
    src_root: Path,
    dest_root: Path,
    dest_repo: Repo,
    skip_keys: set[str],
) -> list[PullCandidate]:
    return [
        _dest_only_candidate(row)
        for row in collect_dest_only_files(config, dest, src_root, dest_root, dest_repo, skip_keys)
    ]


def _text_pull_kind(
    src_path: Path,
    dest_path: Path,
    dest_text: str,
    src_text: str,
    sync_mode: SyncMode,
    skip_list: list[str],
) -> tuple[PullKind, list[str]] | None:
    if is_opted_out(dest_text, sync_mode):
        return None

    dest_body = header.remove_header(dest_text)
    if header.has_known_comment_prefix(dest_path) and sections.has_sections(dest_body, dest_path):
        dest_map = _managed_section_map(dest_text, dest_path, skip_list)
        src_map = _managed_section_map(src_text, src_path, skip_list)
        if dest_map == src_map:
            return None
        return PullKind.SECTIONS, _diff_section_ids(dest_map, src_map)

    if header.remove_header(dest_text) == src_text:
        return None
    return PullKind.WHOLE, []


def _candidate_for_path(
    src_path: Path,
    dest_path: Path,
    dest_key: str,
    sync_mode: SyncMode,
    skip_list: list[str],
    src_repo: Repo,
    dest_repo: Repo,
) -> PullCandidate | None:
    try:
        dest_text = dest_path.read_text()
        src_text = src_path.read_text()
    except UnicodeDecodeError:
        if dest_path.read_bytes() == src_path.read_bytes():
            return None
        kind, section_ids = PullKind.BINARY, []
    else:
        kind_info = _text_pull_kind(src_path, dest_path, dest_text, src_text, sync_mode, skip_list)
        if kind_info is None:
            return None
        kind, section_ids = kind_info

    if git_ops.path_is_dirty(dest_repo, dest_path):
        logger.warning(f"Skipping dirty dest path: {dest_path}")
        return None
    if git_ops.path_is_dirty(src_repo, src_path):
        logger.warning(f"Skipping dirty src path: {src_path}")
        return None

    dest_ts = git_ops.file_last_commit_unix(dest_repo, dest_path)
    src_ts = git_ops.file_last_commit_unix(src_repo, src_path)
    if dest_ts is None or src_ts is None or dest_ts <= src_ts:
        return None

    return PullCandidate(
        src_path=src_path,
        dest_path=dest_path,
        dest_key=dest_key,
        kind=kind,
        section_ids=section_ids,
        dest_ts=dest_ts,
        src_ts=src_ts,
        skip_sections=skip_list,
    )


def _keep_pull_path(rel: str, include: list[str], exclude: list[str]) -> bool:
    if include and not any(fnmatch.fnmatch(rel, pat) for pat in include):
        return False
    return not (exclude and any(fnmatch.fnmatch(rel, pat) for pat in exclude))


def _format_candidate_line(candidate: PullCandidate, src_root: Path) -> str:
    rel = str(candidate.src_path.relative_to(src_root))
    if candidate.dest_only:
        return f"  {rel:<30}  dest-only"
    if candidate.kind == PullKind.SECTIONS:
        detail = f"sections: {', '.join(candidate.section_ids)}"
    elif candidate.kind == PullKind.WHOLE:
        detail = "whole file"
    else:
        detail = "binary"
    dest_ts = candidate.dest_ts
    src_ts = candidate.src_ts
    assert dest_ts is not None and src_ts is not None
    ts = f"dest {_format_unix(dest_ts)} > src {_format_unix(src_ts)}"
    return f"  {rel:<30}  {detail:<30}  {ts}"


def _print_candidates(dest_name: str, candidates: list[PullCandidate], src_root: Path) -> None:
    typer.echo(f"\nPull from {dest_name} into src?\n", err=True)
    for c in candidates:
        typer.echo(_format_candidate_line(c, src_root), err=True)


def _apply_candidate(candidate: PullCandidate) -> None:
    if candidate.kind == PullKind.BINARY:
        candidate.src_path.parent.mkdir(parents=True, exist_ok=True)
        candidate.src_path.write_bytes(candidate.dest_path.read_bytes())
        logger.info(f"Pulled binary: {candidate.src_path}")
        return

    if candidate.kind == PullKind.SECTIONS:
        dest_body = header.remove_header(candidate.dest_path.read_text())
        dest_sections = sections.parse_sections(dest_body, candidate.dest_path)
        new_content = sections.replace_sections(
            candidate.src_path.read_text(),
            dest_sections,
            candidate.src_path,
            skip_sections=candidate.skip_sections,
            keep_deleted_sections=True,
        )
    else:
        new_content = header.remove_header(candidate.dest_path.read_text())

    ensure_parents_write_text(candidate.src_path, new_content)
    logger.info(f"Pulled: {candidate.src_path}")


def _run_pull(config: SrcConfig, dest: Destination, src_root: Path, opts: PullOptions) -> None:
    dest_root = resolve_repo_path(dest, src_root, "")
    if not git_ops.is_git_repo(dest_root):
        raise ValueError(f"Not a git repository: {dest_root}")

    src_repo = git_ops.get_repo(src_root)
    dest_repo = git_ops.get_repo(dest_root)
    candidates = _collect_mapped_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    if opts.dest_only:
        skip_keys = {c.dest_key for c in candidates}
        candidates.extend(_collect_dest_only_candidates(config, dest, src_root, dest_root, dest_repo, skip_keys))

    candidates = [
        c for c in candidates if _keep_pull_path(str(c.src_path.relative_to(src_root)), opts.include, opts.exclude)
    ]

    if not candidates:
        typer.echo("No pull candidates.", err=True)
        return

    _print_candidates(dest.name, candidates, src_root)

    if opts.dry_run or not sys.stdin.isatty():
        return
    if prompt_utils.prompt_pull_confirm("Confirm?"):
        for c in candidates:
            _apply_candidate(c)


@app.command()
def pull(
    name: str = typer.Option("", "-n", "--name", help="Config name"),
    config_path_opt: str = typer.Option("", "-c", "--config-path", help="Full path to config file"),
    src_root_opt: str = typer.Option("", "--src-root", help="Source repo root"),
    dest_name: str = typer.Option(..., "-d", "--dest", help="Destination name (exactly one)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print candidates without writing (same as non-TTY)"),
    dest_only: bool = typer.Option(False, "--dest-only", help="Also harvest dest files with no src counterpart"),
    include: list[str] = _INCLUDE_OPTION,
    exclude: list[str] = _EXCLUDE_OPTION,
) -> None:
    """Harvest newer mapped dest files into src after one confirm.

    --dest-only also copies dest-only files. Quote glob patterns (e.g. -i '.cursor/*').
    """
    if name and config_path_opt:
        logger.error("Cannot use both --name and --config-path")
        raise typer.Exit(1)
    if not name and not config_path_opt:
        logger.error("Either --name or --config-path is required")
        raise typer.Exit(1)

    try:
        dest_filter = _validate_dest_name(dest_name)
    except ValueError as e:
        logger.error(str(e))
        raise typer.Exit(1)

    src_root = Path(src_root_opt) if src_root_opt else find_repo_root(Path.cwd())
    config_path = Path(config_path_opt) if config_path_opt else resolve_config_path(src_root, name)
    if not config_path.exists():
        logger.error(f"Config not found: {config_path}")
        raise typer.Exit(1)

    config = load_yaml_model(config_path, SrcConfig)
    dest = config.find_destination(dest_filter)
    opts = PullOptions(
        dry_run=dry_run,
        dest_only=dest_only,
        include=include,
        exclude=exclude,
    )

    try:
        _run_pull(config, dest, src_root, opts)
    except ValueError as e:
        logger.error(f"Pull failed: {e}")
        raise typer.Exit(1)
