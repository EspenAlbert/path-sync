from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from path_sync._internal.cmd_dep_update import (
    Status,
    StepFailure,
    _process_single_repo,
    _run_updates,
    _run_verify_steps,
    _truncate_stderr,
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

        assert result.status == Status.NO_CHANGES
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

        assert result.status == Status.SKIPPED
        assert len(result.failures) == 1
        assert result.failures[0].step == "uv lock"
        assert result.failures[0].returncode == 1


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

    with (
        patch(f"{MODULE}.git_ops") as git_ops,
        patch(f"{MODULE}._run_command") as run_cmd,
    ):
        git_ops.get_repo.return_value = mock_repo
        git_ops.is_git_repo.return_value = True
        git_ops.has_changes.return_value = True

        result = _process_single_repo(config, dest, tmp_path, "", skip_verify=False)

        assert result.status == Status.PASSED
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


def test_run_updates_failure_returns_step_failure(tmp_path: Path):
    updates = [UpdateEntry(command="fail")]

    with patch(f"{MODULE}._run_command") as run_cmd:
        run_cmd.side_effect = subprocess.CalledProcessError(1, "fail")

        result = _run_updates(updates, tmp_path)

        assert result is not None
        assert isinstance(result, StepFailure)
        assert result.step == "fail"
        assert result.returncode == 1


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
        status, failures = _run_verify_steps(mock_repo, tmp_path, verify)

        assert status == Status.PASSED
        assert not failures


def test_verify_step_fails_with_skip_strategy(tmp_path: Path):
    verify = VerifyConfig(
        on_fail=OnFailStrategy.SKIP,
        steps=[VerifyStep(run="just test")],
    )
    mock_repo = MagicMock()

    with patch(f"{MODULE}._run_command") as run_cmd:
        run_cmd.side_effect = subprocess.CalledProcessError(1, "just test")

        status, failures = _run_verify_steps(mock_repo, tmp_path, verify)

        assert status == Status.SKIPPED
        assert len(failures) == 1
        assert failures[0].step == "just test"
        assert failures[0].on_fail == OnFailStrategy.SKIP


def test_verify_step_fails_with_fail_strategy(tmp_path: Path):
    verify = VerifyConfig(
        on_fail=OnFailStrategy.FAIL,
        steps=[VerifyStep(run="just test")],
    )
    mock_repo = MagicMock()

    with patch(f"{MODULE}._run_command") as run_cmd:
        run_cmd.side_effect = subprocess.CalledProcessError(1, "just test")

        status, failures = _run_verify_steps(mock_repo, tmp_path, verify)

        assert status == Status.FAILED
        assert len(failures) == 1
        assert failures[0].step == "just test"
        assert failures[0].on_fail == OnFailStrategy.FAIL


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

        status, failures = _run_verify_steps(mock_repo, tmp_path, verify)

        assert status == Status.WARN
        assert len(failures) == 1
        assert failures[0].step == "just fmt"
        assert failures[0].on_fail == OnFailStrategy.WARN


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
        status, failures = _run_verify_steps(mock_repo, tmp_path, verify)

        assert status == Status.PASSED
        assert not failures
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

        status, failures = _run_verify_steps(mock_repo, tmp_path, verify)

        assert status == Status.WARN  # Uses step-level override, not verify-level
        assert len(failures) == 1
        assert failures[0].on_fail == OnFailStrategy.WARN


# --- _truncate_stderr tests ---


def test_truncate_stderr_short_text_unchanged():
    text = "line1\nline2\nline3"
    result = _truncate_stderr(text, max_lines=5)
    assert result == "line1\nline2\nline3"


def test_truncate_stderr_keeps_last_lines():
    lines = [f"line{i}" for i in range(30)]
    text = "\n".join(lines)

    result = _truncate_stderr(text, max_lines=5)

    assert result.startswith("... (25 lines skipped)")
    assert "line25" in result
    assert "line29" in result
    assert "line0" not in result
