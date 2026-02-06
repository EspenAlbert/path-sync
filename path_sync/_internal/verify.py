from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from git import Repo

from path_sync._internal import git_ops
from path_sync._internal.models import OnFailStrategy, VerifyConfig

logger = logging.getLogger(__name__)


class VerifyStatus(StrEnum):
    PASSED = "passed"
    SKIPPED = "skipped"
    WARN = "warn"
    FAILED = "failed"


@dataclass
class StepFailure:
    step: str
    returncode: int
    on_fail: OnFailStrategy


@dataclass
class VerifyResult:
    status: VerifyStatus = VerifyStatus.PASSED
    failures: list[StepFailure] = field(default_factory=list)


def run_command(cmd: str, cwd: Path, dry_run: bool = False) -> None:
    if dry_run:
        logger.info(f"[DRY RUN] Would run: {cmd} from {cwd}")
        return
    logger.info(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    prefix = cmd.split()[0]
    for line in result.stdout.strip().splitlines():
        logger.info(f"[{prefix}] {line}")
    for line in result.stderr.strip().splitlines():
        if result.returncode != 0:
            logger.error(f"[{prefix}] {line}")
        else:
            logger.info(f"[{prefix}] {line}")
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)


def run_verify_steps(
    repo: Repo, repo_path: Path, verify: VerifyConfig, dry_run: bool = False, skip_commit: bool = False
) -> VerifyResult:
    if not verify.steps:
        return VerifyResult()

    failures: list[StepFailure] = []

    for step in verify.steps:
        on_fail = step.on_fail or verify.on_fail

        try:
            run_command(step.run, repo_path, dry_run=dry_run)
        except subprocess.CalledProcessError as e:
            failure = StepFailure(step=step.run, returncode=e.returncode, on_fail=on_fail)
            match on_fail:
                case OnFailStrategy.FAIL:
                    return VerifyResult(status=VerifyStatus.FAILED, failures=[failure])
                case OnFailStrategy.SKIP:
                    return VerifyResult(status=VerifyStatus.SKIPPED, failures=[failure])
                case OnFailStrategy.WARN:
                    failures.append(failure)
                    continue

        if step.commit and not dry_run and not skip_commit:
            git_ops.stage_and_commit(repo, step.commit.add_paths, step.commit.message)

    status = VerifyStatus.WARN if failures else VerifyStatus.PASSED
    return VerifyResult(status=status, failures=failures)


def log_verify_summary(name: str, result: VerifyResult) -> None:
    match result.status:
        case VerifyStatus.PASSED:
            logger.info(f"Verification passed for {name}")
        case VerifyStatus.WARN:
            logger.warning(f"Verification completed with warnings for {name}")
            for f in result.failures:
                logger.warning(f"  {f.step} failed (exit {f.returncode})")
        case VerifyStatus.SKIPPED:
            logger.warning(f"Verification skipped for {name}")
        case VerifyStatus.FAILED:
            logger.error(f"Verification failed for {name}")
