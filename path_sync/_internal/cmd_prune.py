from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer
from pydantic import BaseModel, Field

from path_sync._internal import git_ops, prompt_utils
from path_sync._internal.cmd_pull import _EXCLUDE_OPTION, _INCLUDE_OPTION, _keep_pull_path, _validate_dest_name
from path_sync._internal.dest_only import collect_dest_only_files, prune_eligible
from path_sync._internal.models import Destination, SrcConfig, find_repo_root, resolve_config_path
from path_sync._internal.repo_utils import resolve_repo_path
from path_sync._internal.typer_app import app
from path_sync._internal.yaml_utils import load_yaml_model

logger = logging.getLogger(__name__)


class PruneOptions(BaseModel):
    dry_run: bool = False
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


def _run_prune(config: SrcConfig, dest: Destination, src_root: Path, opts: PruneOptions) -> None:
    dest_root = resolve_repo_path(dest, src_root, "")
    if not git_ops.is_git_repo(dest_root):
        raise ValueError(f"Not a git repository: {dest_root}")

    dest_repo = git_ops.get_repo(dest_root)
    files = prune_eligible(collect_dest_only_files(config, dest, src_root, dest_root, dest_repo, set()))
    files = [
        row for row in files if _keep_pull_path(str(row.dest_path.relative_to(dest_root)), opts.include, opts.exclude)
    ]

    if not files:
        typer.echo("No prune candidates.", err=True)
        return

    typer.echo(f"\nPrune dest-only files in {dest.name}?\n", err=True)
    for row in files:
        typer.echo(str(row.dest_path.relative_to(dest_root)), err=True)

    if opts.dry_run or not sys.stdin.isatty():
        return
    if prompt_utils.prompt_pull_confirm("Confirm?"):
        for row in files:
            row.dest_path.unlink()
            logger.info(f"Pruned: {row.dest_path}")


@app.command()
def prune(
    name: str = typer.Option("", "-n", "--name", help="Config name"),
    config_path_opt: str = typer.Option("", "-c", "--config-path", help="Full path to config file"),
    src_root_opt: str = typer.Option("", "--src-root", help="Source repo root"),
    dest_name: str = typer.Option(..., "-d", "--dest", help="Destination name (exactly one)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print candidates without deleting"),
    include: list[str] = _INCLUDE_OPTION,
    exclude: list[str] = _EXCLUDE_OPTION,
) -> None:
    """Delete dest-only files after one confirm.

    Quote glob patterns (e.g. -i '.cursor/*').
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
    opts = PruneOptions(dry_run=dry_run, include=include, exclude=exclude)

    try:
        _run_prune(config, dest, src_root, opts)
    except ValueError as e:
        logger.error(f"Prune failed: {e}")
        raise typer.Exit(1)
