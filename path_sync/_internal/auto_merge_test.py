from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from path_sync._internal.auto_merge import (
    CheckRun,
    PRMergeResult,
    PRRef,
    PRState,
    _log_summary,
    enable_auto_merge,
    get_pr_checks,
    get_pr_state,
    handle_auto_merge,
    wait_for_merge,
)
from path_sync._internal.models import AutoMergeConfig, MergeMethod

MODULE = enable_auto_merge.__module__


def test_enable_auto_merge_calls_gh(tmp_path: Path):
    config = AutoMergeConfig(method=MergeMethod.REBASE, delete_branch=False)
    with patch(f"{MODULE}.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess([], 0, "", "")
        enable_auto_merge(tmp_path, "https://github.com/o/r/pull/1", config)
        cmd = mock_run.call_args[0][0]
        assert "--rebase" in cmd
        assert "--delete-branch" not in cmd


def test_get_pr_checks_parses_json(tmp_path: Path):
    checks_json = json.dumps(
        [
            {"name": "lint", "state": "SUCCESS"},
            {"name": "test", "state": "FAILURE"},
        ]
    )
    with patch(f"{MODULE}.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess([], 0, checks_json, "")
        checks = get_pr_checks(tmp_path, "branch")
        assert len(checks) == 2
        assert checks[1].failed
        assert not checks[0].failed


def test_get_pr_state_returns_merged(tmp_path: Path):
    with patch(f"{MODULE}.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess([], 0, "MERGED\n", "")
        assert get_pr_state(tmp_path, "branch") == PRState.MERGED


def test_handle_auto_merge_no_wait_skips_polling(tmp_path: Path):
    refs = [PRRef("repo1", tmp_path, "branch1")]
    config = AutoMergeConfig()
    with (
        patch(f"{MODULE}.get_pr_state", return_value=PRState.OPEN),
        patch(f"{MODULE}.enable_auto_merge") as mock_enable,
        patch(f"{MODULE}.wait_for_merge") as mock_wait,
    ):
        results = handle_auto_merge(refs, config, no_wait=True)
        mock_enable.assert_called_once()
        mock_wait.assert_not_called()
        assert not results


def test_handle_auto_merge_skips_already_merged(tmp_path: Path):
    refs = [PRRef("repo1", tmp_path, "branch1")]
    config = AutoMergeConfig()
    with (
        patch(f"{MODULE}.get_pr_state", return_value=PRState.MERGED),
        patch(f"{MODULE}.enable_auto_merge") as mock_enable,
    ):
        handle_auto_merge(refs, config, no_wait=True)
        mock_enable.assert_not_called()


def test_pr_merge_result_failed_and_pending_checks():
    result = PRMergeResult(
        dest_name="r",
        pr_url="url",
        branch="b",
        state=PRState.OPEN,
        checks=[
            CheckRun(name="lint", state="SUCCESS"),
            CheckRun(name="test", state="FAILURE"),
            CheckRun(name="build", state="IN_PROGRESS"),
        ],
    )
    assert len(result.failed_checks) == 1
    assert result.failed_checks[0].name == "test"
    assert len(result.pending_checks) == 1
    assert result.pending_checks[0].name == "build"


def test_log_summary_formats_table(caplog):
    results = [
        PRMergeResult(dest_name="repo1", pr_url="", branch="b", state=PRState.MERGED),
        PRMergeResult(
            dest_name="repo2",
            pr_url="",
            branch="b",
            state=PRState.OPEN,
            checks=[CheckRun(name="lint", state="FAILURE")],
        ),
    ]
    with caplog.at_level("INFO"):
        _log_summary(results)
    assert "repo1" in caplog.text
    assert "MERGED" in caplog.text
    assert "lint" in caplog.text


def test_wait_for_merge_timeout(tmp_path: Path):
    config = AutoMergeConfig(timeout_seconds=0)
    checks = [CheckRun(name="ci", state="IN_PROGRESS")]
    with (
        patch(f"{MODULE}.get_pr_url", return_value="https://github.com/o/r/pull/1"),
        patch(f"{MODULE}.get_pr_checks", return_value=checks),
    ):
        result = wait_for_merge(tmp_path, "branch", config, dest_name="myrepo")
    assert result.state == PRState.OPEN
    assert result.dest_name == "myrepo"
    assert len(result.pending_checks) == 1


def test_wait_for_merge_merged(tmp_path: Path):
    config = AutoMergeConfig(timeout_seconds=60)
    with (
        patch(f"{MODULE}.get_pr_url", return_value="https://github.com/o/r/pull/1"),
        patch(f"{MODULE}.get_pr_state", return_value=PRState.MERGED),
    ):
        result = wait_for_merge(tmp_path, "branch", config, dest_name="repo1")
    assert result.state == PRState.MERGED
    assert result.dest_name == "repo1"
    assert result.pr_url == "https://github.com/o/r/pull/1"
