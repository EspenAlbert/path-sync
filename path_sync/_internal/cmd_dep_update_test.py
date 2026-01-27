from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from path_sync._internal.cmd_dep_update import (
    _process_single_repo,
    _run_updates,
    _run_verify_steps,
)
from path_sync._internal.models import Destination
from path_sync._internal.models_dep import (
    CommitConfig,
    DepConfig,
    OnFailStrategy,
    PRConfig,
    UpdateEntry,
    VerifyConfig,
    VerifyStep,
)

MODULE = _process_single_repo.__module__


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

    with (
        patch(f"{MODULE}.git_ops") as git_ops,
        patch(f"{MODULE}._run_command"),
    ):
        git_ops.get_repo.return_value = mock_repo
        git_ops.is_git_repo.return_value = True
        git_ops.has_changes.return_value = False

        result = _process_single_repo(config, dest, tmp_path, "", skip_verify=False)

        assert result.status == "no_changes"
        git_ops.prepare_copy_branch.assert_called_once_with(mock_repo, "main", "chore/deps", from_default=True)


def test_process_single_repo_update_fails_returns_skipped(
    dest: Destination, config: DepConfig, tmp_path: Path, repo_path: Path
):
    mock_repo = MagicMock()

    with (
        patch(f"{MODULE}.git_ops") as git_ops,
        patch(f"{MODULE}._run_command") as run_cmd,
    ):
        git_ops.get_repo.return_value = mock_repo
        git_ops.is_git_repo.return_value = True
        run_cmd.side_effect = subprocess.CalledProcessError(1, "uv lock")

        result = _process_single_repo(config, dest, tmp_path, "", skip_verify=False)

        assert result.status == "skipped"
        assert "Update failed" in result.warnings[0]


def test_process_single_repo_changes_with_skip_verify_passes(
    dest: Destination, config: DepConfig, tmp_path: Path, repo_path: Path
):
    mock_repo = MagicMock()

    with (
        patch(f"{MODULE}.git_ops") as git_ops,
        patch(f"{MODULE}._run_command"),
    ):
        git_ops.get_repo.return_value = mock_repo
        git_ops.is_git_repo.return_value = True
        git_ops.has_changes.return_value = True

        result = _process_single_repo(config, dest, tmp_path, "", skip_verify=True)

        assert result.status == "passed"
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

    with (
        patch(f"{MODULE}.git_ops") as git_ops,
        patch(f"{MODULE}._run_command") as run_cmd,
    ):
        git_ops.get_repo.return_value = mock_repo
        git_ops.is_git_repo.return_value = True
        git_ops.has_changes.return_value = True

        result = _process_single_repo(config, dest, tmp_path, "", skip_verify=False)

        assert result.status == "passed"
        assert run_cmd.call_count == 2  # update + verify step


# --- _run_updates tests ---


def test_run_updates_success_returns_none(tmp_path: Path):
    updates = [UpdateEntry(command="echo 1"), UpdateEntry(command="echo 2", workdir="sub")]

    with patch(f"{MODULE}._run_command") as run_cmd:
        result = _run_updates(updates, tmp_path)

        assert result is None
        assert run_cmd.call_count == 2
        run_cmd.assert_any_call("echo 1", tmp_path / ".")
        run_cmd.assert_any_call("echo 2", tmp_path / "sub")


def test_run_updates_failure_returns_error_message(tmp_path: Path):
    updates = [UpdateEntry(command="fail")]

    with patch(f"{MODULE}._run_command") as run_cmd:
        run_cmd.side_effect = subprocess.CalledProcessError(1, "fail")

        result = _run_updates(updates, tmp_path)

        assert result is not None
        assert "Update failed" in result


# --- _run_verify_steps tests ---


def test_verify_steps_all_pass(tmp_path: Path):
    verify = VerifyConfig(
        steps=[
            VerifyStep(run="just fmt"),
            VerifyStep(run="just test"),
        ]
    )
    mock_repo = MagicMock()

    with patch(f"{MODULE}._run_command"):
        status, warnings = _run_verify_steps(mock_repo, tmp_path, verify)

        assert status == "passed"
        assert not warnings


def test_verify_step_fails_with_skip_strategy(tmp_path: Path):
    verify = VerifyConfig(
        on_fail=OnFailStrategy.SKIP,
        steps=[VerifyStep(run="just test")],
    )
    mock_repo = MagicMock()

    with patch(f"{MODULE}._run_command") as run_cmd:
        run_cmd.side_effect = subprocess.CalledProcessError(1, "just test")

        status, warnings = _run_verify_steps(mock_repo, tmp_path, verify)

        assert status == "skipped"
        assert "`just test` failed" in warnings[0]


def test_verify_step_fails_with_fail_strategy(tmp_path: Path):
    verify = VerifyConfig(
        on_fail=OnFailStrategy.FAIL,
        steps=[VerifyStep(run="just test")],
    )
    mock_repo = MagicMock()

    with patch(f"{MODULE}._run_command") as run_cmd:
        run_cmd.side_effect = subprocess.CalledProcessError(1, "just test")

        status, warnings = _run_verify_steps(mock_repo, tmp_path, verify)

        assert status == "failed"
        assert "`just test` failed" in warnings[0]


def test_verify_step_fails_with_warn_strategy_continues(tmp_path: Path):
    verify = VerifyConfig(
        on_fail=OnFailStrategy.WARN,
        steps=[
            VerifyStep(run="just fmt"),
            VerifyStep(run="just test"),
        ],
    )
    mock_repo = MagicMock()

    with patch(f"{MODULE}._run_command") as run_cmd:
        run_cmd.side_effect = [
            subprocess.CalledProcessError(1, "just fmt"),
            None,  # just test passes
        ]

        status, warnings = _run_verify_steps(mock_repo, tmp_path, verify)

        assert status == "warn"
        assert len(warnings) == 1
        assert "`just fmt` failed" in warnings[0]


def test_verify_step_with_commit_stages_and_commits(tmp_path: Path):
    verify = VerifyConfig(
        steps=[
            VerifyStep(
                run="just fmt",
                commit=CommitConfig(message="style: format", add_paths=[".", "!.venv"]),
            ),
        ]
    )
    mock_repo = MagicMock()

    with patch(f"{MODULE}._run_command"), patch(f"{MODULE}.git_ops") as git_ops:
        status, warnings = _run_verify_steps(mock_repo, tmp_path, verify)

        assert status == "passed"
        git_ops.stage_and_commit.assert_called_once_with(mock_repo, [".", "!.venv"], "style: format")


def test_verify_per_step_on_fail_overrides_verify_level(tmp_path: Path):
    verify = VerifyConfig(
        on_fail=OnFailStrategy.FAIL,  # Default: fail
        steps=[
            VerifyStep(run="just fmt", on_fail=OnFailStrategy.WARN),  # Override: warn
        ],
    )
    mock_repo = MagicMock()

    with patch(f"{MODULE}._run_command") as run_cmd:
        run_cmd.side_effect = subprocess.CalledProcessError(1, "just fmt")

        status, warnings = _run_verify_steps(mock_repo, tmp_path, verify)

        assert status == "warn"  # Uses step-level override, not verify-level
        assert len(warnings) == 1
