from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import typer
from git import Repo
from pydantic import BaseModel, Field

from path_sync import sections
from path_sync._internal import git_ops, header, prompt_utils
from path_sync._internal.cmd_copy import _iter_sync_files
from path_sync._internal.cmd_pull import _EMPTY_STR_LIST, _EXCLUDE_OPTION, _INCLUDE_OPTION, keep_pull_path
from path_sync._internal.dest_only import is_opted_out
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


class MergeClassification(StrEnum):
    DEST_CHANGED = "dest-changed"
    SRC_CHANGED = "src-changed"
    MERGE = "merge"
    NO_COMMON_BASE = "no-common-base"


class MergeOptions(BaseModel):
    dry_run: bool = False
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


@dataclass
class MergeUnit:
    src_path: Path
    dest_path: Path
    dest_key: str
    section_id: str | None
    skip_sections: list[str] = field(default_factory=list)
    wrap: bool = False


@dataclass(frozen=True)
class UnitVersion:
    body: str
    commit_unix: int
    renamed_from: str | None = None


@dataclass
class MergeCandidate:
    unit: MergeUnit
    classification: MergeClassification
    src_body: str
    dest_body: str
    merged_body: str | None = None
    conflicted: bool = False
    renamed_from: str | None = None

    @property
    def is_conflict(self) -> bool:
        return self.classification == MergeClassification.NO_COMMON_BASE or self.conflicted

    @property
    def effective_body(self) -> str:
        if self.classification == MergeClassification.MERGE:
            assert self.merged_body is not None
            return self.merged_body
        return self.dest_body


def _unit_body(content: str, path: Path, section_id: str | None) -> str | None:
    body = header.remove_header(content)
    if section_id is None:
        return body
    return sections.extract_sections(body, path).get(section_id)


def _unit_bodies(repo: Repo, path: Path, section_id: str | None) -> list[UnitVersion]:
    rel_path = str(path.relative_to(repo.working_dir))
    seen: set[str] = set()
    versions: list[UnitVersion] = []
    for file_version in git_ops.walk_file_history(repo, rel_path):
        content = git_ops.file_content_at_commit(repo, file_version.sha, file_version.path)
        if content is None:
            continue
        body = _unit_body(content, path, section_id)
        if body is None or body in seen:
            continue
        seen.add(body)
        versions.append(
            UnitVersion(body=body, commit_unix=file_version.commit_unix, renamed_from=file_version.renamed_from)
        )
    return versions


def _find_base(src_versions: list[UnitVersion], dest_versions: list[UnitVersion]) -> UnitVersion | None:
    src_bodies = {version.body for version in src_versions}
    for dest_version in dest_versions:
        if dest_version.body in src_bodies:
            return dest_version
    return None


def _classify(src_body: str, dest_body: str, base: UnitVersion | None) -> MergeClassification:
    if base is None:
        return MergeClassification.NO_COMMON_BASE
    if src_body == base.body:
        return MergeClassification.DEST_CHANGED
    if dest_body == base.body:
        return MergeClassification.SRC_CHANGED
    return MergeClassification.MERGE


def _merge_bodies(base: str, src: str, dest: str) -> tuple[str, bool]:
    """Run `git merge-file` on the three bodies, returning (merged, conflicted)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        base_file = tmp_path / "base"
        src_file = tmp_path / "src"
        dest_file = tmp_path / "dest"
        base_file.write_text(base)
        src_file.write_text(src)
        dest_file.write_text(dest)
        result = subprocess.run(
            ["git", "merge-file", "-p", str(src_file), str(base_file), str(dest_file)],
            capture_output=True,
            text=True,
            check=False,
        )
    return result.stdout, result.returncode != 0


def _units_for_path(
    src_path: Path,
    src_text: str,
    dest_path: Path,
    dest_key: str,
    skip_list: list[str],
    wrap: bool,
) -> list[MergeUnit]:
    body = header.remove_header(src_text)
    if header.has_known_comment_prefix(dest_path) and sections.has_sections(body, dest_path):
        section_ids = sections.extract_sections(body, dest_path)
        return [
            MergeUnit(
                src_path=src_path,
                dest_path=dest_path,
                dest_key=dest_key,
                section_id=section_id,
                skip_sections=skip_list,
            )
            for section_id in section_ids
            if section_id not in skip_list
        ]
    if wrap:
        if "synced" in skip_list:
            return []
        return [
            MergeUnit(
                src_path=src_path,
                dest_path=dest_path,
                dest_key=dest_key,
                section_id=None,
                skip_sections=skip_list,
                wrap=True,
            )
        ]
    return [
        MergeUnit(src_path=src_path, dest_path=dest_path, dest_key=dest_key, section_id=None, skip_sections=skip_list)
    ]


def _first_rename(versions: list[UnitVersion]) -> str | None:
    for version in versions:
        if version.renamed_from:
            return version.renamed_from
    return None


def _candidate_for_unit(
    unit: MergeUnit,
    src_text: str,
    dest_text: str,
    src_repo: Repo,
    dest_repo: Repo,
) -> MergeCandidate | None:
    dest_section_id = unit.section_id if unit.section_id is not None else ("synced" if unit.wrap else None)
    src_body = _unit_body(src_text, unit.src_path, unit.section_id)
    dest_body = _unit_body(dest_text, unit.dest_path, dest_section_id)
    if src_body is None or dest_body is None:
        return None
    if src_body == dest_body:
        return None

    src_versions = _unit_bodies(src_repo, unit.src_path, unit.section_id)
    dest_versions = _unit_bodies(dest_repo, unit.dest_path, dest_section_id)
    base = _find_base(src_versions, dest_versions)
    classification = _classify(src_body, dest_body, base)
    if classification == MergeClassification.SRC_CHANGED:
        return None

    candidate = MergeCandidate(
        unit=unit,
        classification=classification,
        src_body=src_body,
        dest_body=dest_body,
    )
    if classification == MergeClassification.MERGE:
        assert base is not None
        candidate.merged_body, candidate.conflicted = _merge_bodies(base.body, src_body, dest_body)
    elif classification == MergeClassification.NO_COMMON_BASE:
        candidate.renamed_from = _first_rename(dest_versions)
    return candidate


def _candidates_for_path(
    src_path: Path,
    dest_path: Path,
    dest_key: str,
    sync_mode: SyncMode,
    skip_list: list[str],
    wrap: bool,
    src_repo: Repo,
    dest_repo: Repo,
) -> list[MergeCandidate]:
    try:
        src_text = src_path.read_text()
        dest_text = dest_path.read_text()
    except UnicodeDecodeError:
        return []
    if is_opted_out(dest_text, sync_mode):
        return []
    if git_ops.path_is_dirty(src_repo, src_path):
        logger.warning(f"Skipping dirty src path: {src_path}")
        return []
    if git_ops.path_is_dirty(dest_repo, dest_path):
        logger.warning(f"Skipping dirty dest path: {dest_path}")
        return []

    candidates: list[MergeCandidate] = []
    for unit in _units_for_path(src_path, src_text, dest_path, dest_key, skip_list, wrap):
        candidate = _candidate_for_unit(unit, src_text, dest_text, src_repo, dest_repo)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _collect_merge_candidates(
    config: SrcConfig,
    dest: Destination,
    src_root: Path,
    dest_root: Path,
    src_repo: Repo,
    dest_repo: Repo,
) -> list[MergeCandidate]:
    candidates: list[MergeCandidate] = []
    for mapping in config.resolve_paths(dest):
        if mapping.sync_mode == SyncMode.SCAFFOLD:
            continue
        for src_path, dest_key, dest_path in _iter_sync_files(mapping, src_root, dest_root):
            if dest.is_skipped(dest_key):
                continue
            if not src_path.exists():
                continue
            if not dest_path.exists():
                logger.warning(f"Dest not found: {dest_path}")
                continue
            skip_list = dest.skip_sections.get(dest_key, [])
            wrap = mapping.should_wrap(config.wrap_synced_files)
            candidates.extend(
                _candidates_for_path(
                    src_path, dest_path, dest_key, mapping.sync_mode, skip_list, wrap, src_repo, dest_repo
                )
            )
    return candidates


def _apply_merge(candidate: MergeCandidate) -> Path:
    unit = candidate.unit
    body = candidate.merged_body if candidate.classification == MergeClassification.MERGE else candidate.dest_body
    assert body is not None
    if unit.section_id is None:
        ensure_parents_write_text(unit.src_path, body)
    else:
        section = sections.Section(id=unit.section_id, parts=[sections.SectionPart(body, 0, 0)])
        new_content = sections.replace_sections(
            unit.src_path.read_text(),
            [section],
            unit.src_path,
            skip_sections=unit.skip_sections,
            keep_deleted_sections=True,
        )
        ensure_parents_write_text(unit.src_path, new_content)
    logger.info(f"Merged: {unit.src_path}")
    return unit.src_path


def _candidate_label(candidate: MergeCandidate, src_root: Path) -> str:
    rel = str(candidate.unit.src_path.relative_to(src_root))
    if candidate.unit.section_id:
        return f"{rel}:{candidate.unit.section_id}"
    return rel


def _candidate_detail(candidate: MergeCandidate) -> str:
    if candidate.classification == MergeClassification.DEST_CHANGED:
        return "dest-changed"
    if candidate.classification == MergeClassification.MERGE:
        return "conflict: overlapping edit" if candidate.conflicted else "merge"
    if candidate.renamed_from:
        return f"conflict: no common base ({candidate.renamed_from} -> {candidate.unit.dest_key})"
    return "conflict: no common base"


def _print_candidates(dest_name: str, candidates: list[MergeCandidate], src_root: Path) -> None:
    typer.echo(f"\nMerge {dest_name} into src?\n", err=True)
    for candidate in candidates:
        typer.echo(f"  {_candidate_label(candidate, src_root):<40}  {_candidate_detail(candidate)}", err=True)


def _parse_dest_filter(values: list[str]) -> list[str]:
    names: list[str] = []
    for value in values:
        names.extend(part.strip() for part in value.split(",") if part.strip())
    return names


def _collect_dest_candidates(
    config: SrcConfig, dest: Destination, src_root: Path, opts: MergeOptions, src_repo: Repo
) -> list[MergeCandidate]:
    dest_root = resolve_repo_path(dest, src_root, "")
    if not git_ops.is_git_repo(dest_root):
        raise ValueError(f"Not a git repository: {dest_root}")
    dest_repo = git_ops.get_repo(dest_root)
    candidates = _collect_merge_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    return [
        candidate
        for candidate in candidates
        if keep_pull_path(str(candidate.unit.src_path.relative_to(src_root)), opts.include, opts.exclude)
    ]


def _conflict_labels(candidates_by_dest: dict[str, list[MergeCandidate]], src_root: Path) -> list[str]:
    return [
        f"{name}:{_candidate_label(candidate, src_root)}"
        for name, candidates in candidates_by_dest.items()
        for candidate in candidates
        if candidate.is_conflict
    ]


def _duplicate_conflicts(candidates_by_dest: dict[str, list[MergeCandidate]], src_root: Path) -> list[str]:
    units: dict[tuple[str, str | None], list[tuple[str, MergeCandidate]]] = {}
    for name, candidates in candidates_by_dest.items():
        for candidate in candidates:
            if candidate.is_conflict:
                continue
            key = (str(candidate.unit.src_path), candidate.unit.section_id)
            units.setdefault(key, []).append((name, candidate))
    conflicts: list[str] = []
    for entries in units.values():
        if len({candidate.effective_body for _, candidate in entries}) <= 1:
            continue
        names = ", ".join(sorted({name for name, _ in entries}))
        conflicts.append(f"{names}: {_candidate_label(entries[0][1], src_root)}")
    return conflicts


def _apply_candidates(candidates: list[MergeCandidate]) -> None:
    for candidate in candidates:
        _apply_merge(candidate)


def _apply_and_report(
    src_root: Path,
    src_repo: Repo,
    changed: list[Destination],
    candidates_by_dest: dict[str, list[MergeCandidate]],
) -> None:
    touched = sorted({c.unit.src_path for dest in changed for c in candidates_by_dest[dest.name]})
    originals = {path: path.read_text() for path in touched}
    for dest in changed:
        _apply_candidates(candidates_by_dest[dest.name])
        typer.echo(f"  {dest.name}: chore: merge destination {dest.name}", err=True)

    if not sys.stdin.isatty():
        for dest in changed:
            typer.echo(f"Suggested commit: chore: merge destination {dest.name}", err=True)
        return
    if not prompt_utils.prompt_confirm("Commit src?"):
        return
    for path, content in originals.items():
        ensure_parents_write_text(path, content)
    for dest in changed:
        _apply_candidates(candidates_by_dest[dest.name])
        paths = sorted({str(c.unit.src_path.relative_to(src_root)) for c in candidates_by_dest[dest.name]})
        git_ops.commit_paths(src_repo, paths, f"chore: merge destination {dest.name}")


def _run_merge(config: SrcConfig, src_root: Path, dest_names: list[str], opts: MergeOptions) -> None:
    dests = [config.find_destination(name) for name in dest_names] if dest_names else config.destinations
    src_repo = git_ops.get_repo(src_root)
    candidates_by_dest = {dest.name: _collect_dest_candidates(config, dest, src_root, opts, src_repo) for dest in dests}
    for dest in dests:
        _print_candidates(dest.name, candidates_by_dest[dest.name], src_root)

    if conflicts := _conflict_labels(candidates_by_dest, src_root):
        typer.echo("\nConflicts found; nothing written:", err=True)
        for label in conflicts:
            typer.echo(f"  {label}", err=True)
        raise typer.Exit(1)
    if duplicates := _duplicate_conflicts(candidates_by_dest, src_root):
        typer.echo("\nDestinations disagree on the same unit; nothing written:", err=True)
        for label in duplicates:
            typer.echo(f"  {label}", err=True)
        raise typer.Exit(1)

    if opts.dry_run:
        return

    changed = [dest for dest in dests if candidates_by_dest[dest.name]]
    if not changed:
        typer.echo("Nothing to merge.", err=True)
        return

    _apply_and_report(src_root, src_repo, changed, candidates_by_dest)

    for dest in changed:
        typer.echo(f"path-sync copy -n {config.name} -d {dest.name}", err=True)


@app.command()
def merge(
    name: str = typer.Option("", "-n", "--name", help="Config name"),
    config_path_opt: str = typer.Option("", "-c", "--config-path", help="Full path to config file"),
    src_root_opt: str = typer.Option("", "--src-root", help="Source repo root"),
    dest_filter: list[str] = typer.Option(
        _EMPTY_STR_LIST, "-d", "--dest", help="Destination filter (repeatable or comma-separated)"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print classifications without writing"),
    include: list[str] = _INCLUDE_OPTION,
    exclude: list[str] = _EXCLUDE_OPTION,
) -> None:
    """Reconcile destination changes into src before the next copy.

    Recovers the last-synced base from both repos' histories, prefers the changed side, and
    combines non-overlapping changes. Writes and commits src, then prints the copy hint.
    merge never runs copy.
    """
    if name and config_path_opt:
        logger.error("Cannot use both --name and --config-path")
        raise typer.Exit(1)
    if not name and not config_path_opt:
        logger.error("Either --name or --config-path is required")
        raise typer.Exit(1)

    src_root = Path(src_root_opt) if src_root_opt else find_repo_root(Path.cwd())
    config_path = Path(config_path_opt) if config_path_opt else resolve_config_path(src_root, name)
    if not config_path.exists():
        logger.error(f"Config not found: {config_path}")
        raise typer.Exit(1)

    config = load_yaml_model(config_path, SrcConfig)
    opts = MergeOptions(dry_run=dry_run, include=include, exclude=exclude)

    try:
        _run_merge(config, src_root, _parse_dest_filter(dest_filter), opts)
    except ValueError as e:
        logger.error(f"Merge failed: {e}")
        raise typer.Exit(1)
