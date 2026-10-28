import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from git import Repo
from typer.testing import CliRunner

from path_sync import sections
from path_sync._internal import prompt_utils
from path_sync._internal.cmd_merge import (
    MergeClassification,
    MergeOptions,
    UnitVersion,
    _apply_merge,
    _candidate_detail,
    _classify,
    _collect_merge_candidates,
    _merge_bodies,
    _run_merge,
)
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


def _merge_setup(tmp_path):
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
    dest = Destination(name="dest", dest_path_relative="../dest")
    config = SrcConfig(
        name=CONFIG_NAME,
        paths=[PathMapping(src_path="file.txt", sync_mode=SyncMode.REPLACE)],
        destinations=[dest],
    )
    return src_root, dest_root, src_repo, dest_repo, config, dest


def _two_sections(alpha: str, beta: str, trailer: str = "") -> str:
    body = (
        "# === DO_NOT_EDIT: path-sync alpha ===\n"
        f"{alpha}\n"
        "# === OK_EDIT: path-sync alpha ===\n"
        "# === DO_NOT_EDIT: path-sync beta ===\n"
        f"{beta}\n"
        "# === OK_EDIT: path-sync beta ==="
    )
    if trailer:
        body += f"\n{trailer}"
    return body


def _merge_setup_two_dests(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _merge_setup(tmp_path)
    dest2_root = tmp_path / "workspace" / "dest2"
    dest2_root.mkdir()
    dest2_repo = Repo.init(dest2_root)
    _commit_file(dest2_repo, dest2_root, ".gitkeep", "", OLD)
    dest2 = Destination(name="dest2", dest_path_relative="../dest2")
    config.destinations = [dest, dest2]
    return src_root, dest_root, dest2_root, src_repo, dest_repo, dest2_repo, config, dest, dest2


def _write_config(src_root: Path) -> None:
    config_path = src_root / ".github" / f"{CONFIG_NAME}.src.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        f"name: {CONFIG_NAME}\n"
        "paths:\n"
        "  - src_path: file.txt\n"
        "    sync_mode: replace\n"
        "destinations:\n"
        "  - name: dest\n"
        "    dest_path_relative: ../dest\n"
    )


def test_classify_only_dest_changed(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _merge_setup(tmp_path)
    _commit_file(src_repo, src_root, "file.txt", "base\n", OLD)
    _commit_file(dest_repo, dest_root, "file.txt", "base\n", OLD)
    _commit_file(dest_repo, dest_root, "file.txt", "dest-new\n", NEW)

    candidates = _collect_merge_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert len(candidates) == 1
    assert candidates[0].classification == MergeClassification.DEST_CHANGED


def test_classify_only_src_changed(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _merge_setup(tmp_path)
    _commit_file(src_repo, src_root, "file.txt", "base\n", OLD)
    _commit_file(dest_repo, dest_root, "file.txt", "base\n", OLD)
    _commit_file(src_repo, src_root, "file.txt", "src-new\n", NEW)

    candidates = _collect_merge_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert candidates == []


def test_classify_both_changed_merge(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _merge_setup(tmp_path)
    base = "line1\nline2\nline3\nline4\nline5\n"
    _commit_file(src_repo, src_root, "file.txt", base, OLD)
    _commit_file(dest_repo, dest_root, "file.txt", base, OLD)
    _commit_file(src_repo, src_root, "file.txt", "line1\nsrc-line2\nline3\nline4\nline5\n", NEW)
    _commit_file(dest_repo, dest_root, "file.txt", "line1\nline2\nline3\ndest-line4\nline5\n", NEW)

    candidates = _collect_merge_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert len(candidates) == 1
    assert candidates[0].classification == MergeClassification.MERGE
    assert not candidates[0].conflicted
    assert candidates[0].merged_body == "line1\nsrc-line2\nline3\ndest-line4\nline5\n"


def test_classify_no_common_base(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _merge_setup(tmp_path)
    _commit_file(src_repo, src_root, "file.txt", "aaa\n", OLD)
    _commit_file(dest_repo, dest_root, "file.txt", "bbb\n", OLD)

    candidates = _collect_merge_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert len(candidates) == 1
    assert candidates[0].classification == MergeClassification.NO_COMMON_BASE
    assert candidates[0].is_conflict


def test_classify_helper_uses_base():
    base = UnitVersion(body="base\n", commit_unix=1)
    assert _classify("base\n", "dest\n", base) == MergeClassification.DEST_CHANGED
    assert _classify("src\n", "base\n", base) == MergeClassification.SRC_CHANGED
    assert _classify("src\n", "dest\n", base) == MergeClassification.MERGE
    assert _classify("src\n", "dest\n", None) == MergeClassification.NO_COMMON_BASE


def test_merge_file_non_overlapping():
    base = "line1\nline2\nline3\nline4\nline5\n"
    merged, conflicted = _merge_bodies(
        base, "line1\nsrc-line2\nline3\nline4\nline5\n", "line1\nline2\nline3\ndest-line4\nline5\n"
    )
    assert not conflicted
    assert merged == "line1\nsrc-line2\nline3\ndest-line4\nline5\n"


def test_merge_file_overlapping_conflict():
    _merged, conflicted = _merge_bodies("line1\nline2\n", "src-change\nline2\n", "dest-change\nline2\n")
    assert conflicted


def test_merge_section_partial_change(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _merge_setup(tmp_path)
    config.paths = [PathMapping(src_path="justfile", sync_mode=SyncMode.REPLACE)]
    _commit_file(src_repo, src_root, "justfile", _two_sections("a-src", "b-src", "src trailer"), OLD)
    _commit_file(dest_repo, dest_root, "justfile", _two_sections("a-src", "b-src"), OLD)
    _commit_file(dest_repo, dest_root, "justfile", _two_sections("a-dest", "b-src", "dest trailer"), NEW)

    candidates = _collect_merge_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert len(candidates) == 1
    assert candidates[0].unit.section_id == "alpha"
    assert candidates[0].classification == MergeClassification.DEST_CHANGED

    _apply_merge(candidates[0])
    result = (src_root / "justfile").read_text()
    assert "a-dest" in result
    assert "b-src" in result
    assert "src trailer" in result
    assert "a-src" not in result


def test_merge_rename_edit_finds_base(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _merge_setup(tmp_path)
    config.paths = [PathMapping(src_path="rule.md", sync_mode=SyncMode.REPLACE)]
    base = "l1\nl2\nl3\nl4\nl5\nl6\nl7\nl8\nl9\nl10\n"
    _commit_file(src_repo, src_root, "rule.md", base, OLD)
    _commit_file(dest_repo, dest_root, "old-rule.md", base, OLD)
    dest_repo.git.mv("old-rule.md", "rule.md")
    (dest_root / "rule.md").write_text(base + "dest-add\n")
    dest_repo.index.add(["rule.md"])
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = NEW
    env["GIT_COMMITTER_DATE"] = NEW
    dest_repo.git.commit("-m", "rename and edit", env=env)

    candidates = _collect_merge_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert len(candidates) == 1
    assert candidates[0].classification == MergeClassification.DEST_CHANGED

    _apply_merge(candidates[0])
    assert (src_root / "rule.md").read_text() == base + "dest-add\n"


def test_merge_no_common_base_reports_rename(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _merge_setup(tmp_path)
    config.paths = [PathMapping(src_path="rule.md", sync_mode=SyncMode.REPLACE)]
    _commit_file(src_repo, src_root, "rule.md", "src line1\nline2\nline3\nline4\nline5\n", OLD)
    _commit_file(dest_repo, dest_root, "old-rule.md", "dest line1\nline2\nline3\nline4\nline5\n", OLD)
    dest_repo.git.mv("old-rule.md", "rule.md")
    (dest_root / "rule.md").write_text("dest line1\nCHANGED\nline3\nline4\nline5\n")
    dest_repo.index.add(["rule.md"])
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = NEW
    env["GIT_COMMITTER_DATE"] = NEW
    dest_repo.git.commit("-m", "rename and edit", env=env)

    candidates = _collect_merge_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert len(candidates) == 1
    assert candidates[0].classification == MergeClassification.NO_COMMON_BASE
    assert candidates[0].renamed_from == "old-rule.md"
    assert _candidate_detail(candidates[0]) == "conflict: no common base (old-rule.md -> rule.md)"


def test_merge_skip_sections_honored(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _merge_setup(tmp_path)
    config.paths = [PathMapping(src_path="justfile", sync_mode=SyncMode.REPLACE)]
    dest.skip_sections = {"justfile": ["alpha"]}
    _commit_file(src_repo, src_root, "justfile", _two_sections("a-src", "b-src"), OLD)
    _commit_file(dest_repo, dest_root, "justfile", _two_sections("a-src", "b-src"), OLD)
    _commit_file(dest_repo, dest_root, "justfile", _two_sections("a-dest", "b-dest"), NEW)

    candidates = _collect_merge_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert len(candidates) == 1
    assert candidates[0].unit.section_id == "beta"

    _apply_merge(candidates[0])
    result = (src_root / "justfile").read_text()
    assert "b-dest" in result
    assert "a-src" in result
    assert "a-dest" not in result


def test_merge_dry_run_cli(tmp_path):
    src_root, dest_root, src_repo, dest_repo, _config, _dest = _merge_setup(tmp_path)
    _commit_file(src_repo, src_root, "file.txt", "base\n", OLD)
    _commit_file(dest_repo, dest_root, "file.txt", "base\n", OLD)
    _commit_file(dest_repo, dest_root, "file.txt", "dest-new\n", NEW)
    _write_config(src_root)

    result = runner.invoke(app, ["merge", "-n", CONFIG_NAME, "-d", "dest", "--dry-run", "--src-root", str(src_root)])
    assert result.exit_code == 0
    assert (src_root / "file.txt").read_text() == "base\n"
    assert (dest_root / "file.txt").read_text() == "dest-new\n"


def test_merge_conflict_writes_nothing(tmp_path):
    src_root, dest_root, src_repo, dest_repo, _config, _dest = _merge_setup(tmp_path)
    _commit_file(src_repo, src_root, "file.txt", "line1\nline2\n", OLD)
    _commit_file(dest_repo, dest_root, "file.txt", "line1\nline2\n", OLD)
    _commit_file(src_repo, src_root, "file.txt", "src-change\nline2\n", NEW)
    _commit_file(dest_repo, dest_root, "file.txt", "dest-change\nline2\n", NEW)
    _write_config(src_root)

    result = runner.invoke(app, ["merge", "-n", CONFIG_NAME, "-d", "dest", "--src-root", str(src_root)])
    assert result.exit_code == 1
    assert (src_root / "file.txt").read_text() == "src-change\nline2\n"
    assert (dest_root / "file.txt").read_text() == "dest-change\nline2\n"


def test_merge_hint_commits_src(tmp_path, capsys):
    src_root, dest_root, src_repo, dest_repo, config, _dest = _merge_setup(tmp_path)
    _commit_file(src_repo, src_root, "file.txt", "base\n", OLD)
    _commit_file(dest_repo, dest_root, "file.txt", "base\n", OLD)
    _commit_file(dest_repo, dest_root, "file.txt", "dest-new\n", NEW)

    with (
        patch.object(sys.stdin, "isatty", return_value=True),
        patch.object(prompt_utils, "prompt_confirm", return_value=True),
    ):
        _run_merge(config, src_root, ["dest"], MergeOptions())

    assert (src_root / "file.txt").read_text() == "dest-new\n"
    assert (dest_root / "file.txt").read_text() == "dest-new\n"
    assert not src_repo.is_dirty(submodules=False)
    err = capsys.readouterr().err
    assert "path-sync copy -n test-config -d dest" in err
    assert "chore: merge destination dest" in err


@pytest.mark.parametrize("args", [["merge"], ["merge", "-n", "cfg", "-c", "/tmp/cfg.yaml"]])
def test_merge_cli_config_selector(tmp_path, args):
    src_root = tmp_path / "src"
    src_root.mkdir()
    Repo.init(src_root)
    result = runner.invoke(app, [*args, "--src-root", str(src_root)])
    assert result.exit_code == 1


def test_merge_keeps_unrelated_staged_changes(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, _dest = _merge_setup(tmp_path)
    _commit_file(src_repo, src_root, "file.txt", "base\n", OLD)
    _commit_file(dest_repo, dest_root, "file.txt", "base\n", OLD)
    _commit_file(dest_repo, dest_root, "file.txt", "dest-new\n", NEW)
    _commit_file(src_repo, src_root, "other.txt", "other-base\n", OLD)
    (src_root / "other.txt").write_text("other-staged\n")
    src_repo.index.add(["other.txt"])

    with (
        patch.object(sys.stdin, "isatty", return_value=True),
        patch.object(prompt_utils, "prompt_confirm", return_value=True),
    ):
        _run_merge(config, src_root, ["dest"], MergeOptions())

    assert src_repo.git.show("--name-only", "--format=", "HEAD").splitlines() == ["file.txt"]
    assert src_repo.git.diff("--cached", "--name-only").splitlines() == ["other.txt"]


def test_merge_multi_dest_same_unit_conflict(tmp_path):
    src_root, dest_root, dest2_root, src_repo, dest_repo, dest2_repo, config, _dest, _dest2 = _merge_setup_two_dests(
        tmp_path
    )
    _commit_file(src_repo, src_root, "file.txt", "base\n", OLD)
    _commit_file(dest_repo, dest_root, "file.txt", "base\n", OLD)
    _commit_file(dest2_repo, dest2_root, "file.txt", "base\n", OLD)
    _commit_file(dest_repo, dest_root, "file.txt", "dest-a\n", NEW)
    _commit_file(dest2_repo, dest2_root, "file.txt", "dest-b\n", NEW)

    with pytest.raises(typer.Exit) as exc:
        _run_merge(config, src_root, ["dest", "dest2"], MergeOptions())

    assert exc.value.exit_code == 1
    assert (src_root / "file.txt").read_text() == "base\n"
    assert dest_repo.head.commit.message.strip() != "chore: merge destination dest"


def test_merge_multi_dest_distinct_sections_commit_separately(tmp_path):
    src_root, dest_root, dest2_root, src_repo, dest_repo, dest2_repo, config, _dest, _dest2 = _merge_setup_two_dests(
        tmp_path
    )
    config.paths = [PathMapping(src_path="justfile", sync_mode=SyncMode.REPLACE)]
    _commit_file(src_repo, src_root, "justfile", _two_sections("a-src", "b-src"), OLD)
    _commit_file(dest_repo, dest_root, "justfile", _two_sections("a-src", "b-src"), OLD)
    _commit_file(dest2_repo, dest2_root, "justfile", _two_sections("a-src", "b-src"), OLD)
    _commit_file(dest_repo, dest_root, "justfile", _two_sections("a-dest", "b-src"), NEW)
    _commit_file(dest2_repo, dest2_root, "justfile", _two_sections("a-src", "b-dest"), NEW)

    with (
        patch.object(sys.stdin, "isatty", return_value=True),
        patch.object(prompt_utils, "prompt_confirm", return_value=True),
    ):
        _run_merge(config, src_root, ["dest", "dest2"], MergeOptions())

    result = (src_root / "justfile").read_text()
    assert "a-dest" in result
    assert "b-dest" in result
    assert src_repo.git.log("--format=%s").splitlines()[:2] == [
        "chore: merge destination dest2",
        "chore: merge destination dest",
    ]


def test_merge_wrapped_synced_file(tmp_path):
    src_root, dest_root, src_repo, dest_repo, config, dest = _merge_setup(tmp_path)
    config.wrap_synced_files = True
    config.paths = [PathMapping(src_path="file.md", sync_mode=SyncMode.REPLACE)]
    _commit_file(src_repo, src_root, "file.md", "base\n", OLD)
    _commit_file(dest_repo, dest_root, "file.md", sections.wrap_in_synced_section("base\n", dest_root / "file.md"), OLD)
    _commit_file(
        dest_repo, dest_root, "file.md", sections.wrap_in_synced_section("dest-new\n", dest_root / "file.md"), NEW
    )

    candidates = _collect_merge_candidates(config, dest, src_root, dest_root, src_repo, dest_repo)
    assert len(candidates) == 1
    assert candidates[0].classification == MergeClassification.DEST_CHANGED
    assert candidates[0].dest_body == "dest-new\n"

    _apply_merge(candidates[0])
    assert (src_root / "file.md").read_text() == "dest-new\n"
