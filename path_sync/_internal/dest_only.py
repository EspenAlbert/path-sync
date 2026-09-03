from __future__ import annotations

import logging
from pathlib import Path
from typing import NamedTuple

from git import Repo

from path_sync._internal import git_ops, header
from path_sync._internal.models import Destination, PathMapping, SrcConfig, SyncMode

logger = logging.getLogger(__name__)


class DestOnlyFile(NamedTuple):
    src_path: Path
    dest_path: Path
    dest_key: str
    sync_mode: SyncMode


class _DestFileMap(NamedTuple):
    src_path: Path
    dest_key: str


def is_opted_out(dest_text: str, sync_mode: SyncMode) -> bool:
    return sync_mode == SyncMode.SYNC and not header.has_header(dest_text)


def prune_eligible(files: list[DestOnlyFile]) -> list[DestOnlyFile]:
    eligible: list[DestOnlyFile] = []
    for row in files:
        try:
            dest_text = row.dest_path.read_text()
        except UnicodeDecodeError:
            eligible.append(row)
            continue
        if not is_opted_out(dest_text, row.sync_mode):
            eligible.append(row)
    return eligible


def _src_for_dest_file(
    mapping: PathMapping,
    dest_path: Path,
    src_root: Path,
    dest_root: Path,
) -> _DestFileMap | None:
    if "*" in mapping.src_path:
        glob_prefix = mapping.src_path.split("*")[0].rstrip("/")
        dest_base = mapping.dest_path or glob_prefix
        src_base = glob_prefix
    elif (dest_root / mapping.resolved_dest_path()).is_dir():
        dest_base = mapping.resolved_dest_path()
        src_base = mapping.src_path
    elif dest_path == dest_root / mapping.resolved_dest_path():
        dest_base = mapping.resolved_dest_path()
        return _DestFileMap(src_root / mapping.src_path, dest_base)
    else:
        return None

    dest_anchor = dest_root / dest_base
    if dest_path.is_relative_to(dest_anchor):
        rel = dest_path.relative_to(dest_anchor)
        return _DestFileMap(src_root / src_base / rel, str(Path(dest_base) / rel))
    return None


def collect_dest_only_files(
    config: SrcConfig,
    dest: Destination,
    src_root: Path,
    dest_root: Path,
    dest_repo: Repo,
    skip_keys: set[str],
) -> list[DestOnlyFile]:
    files: list[DestOnlyFile] = []
    seen = set(skip_keys)
    for mapping in config.resolve_paths(dest):
        if mapping.sync_mode == SyncMode.SCAFFOLD:
            continue
        for dest_path in mapping.expand_dest_paths(dest_root):
            if dest_path.is_dir() or mapping.is_excluded(dest_path):
                continue
            mapped = _src_for_dest_file(mapping, dest_path, src_root, dest_root)
            if mapped is None:
                continue
            if dest.is_skipped(mapped.dest_key) or mapped.src_path.exists() or mapped.dest_key in seen:
                continue
            if git_ops.path_is_tracked_dirty(dest_repo, dest_path):
                logger.warning(f"Skipping dirty dest path: {dest_path}")
                continue
            seen.add(mapped.dest_key)
            files.append(
                DestOnlyFile(
                    src_path=mapped.src_path,
                    dest_path=dest_path,
                    dest_key=mapped.dest_key,
                    sync_mode=mapping.sync_mode,
                )
            )
    return files
