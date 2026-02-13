from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from path_sync._internal import verify as verify_module
from path_sync._internal.cmd_dep_update import (
    DepUpdateOptions,
    Status,
    _process_single_repo,
    _run_updates,
    _update_and_validate,
)
from path_sync._internal.models import (
    Destination,
    VerifyConfig,
    VerifyStep,
)
from path_sync._internal.models_dep import (
    DepConfig,
    PRConfig,
    UpdateEntry,
)
from path_sync._internal.verify import StepFailure

MODULE = _process_single_repo.__module__
VERIFY_MODULE = verify_module.run_command.__module__


@pytest.fixture
def dest() -> Destination:
    return Destination(
        name="test-repo",
        dest_path_relative="code/test-repo",
        default_branch="main",
    )


@pytest.fixture
def repo_path(tmp_path: Path, dest: Destination) -> Path:
    path = tmp_path / dest.dest_path_relative
    path.mkdir(parents=True)
    return path


@pytest.fixture
def config() -> DepConfig:
    return DepConfig(
        name="test",
        from_config="python-template",
        updates=[UpdateEntry(command="uv lock --upgrade")],
        verify=VerifyConfig(steps=[]),
        pr=PRConfig(branch="chore/deps", title="chore: update deps"),
    )


# --- _process_single_repo tests ---


def test_process_single_repo_no_changes_skips(dest: Destination, config: DepConfig, tmp_path: Path, repo_path: Path):
    mock_repo = MagicMock()
    opts = DepUpdateOptions()

    with (
        patch(f"{MODULE}.git_ops") as git_ops,
        patch(f"{VERIFY_MODULE}.{verify_module.run_command.__name__}"),
    ):
        git_ops.get_repo.return_value = mock_repo
        git_ops.is_git_repo.return_value = True
        git_ops.has_changes.return_value = False

        result = _process_single_repo(config, dest, tmp_path, "", opts)

        assert result.status == Status.NO_CHANGES
        git_ops.prepare_copy_branch.assert_called_once_with(mock_repo, "main", "chore/deps", from_default=True)


def test_process_single_repo_update_fails_returns_skipped(
    dest: Destination, config: DepConfig, tmp_path: Path, repo_path: Path
):
    mock_repo = MagicMock()
    opts = DepUpdateOptions()

    with (
        patch(f"{MODULE}.git_ops") as git_ops,
        patch(f"{VERIFY_MODULE}.{verify_module.run_command.__name__}") as run_cmd,
    ):
        git_ops.get_repo.return_value = mock_repo
        git_ops.is_git_repo.return_value = True
        run_cmd.side_effect = subprocess.CalledProcessError(1, "uv lock")

        result = _process_single_repo(config, dest, tmp_path, "", opts)

        assert result.status == Status.SKIPPED
        assert len(result.failures) == 1
        assert result.failures[0].step == "uv lock"
        assert result.failures[0].returncode == 1


def test_process_single_repo_changes_with_skip_verify_passes(
    dest: Destination, config: DepConfig, tmp_path: Path, repo_path: Path
):
    mock_repo = MagicMock()
    opts = DepUpdateOptions(skip_verify=True)

    with (
        patch(f"{MODULE}.git_ops") as git_ops,
        patch(f"{VERIFY_MODULE}.{verify_module.run_command.__name__}"),
    ):
        git_ops.get_repo.return_value = mock_repo
        git_ops.is_git_repo.return_value = True
        git_ops.has_changes.return_value = True

        result = _process_single_repo(config, dest, tmp_path, "", opts)

        assert result.status == Status.PASSED
        git_ops.commit_changes.assert_called_once_with(mock_repo, "chore: update deps")


def test_process_single_repo_verify_runs_when_changes_present(dest: Destination, tmp_path: Path, repo_path: Path):
    config = DepConfig(
        name="test",
        from_config="python-template",
        updates=[UpdateEntry(command="uv lock")],
        verify=VerifyConfig(steps=[VerifyStep(run="just test")]),
        pr=PRConfig(branch="chore/deps", title="chore: update deps"),
    )
    mock_repo = MagicMock()
    opts = DepUpdateOptions()

    with (
        patch(f"{MODULE}.git_ops") as git_ops,
        patch(f"{VERIFY_MODULE}.{verify_module.run_command.__name__}") as run_cmd,
    ):
        git_ops.get_repo.return_value = mock_repo
        git_ops.is_git_repo.return_value = True
        git_ops.has_changes.return_value = True

        result = _process_single_repo(config, dest, tmp_path, "", opts)

        assert result.status == Status.PASSED
        assert run_cmd.call_count == 2  # update + verify step


# --- _run_updates tests ---


def test_run_updates_success_returns_none(tmp_path: Path):
    updates = [UpdateEntry(command="echo 1"), UpdateEntry(command="echo 2", workdir="sub")]

    with patch(f"{VERIFY_MODULE}.{verify_module.run_command.__name__}") as run_cmd:
        result = _run_updates(updates, tmp_path)

        assert result is None
        assert run_cmd.call_count == 2
        run_cmd.assert_any_call("echo 1", tmp_path / ".")
        run_cmd.assert_any_call("echo 2", tmp_path / "sub")


def test_run_updates_failure_returns_step_failure(tmp_path: Path):
    updates = [UpdateEntry(command="fail")]

    with patch(f"{VERIFY_MODULE}.{verify_module.run_command.__name__}") as run_cmd:
        run_cmd.side_effect = subprocess.CalledProcessError(1, "fail")

        result = _run_updates(updates, tmp_path)

        assert result is not None
        assert isinstance(result, StepFailure)
        assert result.step == "fail"
        assert result.returncode == 1


# --- _update_and_validate tests ---


def test_update_and_validate_keeps_pr_when_config_flag_set(
    dest: Destination, config: DepConfig, tmp_path: Path, repo_path: Path
):
    config = DepConfig(
        name="test",
        from_config="python-template",
        updates=[UpdateEntry(command="uv lock --upgrade")],
        verify=VerifyConfig(steps=[]),
        pr=PRConfig(branch="chore/deps", title="chore: update deps"),
        keep_pr_on_no_changes=True,
    )
    mock_repo = MagicMock()
    opts = DepUpdateOptions()

    with (
        patch(f"{MODULE}.git_ops") as git_ops,
        patch(f"{VERIFY_MODULE}.{verify_module.run_command.__name__}"),
    ):
        git_ops.get_repo.return_value = mock_repo
        git_ops.is_git_repo.return_value = True
        git_ops.has_changes.return_value = False

        results = _update_and_validate(config, [dest], tmp_path, "", opts)

        assert results == []
        git_ops.has_open_pr.assert_not_called()
        git_ops.close_pr.assert_not_called()
