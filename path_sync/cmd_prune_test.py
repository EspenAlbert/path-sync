import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from git import Repo
from typer.testing import CliRunner

from path_sync._internal import prompt_utils
from path_sync._internal.cmd_prune import PruneOptions, _run_prune
from path_sync._internal.dest_only import collect_dest_only_files, prune_eligible
from path_sync._internal.models import Destination, PathMapping, SrcConfig, SyncMode
from path_sync._internal.typer_app import app

runner = CliRunner()
OLD = "2026-08-01T00:00:00+0000"
CONFIG_NAME = "test-config"


def _commit_file(repo: Repo, root: Path, rel: str, content: str, when: str = "") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    repo.index.add([rel])
    env = os.environ.copy()
    if when:
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    repo.git.commit("-m", "commit", env=env)


def _cursor_setup(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    src_root = workspace / "src"
    dest_root = workspace / "dest"
    src_root.mkdir()
    dest_root.mkdir()
    src_repo = Repo.init(src_root)
    dest_repo = Repo.init(dest_root)
    _commit_file(src_repo, src_root, ".gitkeep", "", OLD)
    _commit_file(dest_repo, dest_root, ".gitkeep", "", OLD)
    config = SrcConfig(name=CONFIG_NAME, paths=[PathMapping(src_path=".cursor", sync_mode=SyncMode.REPLACE)])
    dest = Destination(name="dest", dest_path_relative="../dest")
    _commit_file(src_repo, src_root, ".cursor/rules/foo.mdc", "foo", OLD)
    _commit_file(dest_repo, dest_root, ".cursor/rules/foo.mdc", "foo", OLD)
    return src_root, dest_root, src_repo, dest_repo, config, dest


def _confirm_prune(config, dest, src_root, opts: PruneOptions):
    with (
        patch.object(sys.stdin, "isatty", return_value=True),
        patch.object(prompt_utils, "prompt_pull_confirm", return_value=True),
    ):
        _run_prune(config, dest, src_root, opts)


def test_prune_deletes_dest_extra(tmp_path):
    src_root, dest_root, *_rest, config, dest = _cursor_setup(tmp_path)
    extra = dest_root / ".cursor/rules/bar.mdc"
    extra.write_text("dest only")
    _confirm_prune(config, dest, src_root, PruneOptions())
    assert not extra.exists()
    assert (dest_root / ".cursor/rules/foo.mdc").exists()
    assert not (src_root / ".cursor/rules/bar.mdc").exists()


@pytest.mark.parametrize("opts", [PruneOptions(dry_run=True)])
def test_prune_no_write_opts(tmp_path, opts):
    src_root, dest_root, *_rest, config, dest = _cursor_setup(tmp_path)
    extra = dest_root / ".cursor/rules/bar.mdc"
    extra.write_text("dest only")
    _run_prune(config, dest, src_root, opts)
    assert extra.exists()


def test_prune_non_tty_no_unlink(tmp_path):
    src_root, dest_root, *_rest, config, dest = _cursor_setup(tmp_path)
    extra = dest_root / ".cursor/rules/bar.mdc"
    extra.write_text("dest only")
    with patch.object(sys.stdin, "isatty", return_value=False):
        _run_prune(config, dest, src_root, PruneOptions())
    assert extra.exists()


def test_prune_tracked_dirty_skips(tmp_path):
    src_root, dest_root, _src_repo, dest_repo, config, dest = _cursor_setup(tmp_path)
    extra = dest_root / ".cursor/rules/bar.mdc"
    _commit_file(dest_repo, dest_root, ".cursor/rules/bar.mdc", "committed", OLD)
    extra.write_text("dirty")
    _confirm_prune(config, dest, src_root, PruneOptions())
    assert extra.exists()


def test_prune_skip_file_patterns(tmp_path):
    src_root, dest_root, _src_repo, _dest_repo, config, dest = _cursor_setup(tmp_path)
    dest.skip_file_patterns = {".cursor/*.secret.mdc"}
    for rel in (".cursor/keep.mdc", ".cursor/secret.secret.mdc"):
        path = dest_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    _confirm_prune(config, dest, src_root, PruneOptions())
    assert not (dest_root / ".cursor/keep.mdc").exists()
    assert (dest_root / ".cursor/secret.secret.mdc").exists()


def test_prune_opted_out_kept(tmp_path):
    src_root, dest_root, *_rest, config, dest = _cursor_setup(tmp_path)
    config.paths = [PathMapping(src_path="justfile")]
    dest_file = dest_root / "justfile"
    dest_file.write_text("opted out")
    _confirm_prune(config, dest, src_root, PruneOptions())
    assert dest_file.exists()


def test_prune_include_exclude(tmp_path):
    src_root, dest_root, *_rest, config, dest = _cursor_setup(tmp_path)
    config.paths.append(PathMapping(src_path="docs/00_background/*.md", sync_mode=SyncMode.REPLACE))
    (dest_root / ".cursor/rules/bar.mdc").write_text("cursor")
    docs = dest_root / "docs/00_background/new.md"
    docs.parent.mkdir(parents=True, exist_ok=True)
    docs.write_text("doc")
    _confirm_prune(config, dest, src_root, PruneOptions(include=[".cursor/*"]))
    assert not (dest_root / ".cursor/rules/bar.mdc").exists()
    assert docs.exists()


def test_prune_single_file_mapping(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    src_root = workspace / "src"
    dest_root = workspace / "dest"
    src_root.mkdir()
    dest_root.mkdir()
    Repo.init(src_root)
    Repo.init(dest_root)
    config = SrcConfig(name=CONFIG_NAME, paths=[PathMapping(src_path="LICENSE", sync_mode=SyncMode.REPLACE)])
    dest = Destination(name="dest", dest_path_relative="../dest")
    license_file = dest_root / "LICENSE"
    license_file.write_text("MIT")
    _confirm_prune(config, dest, src_root, PruneOptions())
    assert not license_file.exists()


def test_prune_cli_rejects_bad_dest():
    result = runner.invoke(app, ["prune", "-n", "cfg", "-d", "a,b"])
    assert result.exit_code == 1


def test_prune_cli_rejects_y_flag(tmp_path):
    src_root, _dest_root, *_rest, _config, dest = _cursor_setup(tmp_path)
    config_path = src_root / f"{CONFIG_NAME}.src.yaml"
    config_path.write_text(
        f"name: {CONFIG_NAME}\n"
        "paths:\n"
        "  - src_path: .cursor\n"
        "    sync_mode: replace\n"
        "destinations:\n"
        f"  - name: {dest.name}\n"
        "    dest_path_relative: ../dest\n"
    )
    result = runner.invoke(
        app,
        ["prune", "-c", str(config_path), "--src-root", str(src_root), "-d", dest.name, "-y"],
    )
    assert result.exit_code != 0


def test_readme_contrast():
    readme = Path(__file__).resolve().parents[1] / "README.md"
    text = readme.read_text()
    assert "path-sync prune" in text
    assert "copy orphans" in text.lower() or "orphaned" in text.lower()
    assert "--dest-only" in text


def test_prune_no_candidates(capsys, tmp_path):
    src_root, _dest_root, *_rest, config, dest = _cursor_setup(tmp_path)
    _run_prune(config, dest, src_root, PruneOptions())
    assert "No prune candidates." in capsys.readouterr().err


def test_prune_deletes_binary_dest_extra(tmp_path):
    src_root, dest_root, *_rest, config, dest = _cursor_setup(tmp_path)
    extra = dest_root / ".cursor/rules/blob.bin"
    extra.write_bytes(b"\x80\x81\x82")
    _confirm_prune(config, dest, src_root, PruneOptions())
    assert not extra.exists()


def test_prune_skips_scaffold_mapping(tmp_path):
    src_root, dest_root, *_rest, config, dest = _cursor_setup(tmp_path)
    config.paths.append(PathMapping(src_path="scaffold", sync_mode=SyncMode.SCAFFOLD))
    scaffold_file = dest_root / "scaffold/extra.md"
    scaffold_file.parent.mkdir(parents=True, exist_ok=True)
    scaffold_file.write_text("x")
    _confirm_prune(config, dest, src_root, PruneOptions())
    assert scaffold_file.exists()


def test_prune_eligible_includes_binary(tmp_path):
    src_root, dest_root, *_rest, config, dest = _cursor_setup(tmp_path)
    extra = dest_root / ".cursor/rules/blob.bin"
    extra.write_bytes(b"\x80\x81\x82")
    dest_repo = Repo(dest_root)
    rows = prune_eligible(collect_dest_only_files(config, dest, src_root, dest_root, dest_repo, set()))
    assert [row.dest_path.name for row in rows] == ["blob.bin"]


def test_run_prune_rejects_non_git_dest(tmp_path):
    src_root, _dest_root, *_rest, config, dest = _cursor_setup(tmp_path)
    dest.dest_path_relative = "../missing"
    with pytest.raises(ValueError, match="Not a git repository"):
        _run_prune(config, dest, src_root, PruneOptions())


def test_prune_cli_rejects_both_name_and_config_path(tmp_path):
    src_root = tmp_path / "src"
    src_root.mkdir()
    Repo.init(src_root)
    result = runner.invoke(
        app,
        ["prune", "-n", "cfg", "-c", "/tmp/cfg.yaml", "-d", "dest", "--src-root", str(src_root)],
    )
    assert result.exit_code == 1


def test_prune_cli_requires_config_selector(tmp_path):
    src_root = tmp_path / "src"
    src_root.mkdir()
    Repo.init(src_root)
    result = runner.invoke(app, ["prune", "-d", "dest", "--src-root", str(src_root)])
    assert result.exit_code == 1


def test_prune_cli_config_not_found(tmp_path):
    src_root = tmp_path / "src"
    src_root.mkdir()
    Repo.init(src_root)
    result = runner.invoke(app, ["prune", "-n", "missing", "-d", "dest", "--src-root", str(src_root)])
    assert result.exit_code == 1


def test_prune_cli_non_git_dest(tmp_path):
    src_root, _dest_root, *_rest, _config, dest = _cursor_setup(tmp_path)
    config_path = src_root / f"{CONFIG_NAME}.src.yaml"
    config_path.write_text(
        f"name: {CONFIG_NAME}\n"
        "paths:\n"
        "  - src_path: .cursor\n"
        "    sync_mode: replace\n"
        "destinations:\n"
        f"  - name: {dest.name}\n"
        "    dest_path_relative: ../missing\n"
    )
    result = runner.invoke(
        app,
        ["prune", "-c", str(config_path), "--src-root", str(src_root), "-d", dest.name],
    )
    assert result.exit_code == 1


def test_prune_honors_path_exclude_patterns(tmp_path):
    src_root, dest_root, *_rest, config, dest = _cursor_setup(tmp_path)
    config.paths = [PathMapping(src_path=".cursor", sync_mode=SyncMode.REPLACE, exclude_file_patterns={"*.pyc"})]
    for rel in (".cursor/foo.pyc", ".cursor/keep.mdc"):
        path = dest_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    _confirm_prune(config, dest, src_root, PruneOptions())
    assert (dest_root / ".cursor/foo.pyc").exists()
    assert not (dest_root / ".cursor/keep.mdc").exists()
