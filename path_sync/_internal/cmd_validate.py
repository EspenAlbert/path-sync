from __future__ import annotations

import logging
from pathlib import Path

import typer

from path_sync._internal import git_ops
from path_sync._internal.models import find_repo_root
from path_sync._internal.typer_app import app
from path_sync._internal.validation import parse_skip_sections, validate_no_unauthorized_changes

logger = logging.getLogger(__name__)


@app.command("validate-no-changes")
def validate_no_changes(
    branch: str = typer.Option(
        "main",
        "-b",
        "--branch",
        help="Branch to compare against (default: main; uses GITHUB_BASE_REF when set and -b not passed)",
        envvar="GITHUB_BASE_REF",
    ),
    skip_sections_opt: str = typer.Option(
        "",
        "--skip-sections",
        help="Comma-separated path:section_id pairs to skip (e.g., 'justfile:coverage,pyproject.toml:default')",
    ),
    src_root_opt: str = typer.Option(
        "",
        "--src-root",
        help="Source repo root (default: find git root from cwd)",
    ),
) -> None:
    """Validate no unauthorized changes to synced files."""
    repo_root = Path(src_root_opt) if src_root_opt else find_repo_root(Path.cwd())
    repo = git_ops.get_repo(repo_root)

    current_branch = repo.active_branch.name
    if current_branch.startswith("sync/"):
        logger.info(f"On sync branch {current_branch}, validation skipped")
        return
    if current_branch == branch:
        logger.info(f"On base branch {branch}, validation skipped")
        return

    logger.info(f"Validating changes against branch {branch}")
    skip_sections = parse_skip_sections(skip_sections_opt) if skip_sections_opt else None
    unauthorized = validate_no_unauthorized_changes(repo_root, branch, skip_sections)

    if unauthorized:
        files_list = "\n  ".join(unauthorized)
        logger.error(f"Unauthorized changes in {len(unauthorized)} files:\n  {files_list}")
        raise typer.Exit(1)

    logger.info("Validation passed: no unauthorized changes")
