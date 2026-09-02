from __future__ import annotations

import os
from pathlib import Path

from git import Repo

from path_sync._internal import git_ops
from path_sync._internal.git_ops import (
    GH_PR_BODY_MAX_CHARS,
    _truncate_body,
    push_branch,
    remote_branch_has_same_content,
)


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


def test_path_is_dirty_clean(tmp_repo):
    repo = git_ops.get_repo(tmp_repo)
    path = tmp_repo / "clean.txt"
    path.write_text("x")
    _commit_file(repo, tmp_repo, "clean.txt", "x")
    assert git_ops.path_porcelain_status(repo, path) is None
    assert not git_ops.path_is_dirty(repo, path)


def test_path_is_dirty_modified(tmp_repo):
    repo = git_ops.get_repo(tmp_repo)
    path = tmp_repo / "dirty.txt"
    _commit_file(repo, tmp_repo, "dirty.txt", "a")
    path.write_text("b")
    assert git_ops.path_is_dirty(repo, path)


def test_path_is_dirty_untracked(tmp_repo):
    repo = git_ops.get_repo(tmp_repo)
    path = tmp_repo / "new.txt"
    path.write_text("new")
    assert git_ops.path_is_dirty(repo, path)


def test_file_last_commit_unix_missing_path(tmp_repo):
    repo = git_ops.get_repo(tmp_repo)
    path = tmp_repo / "never.txt"
    path.write_text("x")
    assert git_ops.file_last_commit_unix(repo, path) is None


def test_file_last_commit_unix(tmp_repo):
    repo = git_ops.get_repo(tmp_repo)
    when = "2026-09-01T12:00:00+0000"
    _commit_file(repo, tmp_repo, "dated.txt", "v1", when)
    path = tmp_repo / "dated.txt"
    ts = git_ops.file_last_commit_unix(repo, path)
    assert ts is not None
    _commit_file(repo, tmp_repo, "dated.txt", "v2", "2026-10-01T12:00:00+0000")
    ts2 = git_ops.file_last_commit_unix(repo, path)
    assert ts is not None and ts2 is not None
    assert ts2 > ts


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
    bare_path = tmp_path / "remote.git"
    bare = Repo.init(bare_path, bare=True)
    bare.git.symbolic_ref("HEAD", "refs/heads/main")

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


def test_push_branch_skips_when_content_unchanged(tmp_path: Path):
    _, clone = _init_repo_with_remote(tmp_path)
    clone.git.checkout("-b", "feature")
    (Path(clone.working_dir) / "file.txt").write_text("updated")
    clone.index.add(["file.txt"])
    clone.index.commit("first")
    clone.git.push("-u", "origin", "feature")

    clone.git.commit("--allow-empty", "-m", "empty commit")

    assert not push_branch(clone, "feature", force=True)


def test_push_branch_pushes_when_content_differs(tmp_path: Path):
    _, clone = _init_repo_with_remote(tmp_path)
    clone.git.checkout("-b", "feature")
    (Path(clone.working_dir) / "file.txt").write_text("v1")
    clone.index.add(["file.txt"])
    clone.index.commit("first")
    clone.git.push("-u", "origin", "feature")

    (Path(clone.working_dir) / "file.txt").write_text("v2")
    clone.index.add(["file.txt"])
    clone.index.commit("second")

    assert push_branch(clone, "feature", force=True)
