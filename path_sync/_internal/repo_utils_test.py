from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from path_sync._internal.models import Destination
from path_sync._internal.repo_utils import ensure_repo, resolve_repo_path

MODULE = ensure_repo.__module__


@pytest.fixture
def dest() -> Destination:
    return Destination(name="my-repo", dest_path_relative="code/my-repo", repo_url="https://github.com/org/my-repo")


def test_resolve_repo_path_work_dir(dest: Destination):
    result = resolve_repo_path(dest, Path("/src"), "/tmp/work")
    assert result == Path("/tmp/work/my-repo")


def test_resolve_repo_path_relative(dest: Destination):
    result = resolve_repo_path(dest, Path("/src"), "")
    assert result == Path("/src/code/my-repo").resolve()


def test_resolve_repo_path_no_relative_no_workdir():
    dest = Destination(name="x", dest_path_relative="")
    with pytest.raises(ValueError, match="--work-dir"):
        resolve_repo_path(dest, Path("/src"), "")


def test_ensure_repo_clones_when_missing(dest: Destination, tmp_path: Path):
    repo_path = tmp_path / "missing"
    with patch(f"{MODULE}.git_ops") as git_ops:
        mock_repo = MagicMock()
        git_ops.clone_repo.return_value = mock_repo
        result = ensure_repo(dest, repo_path)
        assert result is mock_repo
        git_ops.clone_repo.assert_called_once_with(dest.repo_url, repo_path)


def test_ensure_repo_dry_run_raises_when_missing(dest: Destination, tmp_path: Path):
    repo_path = tmp_path / "missing"
    with pytest.raises(ValueError, match="dry-run"):
        ensure_repo(dest, repo_path, dry_run=True)


def test_ensure_repo_returns_existing(dest: Destination, tmp_path: Path):
    repo_path = tmp_path / "existing"
    repo_path.mkdir()
    mock_repo = MagicMock()

    with patch(f"{MODULE}.git_ops") as git_ops:
        git_ops.is_git_repo.return_value = True
        git_ops.get_repo.return_value = mock_repo
        result = ensure_repo(dest, repo_path)
        assert result is mock_repo
        git_ops.get_repo.assert_called_once_with(repo_path)


@pytest.fixture
def invalid_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "not-a-repo"
    repo_path.mkdir()
    (repo_path / "keep.txt").write_text("keep")
    return repo_path


def test_ensure_repo_keeps_invalid_repo_without_repo_url(invalid_repo: Path):
    dest = Destination(name="my-repo", dest_path_relative="code/my-repo")
    with (
        patch.object(sys.stdin, "isatty", return_value=False),
        pytest.raises(ValueError, match="no repo_url configured, not removing it"),
    ):
        ensure_repo(dest, invalid_repo)
    assert (invalid_repo / "keep.txt").exists()


@pytest.mark.parametrize(("interactive", "answer"), [(False, "y"), (True, "n")], ids=["non_interactive", "declined"])
def test_ensure_repo_keeps_invalid_repo_unless_confirmed(
    dest: Destination, invalid_repo: Path, interactive: bool, answer: str
):
    with (
        patch.object(sys.stdin, "isatty", return_value=interactive),
        patch("builtins.input", return_value=answer),
        patch(f"{MODULE}.git_ops.clone_repo") as clone_repo,
        pytest.raises(ValueError, match="not removed"),
    ):
        ensure_repo(dest, invalid_repo)
    assert (invalid_repo / "keep.txt").exists()
    clone_repo.assert_not_called()


def test_ensure_repo_reclones_invalid_repo_when_confirmed(dest: Destination, invalid_repo: Path):
    with (
        patch.object(sys.stdin, "isatty", return_value=True),
        patch("builtins.input", return_value="y"),
        patch(f"{MODULE}.git_ops.clone_repo") as clone_repo,
    ):
        result = ensure_repo(dest, invalid_repo)
    assert result is clone_repo.return_value
    assert not invalid_repo.exists()
    clone_repo.assert_called_once_with(dest.repo_url, invalid_repo)
