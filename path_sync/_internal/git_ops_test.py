from __future__ import annotations

from pathlib import Path

from git import Repo

from path_sync._internal.git_ops import (
    GH_PR_BODY_MAX_CHARS,
    _truncate_body,
    remote_branch_has_same_content,
)


def test_truncate_body_short_unchanged():
    body = "short body"
    assert _truncate_body(body) == body


def test_truncate_body_at_limit_unchanged():
    body = "x" * GH_PR_BODY_MAX_CHARS
    assert _truncate_body(body) == body


def test_truncate_body_over_limit():
    body = "x" * (GH_PR_BODY_MAX_CHARS + 500)
    result = _truncate_body(body)
    assert len(result) == GH_PR_BODY_MAX_CHARS
    assert result.endswith("... (truncated, output too long for PR body)")


def test_truncate_body_closes_open_code_fence():
    prefix = "## Command Output\n\n```\n"
    filler = "log line\n" * 10_000
    body = prefix + filler
    assert len(body) > GH_PR_BODY_MAX_CHARS

    result = _truncate_body(body)
    assert len(result) <= GH_PR_BODY_MAX_CHARS
    assert "\n```\n" in result[len(prefix) :]
    assert result.endswith("... (truncated, output too long for PR body)")


def test_truncate_body_no_extra_fence_when_closed():
    prefix = "## Output\n\n```\nsome log\n```\n\nmore text\n"
    filler = "x" * GH_PR_BODY_MAX_CHARS
    body = prefix + filler

    result = _truncate_body(body)
    assert len(result) == GH_PR_BODY_MAX_CHARS
    assert "```\n\n... (truncated" not in result


def _init_repo_with_remote(tmp_path: Path) -> tuple[Repo, Repo]:
    """Create a bare 'remote' and a clone that points to it."""
    bare_path = tmp_path / "remote.git"
    bare = Repo.init(bare_path, bare=True)

    clone_path = tmp_path / "clone"
    clone = Repo.clone_from(str(bare_path), str(clone_path))
    (clone_path / "file.txt").write_text("initial")
    clone.index.add(["file.txt"])
    clone.index.commit("initial")
    clone.git.push("-u", "origin", "main")
    return bare, clone


def test_same_content_returns_true(tmp_path: Path):
    _, clone = _init_repo_with_remote(tmp_path)
    clone.git.checkout("-b", "feature")
    (Path(clone.working_dir) / "file.txt").write_text("updated")
    clone.index.add(["file.txt"])
    clone.index.commit("first")
    clone.git.push("-u", "origin", "feature")

    # New commit with same tree (content unchanged)
    clone.git.commit("--allow-empty", "-m", "second")

    assert remote_branch_has_same_content(clone, "feature")


def test_different_content_returns_false(tmp_path: Path):
    _, clone = _init_repo_with_remote(tmp_path)
    clone.git.checkout("-b", "feature")
    (Path(clone.working_dir) / "file.txt").write_text("v1")
    clone.index.add(["file.txt"])
    clone.index.commit("first")
    clone.git.push("-u", "origin", "feature")

    (Path(clone.working_dir) / "file.txt").write_text("v2")
    clone.index.add(["file.txt"])
    clone.index.commit("second")

    assert not remote_branch_has_same_content(clone, "feature")


def test_no_remote_branch_returns_false(tmp_path: Path):
    _, clone = _init_repo_with_remote(tmp_path)
    clone.git.checkout("-b", "new-branch")
    (Path(clone.working_dir) / "file.txt").write_text("changed")
    clone.index.add(["file.txt"])
    clone.index.commit("first")

    assert not remote_branch_has_same_content(clone, "new-branch")
