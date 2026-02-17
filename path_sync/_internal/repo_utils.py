from __future__ import annotations

import logging
import shutil
from pathlib import Path

from git import Repo

from path_sync._internal import git_ops, prompt_utils
from path_sync._internal.models import Destination

logger = logging.getLogger(__name__)


def resolve_repo_path(dest: Destination, src_root: Path, work_dir: str) -> Path:
    if work_dir:
        return Path(work_dir) / dest.name
    if dest.dest_path_relative:
        return (src_root / dest.dest_path_relative).resolve()
    raise ValueError(f"No dest_path_relative for {dest.name}, use --work-dir")


def ensure_repo(dest: Destination, repo_path: Path, dry_run: bool = False) -> Repo:
    if repo_path.exists():
        if git_ops.is_git_repo(repo_path):
            return git_ops.get_repo(repo_path)
        logger.warning(f"Invalid git repo at {repo_path}")
        if dry_run:
            raise ValueError(f"Invalid git repo at {repo_path}, cannot re-clone in dry-run mode")
        if not prompt_utils.prompt_confirm(f"Remove {repo_path} and re-clone?"):
            raise ValueError(f"Aborted: user declined to remove invalid repo at {repo_path}")
        shutil.rmtree(repo_path)
    if dry_run:
        raise ValueError(f"Destination repo not found: {repo_path}. Clone it first or run without --dry-run.")
    if not dest.repo_url:
        raise ValueError(f"Dest {dest.name} not found at {repo_path} and no repo_url configured")
    return git_ops.clone_repo(dest.repo_url, repo_path)
