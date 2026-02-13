from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from git import Repo

from path_sync._internal import git_ops
from path_sync._internal.cmd_copy import (
    CopyOptions,
    _cleanup_orphans,
    _close_stale_pr,
    _ensure_dest_repo,
    _skip_already_synced,
    _sync_path,
)
from path_sync._internal.header import add_header, has_header
from path_sync._internal.models import (
    CommitConfig,
    Destination,
    OnFailStrategy,
    PathMapping,
    SrcConfig,
    SyncMode,
    VerifyConfig,
    VerifyStep,
)
from path_sync._internal.verify import VerifyStatus, run_verify_steps

CONFIG_NAME = "test-config"


def _make_dest(**kwargs) -> Destination:
    defaults = {"name": "test", "dest_path_relative": "."}
    return Destination(**(defaults | kwargs))  # pyright: ignore[reportArgumentType]


def test_sync_single_file(tmp_path):
    src_root = tmp_path / "src"
    dest_root = tmp_path / "dest"
    src_root.mkdir()
    dest_root.mkdir()

    (src_root / "file.py").write_text("content")

    mapping = PathMapping(src_path="file.py", dest_path="out.py")
    changes, synced = _sync_path(mapping, src_root, dest_root, _make_dest(), CONFIG_NAME, False, False)

    assert changes == 1
    assert dest_root / "out.py" in synced
    result = (dest_root / "out.py").read_text()
    assert has_header(result)
    assert f"path-sync copy -n {CONFIG_NAME}" in result


def test_sync_skips_opted_out_file(tmp_path):
    src_root = tmp_path / "src"
    dest_root = tmp_path / "dest"
    src_root.mkdir()
    dest_root.mkdir()

    (src_root / "file.py").write_text("new content")
    (dest_root / "file.py").write_text("local content without header")

    mapping = PathMapping(src_path="file.py")
    changes, _ = _sync_path(mapping, src_root, dest_root, _make_dest(), CONFIG_NAME, False, False)

    assert changes == 0
    assert (dest_root / "file.py").read_text() == "local content without header"


def test_force_overwrite_adds_header_when_content_matches(tmp_path):
    src_root = tmp_path / "src"
    dest_root = tmp_path / "dest"
    src_root.mkdir()
    dest_root.mkdir()

    content = "same content"
    (src_root / "file.py").write_text(content)
    (dest_root / "file.py").write_text(content)  # No header, same content

    mapping = PathMapping(src_path="file.py")
    changes, _ = _sync_path(mapping, src_root, dest_root, _make_dest(), CONFIG_NAME, False, True)

    assert changes == 1
    result = (dest_root / "file.py").read_text()
    assert has_header(result)
    assert content in result


def test_cleanup_orphans(tmp_path):
    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    # File with matching config header - will be orphaned
    orphan = dest_root / "orphan.py"
    orphan.write_text(add_header("orphan content", orphan, CONFIG_NAME))

    # File with different config - should not be deleted
    other = dest_root / "other.py"
    other.write_text(add_header("other content", other, "other-config"))

    synced: set = set()  # No files synced
    deleted = _cleanup_orphans(dest_root, CONFIG_NAME, synced, dry_run=False)

    assert deleted == 1
    assert not orphan.exists()
    assert other.exists()


def test_sync_with_sections_replaces_managed(tmp_path):
    src_root = tmp_path / "src"
    dest_root = tmp_path / "dest"
    src_root.mkdir()
    dest_root.mkdir()

    src_content = """\
# === DO_NOT_EDIT: path-sync standard ===
new recipe
# === OK_EDIT: path-sync standard ==="""
    (src_root / "file.sh").write_text(src_content)

    dest_file = dest_root / "file.sh"
    dest_content = add_header(
        """\
# === DO_NOT_EDIT: path-sync standard ===
old recipe
# === OK_EDIT: path-sync standard ===
# my custom stuff""",
        dest_file,
        CONFIG_NAME,
    )
    dest_file.write_text(dest_content)

    mapping = PathMapping(src_path="file.sh")
    changes, _ = _sync_path(mapping, src_root, dest_root, _make_dest(), CONFIG_NAME, False, False)

    assert changes == 1
    result = (dest_root / "file.sh").read_text()
    assert "new recipe" in result
    assert "old recipe" not in result
    assert "# my custom stuff" in result


def test_sync_with_sections_skip(tmp_path):
    src_root = tmp_path / "src"
    dest_root = tmp_path / "dest"
    src_root.mkdir()
    dest_root.mkdir()

    src_content = """\
# === DO_NOT_EDIT: path-sync standard ===
source
# === OK_EDIT: path-sync standard ==="""
    (src_root / "file.sh").write_text(src_content)

    dest_file = dest_root / "file.sh"
    dest_content = add_header(
        """\
# === DO_NOT_EDIT: path-sync standard ===
keep this
# === OK_EDIT: path-sync standard ===""",
        dest_file,
        CONFIG_NAME,
    )
    dest_file.write_text(dest_content)

    dest = _make_dest(skip_sections={"file.sh": ["standard"]})
    mapping = PathMapping(src_path="file.sh")
    changes, _ = _sync_path(mapping, src_root, dest_root, dest, CONFIG_NAME, False, False)

    assert changes == 0
    assert "keep this" in (dest_root / "file.sh").read_text()


def test_ensure_dest_repo_dry_run_errors_if_missing(tmp_path):
    dest = _make_dest()
    dest_root = tmp_path / "missing_repo"
    with pytest.raises(ValueError, match="Destination repo not found"):
        _ensure_dest_repo(dest, dest_root, dry_run=True)


def test_copy_options_defaults():
    opts = CopyOptions()
    assert not opts.dry_run
    assert not opts.force_overwrite
    assert not opts.no_checkout
    assert not opts.skip_commit
    assert not opts.no_prompt
    assert not opts.no_pr


def test_source_with_header_no_duplicate(tmp_path):
    """Source files with headers should not get double headers in destination."""
    src_root = tmp_path / "src"
    dest_root = tmp_path / "dest"
    src_root.mkdir()
    dest_root.mkdir()

    # Source file already has a header (e.g., template repo uses path-sync itself)
    src_file = src_root / "file.py"
    src_content_with_header = add_header("content", src_file, "original-config")
    src_file.write_text(src_content_with_header)

    mapping = PathMapping(src_path="file.py")
    changes, synced = _sync_path(mapping, src_root, dest_root, _make_dest(), CONFIG_NAME, False, False)

    assert changes == 1
    assert dest_root / "file.py" in synced
    result = (dest_root / "file.py").read_text()

    # Should have exactly one header line with CONFIG_NAME, not two headers
    header_count = result.count("path-sync copy -n")
    assert header_count == 1, f"Expected 1 header, got {header_count}. Content:\n{result}"
    assert f"path-sync copy -n {CONFIG_NAME}" in result
    assert "original-config" not in result


def test_file_mode_replace_no_header(tmp_path):
    src_root = tmp_path / "src"
    dest_root = tmp_path / "dest"
    src_root.mkdir()
    dest_root.mkdir()

    (src_root / "LICENSE").write_text("MIT License")
    (dest_root / "LICENSE").write_text("old license")

    mapping = PathMapping(src_path="LICENSE", sync_mode=SyncMode.REPLACE)
    changes, _ = _sync_path(mapping, src_root, dest_root, _make_dest(), CONFIG_NAME, False, False)

    assert changes == 1
    result = (dest_root / "LICENSE").read_text()
    assert result == "MIT License"
    assert not has_header(result)


def test_file_mode_replace_skips_unchanged(tmp_path):
    src_root = tmp_path / "src"
    dest_root = tmp_path / "dest"
    src_root.mkdir()
    dest_root.mkdir()

    (src_root / "LICENSE").write_text("MIT License")
    (dest_root / "LICENSE").write_text("MIT License")

    mapping = PathMapping(src_path="LICENSE", sync_mode=SyncMode.REPLACE)
    changes, _ = _sync_path(mapping, src_root, dest_root, _make_dest(), CONFIG_NAME, False, False)

    assert changes == 0


def test_file_mode_scaffold_creates_new(tmp_path):
    src_root = tmp_path / "src"
    dest_root = tmp_path / "dest"
    src_root.mkdir()
    dest_root.mkdir()

    (src_root / ".gitignore").write_text("*.pyc")

    mapping = PathMapping(src_path=".gitignore", sync_mode=SyncMode.SCAFFOLD)
    changes, _ = _sync_path(mapping, src_root, dest_root, _make_dest(), CONFIG_NAME, False, False)

    assert changes == 1
    result = (dest_root / ".gitignore").read_text()
    assert result == "*.pyc"
    assert not has_header(result)


def test_file_mode_scaffold_skips_existing(tmp_path):
    src_root = tmp_path / "src"
    dest_root = tmp_path / "dest"
    src_root.mkdir()
    dest_root.mkdir()

    (src_root / ".gitignore").write_text("new content")
    (dest_root / ".gitignore").write_text("user customized")

    mapping = PathMapping(src_path=".gitignore", sync_mode=SyncMode.SCAFFOLD)
    changes, _ = _sync_path(mapping, src_root, dest_root, _make_dest(), CONFIG_NAME, False, False)

    assert changes == 0
    assert (dest_root / ".gitignore").read_text() == "user customized"


def test_sync_new_file_respects_skip_sections(tmp_path):
    """New file should not include skipped sections."""
    src_root = tmp_path / "src"
    dest_root = tmp_path / "dest"
    src_root.mkdir()
    dest_root.mkdir()

    src_content = """\
# === DO_NOT_EDIT: path-sync included ===
keep this
# === OK_EDIT: path-sync included ===
# === DO_NOT_EDIT: path-sync skipped ===
skip this
# === OK_EDIT: path-sync skipped ==="""
    (src_root / "file.sh").write_text(src_content)

    dest = _make_dest(skip_sections={"file.sh": ["skipped"]})
    mapping = PathMapping(src_path="file.sh")
    changes, _ = _sync_path(mapping, src_root, dest_root, dest, CONFIG_NAME, False, False)

    assert changes == 1
    result = (dest_root / "file.sh").read_text()
    assert "keep this" in result
    assert "skipped" not in result
    assert "skip this" not in result


MODULE = run_verify_steps.__module__


def test_verify_steps_empty_returns_passed():
    mock_repo = MagicMock(spec=Repo)
    verify = VerifyConfig(steps=[])
    result = run_verify_steps(mock_repo, Path("/tmp"), verify)
    assert result.status == VerifyStatus.PASSED
    assert not result.failures


def test_verify_steps_all_pass(tmp_path: Path):
    mock_repo = MagicMock(spec=Repo)
    verify = VerifyConfig(steps=[VerifyStep(run="echo hello"), VerifyStep(run="true")])
    result = run_verify_steps(mock_repo, tmp_path, verify)
    assert result.status == VerifyStatus.PASSED
    assert not result.failures


def test_verify_step_fails_with_skip_strategy(tmp_path: Path):
    mock_repo = MagicMock(spec=Repo)
    verify = VerifyConfig(
        on_fail=OnFailStrategy.SKIP,
        steps=[VerifyStep(run="false")],
    )
    result = run_verify_steps(mock_repo, tmp_path, verify)
    assert result.status == VerifyStatus.SKIPPED
    assert len(result.failures) == 1
    assert result.failures[0].on_fail == OnFailStrategy.SKIP


def test_verify_step_fails_with_fail_strategy(tmp_path: Path):
    mock_repo = MagicMock(spec=Repo)
    verify = VerifyConfig(
        on_fail=OnFailStrategy.FAIL,
        steps=[VerifyStep(run="false")],
    )
    result = run_verify_steps(mock_repo, tmp_path, verify)
    assert result.status == VerifyStatus.FAILED
    assert len(result.failures) == 1
    assert result.failures[0].on_fail == OnFailStrategy.FAIL


def test_verify_step_fails_with_warn_strategy_continues(tmp_path: Path):
    mock_repo = MagicMock(spec=Repo)
    verify = VerifyConfig(
        on_fail=OnFailStrategy.WARN,
        steps=[VerifyStep(run="false"), VerifyStep(run="echo after-warn")],
    )
    result = run_verify_steps(mock_repo, tmp_path, verify)
    assert result.status == VerifyStatus.WARN
    assert len(result.failures) == 1
    assert result.failures[0].on_fail == OnFailStrategy.WARN


def test_verify_step_with_commit_stages_and_commits(tmp_path: Path):
    mock_repo = MagicMock(spec=Repo)
    verify = VerifyConfig(
        steps=[
            VerifyStep(
                run="echo format",
                commit=CommitConfig(message="style: format", add_paths=[".", "!.venv"]),
            )
        ]
    )
    git_ops_module = git_ops.stage_and_commit.__module__
    with patch(f"{git_ops_module}.{git_ops.stage_and_commit.__name__}") as mock_stage:
        result = run_verify_steps(mock_repo, tmp_path, verify)
        assert result.status == VerifyStatus.PASSED
        mock_stage.assert_called_once_with(mock_repo, [".", "!.venv"], "style: format")


def test_verify_per_step_on_fail_overrides_verify_level(tmp_path: Path):
    mock_repo = MagicMock(spec=Repo)
    verify = VerifyConfig(
        on_fail=OnFailStrategy.FAIL,
        steps=[VerifyStep(run="false", on_fail=OnFailStrategy.WARN)],
    )
    result = run_verify_steps(mock_repo, tmp_path, verify)
    assert result.status == VerifyStatus.WARN
    assert len(result.failures) == 1
    assert result.failures[0].on_fail == OnFailStrategy.WARN


def test_wrap_synced_files_wraps_content_in_section(tmp_path):
    src_root = tmp_path / "src"
    dest_root = tmp_path / "dest"
    src_root.mkdir()
    dest_root.mkdir()

    (src_root / "file.py").write_text("def hello(): pass")

    mapping = PathMapping(src_path="file.py")
    changes, _ = _sync_path(
        mapping, src_root, dest_root, _make_dest(), CONFIG_NAME, False, False, wrap_synced_files=True
    )

    assert changes == 1
    result = (dest_root / "file.py").read_text()
    assert "# === DO_NOT_EDIT: path-sync synced ===" in result
    assert "def hello(): pass" in result
    assert "# === OK_EDIT: path-sync synced ===" in result


def test_wrap_per_path_override_disables(tmp_path):
    src_root = tmp_path / "src"
    dest_root = tmp_path / "dest"
    src_root.mkdir()
    dest_root.mkdir()

    (src_root / "file.py").write_text("content")

    mapping = PathMapping(src_path="file.py", wrap=False)
    changes, _ = _sync_path(
        mapping, src_root, dest_root, _make_dest(), CONFIG_NAME, False, False, wrap_synced_files=True
    )

    assert changes == 1
    result = (dest_root / "file.py").read_text()
    assert "DO_NOT_EDIT" not in result


def test_wrapped_file_preserves_dest_content_around_section(tmp_path):
    src_root = tmp_path / "src"
    dest_root = tmp_path / "dest"
    src_root.mkdir()
    dest_root.mkdir()

    (src_root / "file.py").write_text("managed content v2")

    dest_file = dest_root / "file.py"
    dest_content = add_header(
        """\
# before section
# === DO_NOT_EDIT: path-sync synced ===
managed content v1
# === OK_EDIT: path-sync synced ===
# after section""",
        dest_file,
        CONFIG_NAME,
    )
    dest_file.write_text(dest_content)

    mapping = PathMapping(src_path="file.py")
    changes, _ = _sync_path(
        mapping, src_root, dest_root, _make_dest(), CONFIG_NAME, False, False, wrap_synced_files=True
    )

    assert changes == 1
    result = (dest_root / "file.py").read_text()
    assert "# before section" in result
    assert "managed content v2" in result
    assert "managed content v1" not in result
    assert "# after section" in result


def test_file_with_existing_sections_not_double_wrapped(tmp_path):
    src_root = tmp_path / "src"
    dest_root = tmp_path / "dest"
    src_root.mkdir()
    dest_root.mkdir()

    src_content = """\
# === DO_NOT_EDIT: path-sync standard ===
already has sections
# === OK_EDIT: path-sync standard ==="""
    (src_root / "file.sh").write_text(src_content)

    mapping = PathMapping(src_path="file.sh")
    changes, _ = _sync_path(
        mapping, src_root, dest_root, _make_dest(), CONFIG_NAME, False, False, wrap_synced_files=True
    )

    assert changes == 1
    result = (dest_root / "file.sh").read_text()
    assert result.count("DO_NOT_EDIT") == 1
    assert "synced" not in result


def test_sync_preserves_dest_trailing_when_adding_new_sections(tmp_path):
    """When source has new sections not in dest, dest's trailing content is preserved."""
    src_root = tmp_path / "src"
    dest_root = tmp_path / "dest"
    src_root.mkdir()
    dest_root.mkdir()

    src_content = """\
# === DO_NOT_EDIT: path-sync core ===
core content
# === OK_EDIT: path-sync core ===

# === DO_NOT_EDIT: path-sync checks ===
checks content
# === OK_EDIT: path-sync checks ===
# source trailing
src-recipe:
    echo source
"""
    (src_root / "justfile").write_text(src_content)

    dest_content = add_header(
        """\
# === DO_NOT_EDIT: path-sync standard ===
old standard
# === OK_EDIT: path-sync standard ===
# dest trailing
dest-recipe:
    echo dest
""",
        dest_root / "justfile",
        CONFIG_NAME,
    )
    (dest_root / "justfile").write_text(dest_content)

    mapping = PathMapping(src_path="justfile")
    changes, _ = _sync_path(mapping, src_root, dest_root, _make_dest(), CONFIG_NAME, False, False)

    assert changes == 1
    result = (dest_root / "justfile").read_text()
    assert "core content" in result
    assert "checks content" in result
    assert "old standard" not in result
    assert "dest trailing" in result
    assert "dest-recipe" in result
    assert "source trailing" not in result
    assert "src-recipe" not in result


COPY_MODULE = _close_stale_pr.__module__


def _make_src_config(**kwargs) -> SrcConfig:
    defaults = {"name": "test", "destinations": []}
    return SrcConfig(**(defaults | kwargs))


def test_close_stale_pr_skipped_when_keep_pr_on_no_changes(tmp_path: Path):
    opts = CopyOptions()
    config = _make_src_config(keep_pr_on_no_changes=True)
    with patch(f"{COPY_MODULE}.git_ops") as mock_git:
        _close_stale_pr(tmp_path, "sync/test", opts, config)
        mock_git.has_open_pr.assert_not_called()


def test_close_stale_pr_runs_by_default(tmp_path: Path):
    opts = CopyOptions()
    config = _make_src_config()
    with patch(f"{COPY_MODULE}.git_ops") as mock_git:
        mock_git.has_open_pr.return_value = True
        _close_stale_pr(tmp_path, "sync/test", opts, config)
        mock_git.close_pr.assert_called_once()


def test_skip_already_synced_bypassed_when_force_resync(tmp_path: Path):
    config = _make_src_config(force_resync=True)
    opts = CopyOptions()
    with patch(f"{COPY_MODULE}.git_ops") as mock_git:
        result = _skip_already_synced("dest", tmp_path, "sync/test", "2026-01-01T00:00:00", opts, config)
        assert not result
        mock_git.get_pr_body.assert_not_called()


def test_skip_already_synced_checks_by_default(tmp_path: Path):
    config = _make_src_config()
    opts = CopyOptions()
    body = "<!-- path-sync: sha=abc12345 ts=2099-01-01T00:00:00+00:00 -->"
    with patch(f"{COPY_MODULE}.git_ops") as mock_git:
        mock_git.get_pr_body.return_value = body
        result = _skip_already_synced("dest", tmp_path, "sync/test", "2026-01-01T00:00:00", opts, config)
        assert result
