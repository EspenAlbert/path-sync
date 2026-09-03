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
    _collect_dest_only_candidates,
    _collect_mapped_candidates,
    _format_candidate_line,
    _keep_pull_path,
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


def test_validate_dest_name_rejects_empty():
    with pytest.raises(ValueError, match="Missing destination"):
        _validate_dest_name("   ")


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


def test_skip_src_dirty(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    dest_file = dest_root / "justfile"
    src_file = src_root / "justfile"
    _commit_file(src_repo, src_root, "justfile", _sectioned("src"), OLD)
    _commit_file(
        dest_repo,
        dest_root,
        "justfile",
        add_header(_sectioned("dest newer"), dest_file, CONFIG_NAME),
        NEW,
    )
    src_file.write_text(src_file.read_text() + "\n# unstaged")
    candidates = _collect_mapped_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert candidates == []


def test_skip_opted_out_sync(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    _commit_file(src_repo, src_root, "justfile", _sectioned("src"), OLD)
    _commit_file(dest_repo, dest_root, "justfile", _sectioned("dest newer"), NEW)
    candidates = _collect_mapped_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert candidates == []


def test_collect_mapped_binary(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    config.paths = [PathMapping(src_path="assets/logo.bin")]
    src_payload = b"\x80\x81\x82"
    dest_payload = b"\x80\x81\x83"
    src_path = src_root / "assets/logo.bin"
    dest_path = dest_root / "assets/logo.bin"
    src_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    src_path.write_bytes(src_payload)
    dest_path.write_bytes(dest_payload)
    src_repo.index.add(["assets/logo.bin"])
    dest_repo.index.add(["assets/logo.bin"])
    src_repo.git.commit("-m", "src", env={**os.environ, "GIT_AUTHOR_DATE": OLD, "GIT_COMMITTER_DATE": OLD})
    dest_repo.git.commit("-m", "dest", env={**os.environ, "GIT_AUTHOR_DATE": NEW, "GIT_COMMITTER_DATE": NEW})
    candidates = _collect_mapped_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert len(candidates) == 1
    assert candidates[0].kind == PullKind.BINARY
    line = _format_candidate_line(candidates[0], src_root)
    assert "binary" in line
    _apply_candidate(candidates[0])
    assert src_path.read_bytes() == dest_payload


def test_run_pull_rejects_non_git_dest(tmp_path):
    src_root, _dest_root, _src_repo, _dest_repo, config, dest = _pull_setup(tmp_path)
    dest.dest_path_relative = "../missing"
    with pytest.raises(ValueError, match="Not a git repository"):
        _run_pull(config, dest, src_root, PullOptions())


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


def _confirm_pull(config, dest, src_root, opts: PullOptions) -> None:
    with (
        patch.object(sys.stdin, "isatty", return_value=True),
        patch.object(prompt_utils, "prompt_pull_confirm", return_value=True),
    ):
        _run_pull(config, dest, src_root, opts)


def _cursor_dir_setup(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    config.paths = [PathMapping(src_path=".cursor", sync_mode=SyncMode.REPLACE)]
    _commit_file(src_repo, src_root, ".cursor/rules/foo.mdc", "foo", OLD)
    _commit_file(dest_repo, dest_root, ".cursor/rules/foo.mdc", "foo", OLD)
    return src_root, dest_root, src_repo, dest_repo, config, dest


def test_dest_only_absent_without_flag(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _cursor_dir_setup(tmp_path)
    (dest_root / ".cursor/rules/bar.mdc").write_text("dest only")
    assert _collect_mapped_candidates(config, dest, src_root, dest_root, src_repo, dest_repo) == []
    _run_pull(config, dest, src_root, PullOptions(dry_run=True))
    assert not (src_root / ".cursor/rules/bar.mdc").exists()


def test_dest_only_untracked_copies_to_src(tmp_path):
    src_root, dest_root, *_rest, config, dest = _cursor_dir_setup(tmp_path)
    dest_file = dest_root / ".cursor/rules/bar.mdc"
    dest_file.write_text(add_header("from dest", dest_file, CONFIG_NAME))
    _confirm_pull(config, dest, src_root, PullOptions(dest_only=True))
    src_file = src_root / ".cursor/rules/bar.mdc"
    assert src_file.read_text() == "from dest"
    assert not has_header(src_file.read_text())


def test_dest_only_tracked_clean_skips_git_log(tmp_path):
    src_root, dest_root, _src_repo, dest_repo, config, dest = _cursor_dir_setup(tmp_path)
    _commit_file(dest_repo, dest_root, ".cursor/rules/bar.mdc", "committed dest-only", NEW)
    with patch.object(git_ops, "file_last_commit_unix") as log_mock:
        candidates = _collect_dest_only_candidates(config, dest, src_root, dest_root, dest_repo, set())
        assert len(candidates) == 1
        assert candidates[0].dest_only
        log_mock.assert_not_called()
    line = _format_candidate_line(candidates[0], src_root)
    assert "dest-only" in line
    assert "dest 20" not in line


def test_dest_only_tracked_dirty_skips(tmp_path):
    src_root, dest_root, _src_repo, dest_repo, config, dest = _cursor_dir_setup(tmp_path)
    dest_file = dest_root / ".cursor/rules/bar.mdc"
    _commit_file(dest_repo, dest_root, ".cursor/rules/bar.mdc", "committed", NEW)
    dest_file.write_text("unstaged edit")
    candidates = _collect_dest_only_candidates(config, dest, src_root, dest_root, dest_repo, set())
    assert candidates == []
    _run_pull(config, dest, src_root, PullOptions(dest_only=True, dry_run=True))
    assert not (src_root / ".cursor/rules/bar.mdc").exists()


def test_dest_only_leaves_src_yaml_unchanged(tmp_path):
    src_root, dest_root, *_rest, config, dest = _cursor_dir_setup(tmp_path)
    yaml_path = src_root / ".github" / f"{CONFIG_NAME}.src.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_before = b"name: test-config\npaths:\n  - src_path: .cursor\n    sync_mode: replace\n"
    yaml_path.write_bytes(yaml_before)
    (dest_root / ".cursor/rules/bar.mdc").write_text("new rule")
    paths_before = list(config.paths)
    _confirm_pull(config, dest, src_root, PullOptions(dest_only=True))
    assert yaml_path.read_bytes() == yaml_before
    assert config.paths == paths_before


def test_dest_only_additive_after_mapped(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    config.paths = [
        PathMapping(src_path="justfile"),
        PathMapping(src_path=".cursor", sync_mode=SyncMode.REPLACE),
    ]
    dest_just = dest_root / "justfile"
    _commit_file(src_repo, src_root, "justfile", _sectioned("src"), OLD)
    _commit_file(dest_repo, dest_root, "justfile", add_header(_sectioned("dest newer"), dest_just, CONFIG_NAME), NEW)
    (dest_root / ".cursor/rules/bar.mdc").parent.mkdir(parents=True, exist_ok=True)
    (dest_root / ".cursor/rules/bar.mdc").write_text("dest only")
    mapped = _collect_mapped_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    dest_only = _collect_dest_only_candidates(
        config, dest, src_root, dest_root, dest_repo, {c.dest_key for c in mapped}
    )
    assert [c.dest_key for c in mapped + dest_only] == ["justfile", ".cursor/rules/bar.mdc"]
    assert dest_only[0].dest_only
    _confirm_pull(config, dest, src_root, PullOptions())
    assert "dest newer" in (src_root / "justfile").read_text()
    assert not (src_root / ".cursor/rules/bar.mdc").exists()


@pytest.mark.parametrize(
    ("mapping", "dest_rel", "src_rel"),
    [
        (PathMapping(src_path="justfile"), "justfile", "justfile"),
        (PathMapping(src_path="docs/00_background/*.md"), "docs/00_background/new.md", "docs/00_background/new.md"),
        (PathMapping(src_path=".cursor/rules", dest_path="rules"), "rules/bar.mdc", ".cursor/rules/bar.mdc"),
    ],
)
def test_dest_only_inverse_mappings(tmp_path, mapping, dest_rel, src_rel):
    src_root, dest_root, _src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    config.paths = [mapping]
    dest_file = dest_root / dest_rel
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    dest_file.write_text("new")
    candidates = _collect_dest_only_candidates(config, dest, src_root, dest_root, dest_repo, set())
    assert [c.src_path.relative_to(src_root).as_posix() for c in candidates] == [src_rel]


def test_dest_only_honors_copy_filters(tmp_path):
    src_root, dest_root, _src_repo, dest_repo, config, dest = _pull_setup(tmp_path)
    dest.skip_file_patterns = {".cursor/*.secret.mdc"}
    config.paths = [
        PathMapping(src_path=".cursor", sync_mode=SyncMode.REPLACE, exclude_file_patterns={"*.pyc"}),
        PathMapping(src_path="scaffold", sync_mode=SyncMode.SCAFFOLD),
    ]
    files = [
        ".cursor/foo.secret.mdc",
        ".cursor/foo.pyc",
        ".cursor/__pycache__/mod.py",
        "scaffold/extra.md",
        ".cursor/keep.mdc",
    ]
    for rel in files:
        path = dest_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    candidates = _collect_dest_only_candidates(config, dest, src_root, dest_root, dest_repo, set())
    assert [c.dest_key for c in candidates] == [".cursor/keep.mdc"]


def test_dest_only_binary_copies_bytes(tmp_path):
    src_root, dest_root, *_rest, config, dest = _cursor_dir_setup(tmp_path)
    payload = b"\x80\x81\x82"
    (dest_root / ".cursor/rules/blob.bin").write_bytes(payload)
    _confirm_pull(config, dest, src_root, PullOptions(dest_only=True))
    assert (src_root / ".cursor/rules/blob.bin").read_bytes() == payload


def test_dest_only_dry_run_no_write(tmp_path):
    src_root, dest_root, *_rest, config, dest = _cursor_dir_setup(tmp_path)
    (dest_root / ".cursor/rules/bar.mdc").write_text("dest only")
    _run_pull(config, dest, src_root, PullOptions(dest_only=True, dry_run=True))
    assert not (src_root / ".cursor/rules/bar.mdc").exists()


def _dest_only_mixed_setup(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _cursor_dir_setup(tmp_path)
    config.paths.append(PathMapping(src_path="docs/00_background/*.md", sync_mode=SyncMode.REPLACE))
    return src_root, dest_root, src_repo, dest_repo, config, dest


@pytest.mark.parametrize(
    ("rel", "include", "exclude", "keep"),
    [
        (".cursor/rules/bar.mdc", [".cursor/*"], [], True),
        ("docs/00_background/new.md", [".cursor/*"], [], False),
        (".cursor/rules/bar.mdc", [], ["docs/*"], True),
        ("docs/00_background/new.md", [], ["docs/*"], False),
        (".cursor/rules/a.mdc", [".cursor/*"], [".cursor/skills/*"], True),
        (".cursor/skills/b.md", [".cursor/*"], [".cursor/skills/*"], False),
        ("justfile", ["justfile"], [], True),
        (".cursor/rules/foo.mdc", ["justfile"], [], False),
        ("docs/x.md", ["missing/*"], [], False),
    ],
)
def test_keep_pull_path(rel, include, exclude, keep):
    assert _keep_pull_path(rel, include, exclude) is keep


def test_run_pull_include_filters_dest_only(tmp_path):
    src_root, dest_root, *_rest, config, dest = _dest_only_mixed_setup(tmp_path)
    (dest_root / ".cursor/rules/bar.mdc").write_text("cursor")
    docs = dest_root / "docs/00_background/new.md"
    docs.parent.mkdir(parents=True, exist_ok=True)
    docs.write_text("doc")
    _confirm_pull(config, dest, src_root, PullOptions(dest_only=True, include=[".cursor/*"]))
    assert (src_root / ".cursor/rules/bar.mdc").read_text() == "cursor"
    assert not (src_root / "docs/00_background/new.md").exists()


def test_run_pull_filter_empty(capsys, tmp_path):
    src_root, dest_root, *_rest, config, dest = _dest_only_mixed_setup(tmp_path)
    (dest_root / ".cursor/rules/bar.mdc").write_text("cursor")
    _run_pull(config, dest, src_root, PullOptions(dest_only=True, include=["missing/*"]))
    assert "No pull candidates." in capsys.readouterr().err
    assert not (src_root / ".cursor/rules/bar.mdc").exists()


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


def test_pull_cli_rejects_empty_dest(tmp_path):
    src_root = tmp_path / "src"
    src_root.mkdir()
    Repo.init(src_root)
    (src_root / ".github").mkdir()
    (src_root / ".github" / "test-config.src.yaml").write_text(
        "name: test-config\ndestinations:\n  - name: dest\n    dest_path_relative: ../dest\n"
    )
    result = runner.invoke(app, ["pull", "-n", "test-config", "-d", " ", "--src-root", str(src_root)])
    assert result.exit_code == 1


def test_pull_cli_rejects_both_name_and_config_path(tmp_path):
    src_root = tmp_path / "src"
    src_root.mkdir()
    Repo.init(src_root)
    result = runner.invoke(
        app,
        ["pull", "-n", "cfg", "-c", "/tmp/cfg.yaml", "-d", "dest", "--src-root", str(src_root)],
    )
    assert result.exit_code == 1


def test_pull_cli_requires_config_selector(tmp_path):
    src_root = tmp_path / "src"
    src_root.mkdir()
    Repo.init(src_root)
    result = runner.invoke(app, ["pull", "-d", "dest", "--src-root", str(src_root)])
    assert result.exit_code == 1
