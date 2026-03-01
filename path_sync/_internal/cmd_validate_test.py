from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from path_sync._internal.cmd_validate import validate_no_changes
from path_sync._internal.validation import validate_no_unauthorized_changes

MODULE = validate_no_changes.__module__


def test_validate_no_changes_passes_branch_to_validation(tmp_path: Path):
    mock_repo = MagicMock()
    mock_repo.active_branch.name = "feature-branch"

    with (
        patch(f"{MODULE}.find_repo_root", return_value=tmp_path),
        patch(f"{MODULE}.git_ops") as git_ops,
        patch(f"{MODULE}.{validate_no_unauthorized_changes.__name__}") as validate_fn,
    ):
        git_ops.get_repo.return_value = mock_repo
        validate_fn.return_value = []

        validate_no_changes(
            branch="develop",
            skip_sections_opt="",
            src_root_opt=str(tmp_path),
        )

        validate_fn.assert_called_once()
        call_kw = validate_fn.call_args
        assert call_kw[0][0] == tmp_path
        assert call_kw[0][1] == "develop"


def test_validate_no_changes_skips_when_on_sync_branch(tmp_path: Path):
    mock_repo = MagicMock()
    mock_repo.active_branch.name = "sync/python-template"

    with (
        patch(f"{MODULE}.find_repo_root", return_value=tmp_path),
        patch(f"{MODULE}.git_ops") as git_ops,
        patch(f"{MODULE}.{validate_no_unauthorized_changes.__name__}") as validate_fn,
    ):
        git_ops.get_repo.return_value = mock_repo

        validate_no_changes(
            branch="main",
            skip_sections_opt="",
            src_root_opt=str(tmp_path),
        )

        validate_fn.assert_not_called()


def test_validate_no_changes_skips_when_on_base_branch(tmp_path: Path):
    mock_repo = MagicMock()
    mock_repo.active_branch.name = "main"

    with (
        patch(f"{MODULE}.find_repo_root", return_value=tmp_path),
        patch(f"{MODULE}.git_ops") as git_ops,
        patch(f"{MODULE}.{validate_no_unauthorized_changes.__name__}") as validate_fn,
    ):
        git_ops.get_repo.return_value = mock_repo

        validate_no_changes(
            branch="main",
            skip_sections_opt="",
            src_root_opt=str(tmp_path),
        )

        validate_fn.assert_not_called()
