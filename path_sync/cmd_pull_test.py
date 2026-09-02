import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from git import Repo
from typer.testing import CliRunner

from path_sync._internal import git_ops, prompt_utils
from path_sync._internal.cmd_pull import (
    PullKind,
    PullOptions,
    _apply_candidate,
    _collect_mapped_candidates,
    _run_pull,
    _validate_dest_name,
)
from path_sync._internal.header import add_header, has_header
from path_sync._internal.models import Destination, PathMapping, SrcConfig, SyncMode
from path_sync._internal.typer_app import app

runner = CliRunner()

OLD = "2026-08-01T00:00:00+0000"
NEW = "2026-09-01T00:00:00+0000"
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


def _pull_setup(tmp_path):
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
    config = SrcConfig(name=CONFIG_NAME, paths=[PathMapping(src_path="justfile")])
    dest = Destination(name="dest", dest_path_relative="../dest")
    return src_root, dest_root, src_repo, dest_repo, config, dest


def _sectioned(content: str, trailer: str = "") -> str:
    body = f"""\
# === DO_NOT_EDIT: path-sync standard ===
{content}
# === OK_EDIT: path-sync standard ==="""
    if trailer:
        body += f"\n{trailer}"
    return body


def test_validate_dest_name_rejects_comma():
    with pytest.raises(ValueError, match="Exactly one"):
        _validate_dest_name("a,b")


def test_collect_sectioned_dest_newer(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    src_file = src_root / "justfile"
    dest_file = dest_root / "justfile"
    _commit_file(src_repo, src_root, "justfile", _sectioned("old"), OLD)
    dest_body = add_header(
        _sectioned("new dest body", "# dest-only trailer"),
        dest_file,
        CONFIG_NAME,
    )
    _commit_file(dest_repo, dest_root, "justfile", dest_body, NEW)

    candidates = _collect_mapped_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert len(candidates) == 1
    assert candidates[0].kind == PullKind.SECTIONS
    _apply_candidate(candidates[0])
    result = src_file.read_text()
    assert "new dest body" in result
    assert "dest-only trailer" not in result


def test_collect_json_whole_file(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    config.paths = [PathMapping(src_path=".cursor/cli.json", sync_mode=SyncMode.REPLACE)]
    src_file = src_root / ".cursor" / "cli.json"
    _commit_file(src_repo, src_root, ".cursor/cli.json", '{"old": true}\n', OLD)
    _commit_file(dest_repo, dest_root, ".cursor/cli.json", '{"new": true}\n', NEW)

    candidates = _collect_mapped_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert len(candidates) == 1
    assert candidates[0].kind == PullKind.WHOLE
    _apply_candidate(candidates[0])
    assert src_file.read_text() == '{"new": true}\n'


def test_skip_equal_json_no_error(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    config.paths = [PathMapping(src_path=".cursor/cli.json", sync_mode=SyncMode.REPLACE)]
    body = '{"same": true}\n'
    _commit_file(src_repo, src_root, ".cursor/cli.json", body, OLD)
    _commit_file(dest_repo, dest_root, ".cursor/cli.json", body, NEW)

    candidates = _collect_mapped_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert candidates == []


def test_collect_whole_file_strips_header(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    config.paths = [PathMapping(src_path="rule.mdc")]
    src_file = src_root / "rule.mdc"
    dest_file = dest_root / "rule.mdc"
    _commit_file(src_repo, src_root, "rule.mdc", "old rule", OLD)
    _commit_file(
        dest_repo,
        dest_root,
        "rule.mdc",
        add_header("new rule", dest_file, CONFIG_NAME),
        NEW,
    )

    candidates = _collect_mapped_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert len(candidates) == 1
    assert candidates[0].kind == PullKind.WHOLE
    _apply_candidate(candidates[0])
    assert src_file.read_text() == "new rule"
    assert not has_header(src_file.read_text())


def test_skip_dest_only_path(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    dest_file = dest_root / "justfile"
    _commit_file(
        dest_repo,
        dest_root,
        "justfile",
        add_header("only dest", dest_file, CONFIG_NAME),
        NEW,
    )
    candidates = _collect_mapped_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert candidates == []


def test_skip_dest_dirty(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    dest_file = dest_root / "justfile"
    _commit_file(src_repo, src_root, "justfile", _sectioned("src"), OLD)
    _commit_file(
        dest_repo,
        dest_root,
        "justfile",
        add_header(_sectioned("dest"), dest_file, CONFIG_NAME),
        NEW,
    )
    dest_file.write_text(dest_file.read_text() + "\n# unstaged")
    candidates = _collect_mapped_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert candidates == []


def test_skip_equal_content_no_git_log(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    dest_file = dest_root / "justfile"
    body = add_header(_sectioned("same"), dest_file, CONFIG_NAME)
    _commit_file(src_repo, src_root, "justfile", _sectioned("same"), OLD)
    _commit_file(dest_repo, dest_root, "justfile", body, NEW)

    with patch.object(git_ops, "file_last_commit_unix") as log_mock:
        candidates = _collect_mapped_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
        assert candidates == []
        log_mock.assert_not_called()


def test_skip_dest_older(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    dest_file = dest_root / "justfile"
    _commit_file(src_repo, src_root, "justfile", _sectioned("src newer"), NEW)
    _commit_file(
        dest_repo,
        dest_root,
        "justfile",
        add_header(_sectioned("dest older"), dest_file, CONFIG_NAME),
        OLD,
    )
    candidates = _collect_mapped_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert candidates == []


def test_skip_sections_preserved(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    dest = Destination(
        name="dest",
        dest_path_relative="../dest",
        skip_sections={"justfile": ["dev"]},
    )
    dest_file = dest_root / "justfile"
    src_body = (
        _sectioned("standard") + "\n# === DO_NOT_EDIT: path-sync dev ===\nkeep-me\n# === OK_EDIT: path-sync dev ==="
    )
    _commit_file(src_repo, src_root, "justfile", src_body, OLD)
    dest_body = add_header(
        _sectioned("new-standard")
        + "\n# === DO_NOT_EDIT: path-sync dev ===\nfrom-dest\n# === OK_EDIT: path-sync dev ===",
        dest_file,
        CONFIG_NAME,
    )
    _commit_file(dest_repo, dest_root, "justfile", dest_body, NEW)

    candidates = _collect_mapped_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    _apply_candidate(candidates[0])
    result = (src_root / "justfile").read_text()
    assert "new-standard" in result
    assert "keep-me" in result
    assert "from-dest" not in result


def test_skip_scaffold_mode(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    config.paths = [PathMapping(src_path="justfile", sync_mode=SyncMode.SCAFFOLD)]
    dest_file = dest_root / "justfile"
    _commit_file(src_repo, src_root, "justfile", "src", OLD)
    _commit_file(
        dest_repo,
        dest_root,
        "justfile",
        add_header("dest scaffold", dest_file, CONFIG_NAME),
        NEW,
    )
    candidates = _collect_mapped_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert candidates == []


def test_run_pull_dry_run_no_write(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    dest_file = dest_root / "justfile"
    _commit_file(src_repo, src_root, "justfile", _sectioned("src"), OLD)
    _commit_file(
        dest_repo,
        dest_root,
        "justfile",
        add_header(_sectioned("dest newer"), dest_file, CONFIG_NAME),
        NEW,
    )
    src_before = (src_root / "justfile").read_text()
    _run_pull(config, dest, src_root, PullOptions(dry_run=True))
    assert (src_root / "justfile").read_text() == src_before


def test_prompt_pull_confirm_non_tty():
    with patch.object(sys.stdin, "isatty", return_value=False):
        assert not prompt_utils.prompt_pull_confirm("Confirm?")


def test_prompt_pull_confirm_yes():
    with (
        patch.object(sys.stdin, "isatty", return_value=True),
        patch("builtins.input", return_value="y"),
    ):
        assert prompt_utils.prompt_pull_confirm("Confirm?")


def test_prompt_pull_confirm_eof():
    with (
        patch.object(sys.stdin, "isatty", return_value=True),
        patch("builtins.input", side_effect=EOFError),
    ):
        assert not prompt_utils.prompt_pull_confirm("Confirm?")


def test_run_pull_applies_on_confirm(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    dest_file = dest_root / "justfile"
    _commit_file(src_repo, src_root, "justfile", _sectioned("src"), OLD)
    _commit_file(
        dest_repo,
        dest_root,
        "justfile",
        add_header(_sectioned("applied"), dest_file, CONFIG_NAME),
        NEW,
    )
    with (
        patch.object(sys.stdin, "isatty", return_value=True),
        patch.object(prompt_utils, "prompt_pull_confirm", return_value=True),
    ):
        _run_pull(config, dest, src_root, PullOptions())
    assert "applied" in (src_root / "justfile").read_text()


def test_pull_cli_rejects_comma_dest(tmp_path):
    src_root = tmp_path / "src"
    src_root.mkdir()
    Repo.init(src_root)
    (src_root / ".github").mkdir()
    (src_root / ".github" / "test-config.src.yaml").write_text(
        "name: test-config\ndestinations:\n  - name: dest\n    dest_path_relative: ../dest\n"
    )
    result = runner.invoke(app, ["pull", "-n", "test-config", "-d", "a,b", "--src-root", str(src_root)])
    assert result.exit_code == 1
