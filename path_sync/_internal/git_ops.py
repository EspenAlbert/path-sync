from __future__ import annotations

import logging
import os
import subprocess
from contextlib import suppress
from pathlib import Path

from git import GitCommandError, InvalidGitRepositoryError, NoSuchPathError, Repo

logger = logging.getLogger(__name__)


def _auth_url(url: str) -> str:
    """Inject GH_TOKEN into HTTPS URL for authentication."""
    token = os.environ.get("GH_TOKEN", "")
    if not token:
        return url
    if url.startswith("https://github.com/"):
        return url.replace("https://", f"https://x-access-token:{token}@")
    return url


def get_repo(path: Path) -> Repo:
    try:
        return Repo(path)
    except InvalidGitRepositoryError as e:
        raise ValueError(f"Not a git repository: {path}") from e


def is_git_repo(path: Path) -> bool:
    with suppress(InvalidGitRepositoryError, NoSuchPathError):
        Repo(path)
        return True
    return False


def get_default_branch(repo: Repo) -> str:
    with suppress(GitCommandError):
        return repo.git.symbolic_ref("refs/remotes/origin/HEAD", short=True).replace("origin/", "")
    return "main"


def fetch_and_reset_to_default(repo: Repo, default_branch: str) -> None:
    """Fetch latest from remote and reset to default branch."""
    logger.info(f"Fetching origin and resetting to {default_branch}")
    repo.remotes.origin.fetch()
    if repo.head.is_detached or repo.active_branch.name != default_branch:
        repo.git.checkout(default_branch)
    repo.git.reset("--hard", f"origin/{default_branch}")


def clone_repo(url: str, dest: Path) -> Repo:
    logger.info(f"Cloning {url} to {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    return Repo.clone_from(_auth_url(url), str(dest))


def checkout_branch(repo: Repo, branch: str) -> None:
    current = repo.active_branch.name
    if current == branch:
        return
    logger.info(f"Checking out {branch}")
    try:
        repo.git.checkout(branch)
    except GitCommandError:
        repo.git.checkout("-b", branch)


def prepare_copy_branch(repo: Repo, default_branch: str, copy_branch: str, from_default: bool = False) -> None:
    """Prepare copy_branch for syncing.

    Args:
        from_default: If True, fetch origin and reset to origin/default_branch
                      before creating copy_branch. Use in CI for clean state.
                      If False, just switch to or create copy_branch from current HEAD.
    """
    if from_default:
        logger.info("Fetching origin")
        repo.git.fetch("origin")

        logger.info(f"Checking out {default_branch}")
        repo.git.checkout(default_branch)
        repo.git.reset("--hard", f"origin/{default_branch}")

        with suppress(GitCommandError):
            repo.git.branch("-D", copy_branch)
            logger.info(f"Deleted existing local branch: {copy_branch}")

        logger.info(f"Creating fresh branch: {copy_branch}")
        repo.git.checkout("-b", copy_branch)
    else:
        checkout_branch(repo, copy_branch)


def get_current_sha(repo: Repo) -> str:
    return repo.head.commit.hexsha


def get_remote_url(repo: Repo, remote_name: str = "origin") -> str:
    try:
        return repo.remote(remote_name).url
    except ValueError:
        return ""


def has_changes(repo: Repo) -> bool:
    return repo.is_dirty(submodules=False) or len(repo.untracked_files) > 0


def commit_changes(repo: Repo, message: str) -> None:
    repo.git.add("-A")
    if repo.is_dirty(submodules=False):
        _ensure_git_user(repo)
        repo.git.commit("-m", message)
        logger.info(f"Committed: {message}")


def stage_and_commit(repo: Repo, add_paths: list[str], message: str) -> bool:
    """Stage specified paths and commit if there are changes. Returns True if a commit was made."""
    include = [p for p in add_paths if not p.startswith("!")]
    exclude = [p[1:] for p in add_paths if p.startswith("!")]
    for path in include:
        repo.git.add(path)
    for path in exclude:
        repo.git.reset("HEAD", "--", path)
    if not repo.is_dirty(index=True, submodules=False):
        return False
    _ensure_git_user(repo)
    repo.git.commit("-m", message)
    logger.info(f"Committed: {message}")
    return True


def _ensure_git_user(repo: Repo) -> None:
    """Configure git user if not already set."""
    try:
        repo.config_reader().get_value("user", "name")
    except Exception:
        repo.config_writer().set_value("user", "name", "path-sync[bot]").release()
        repo.config_writer().set_value("user", "email", "path-sync[bot]@users.noreply.github.com").release()


def push_branch(repo: Repo, branch: str, force: bool = True) -> None:
    logger.info(f"Pushing {branch}" + (" (force)" if force else ""))
    args = ["--force", "-u", "origin", branch] if force else ["-u", "origin", branch]
    repo.git.push(*args)


def _get_repo_full_name(repo_path: Path) -> str | None:
    """Get owner/repo from gh CLI."""
    cmd = [
        "gh",
        "repo",
        "view",
        "--json",
        "owner,name",
        "-q",
        '.owner.login + "/" + .name',
    ]
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(f"Failed to get repo info: {result.stderr}")
        return None
    return result.stdout.strip()


def _get_pr_number(repo_path: Path, branch: str) -> str | None:
    """Get PR number for a branch."""
    cmd = ["gh", "pr", "view", branch, "--json", "number", "-q", ".number"]
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(f"Failed to get PR number: {result.stderr}")
        return None
    return result.stdout.strip()


def update_pr_body(repo_path: Path, branch: str, body: str) -> bool:
    """Update PR body using REST API (only requires 'repo' scope, not 'read:org')."""
    repo_full = _get_repo_full_name(repo_path)
    if not repo_full:
        return False

    pr_number = _get_pr_number(repo_path, branch)
    if not pr_number:
        return False

    cmd = [
        "gh",
        "api",
        "-X",
        "PATCH",
        f"repos/{repo_full}/pulls/{pr_number}",
        "-f",
        f"body={body}",
    ]
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(f"Failed to update PR body: {result.stderr}")
        return False
    logger.info("Updated PR body")
    return True


def create_or_update_pr(
    repo_path: Path,
    branch: str,
    title: str,
    body: str = "",
    labels: list[str] | None = None,
    reviewers: list[str] | None = None,
    assignees: list[str] | None = None,
) -> str:
    cmd = ["gh", "pr", "create", "--head", branch, "--title", title]
    cmd.extend(["--body", body or ""])
    if labels:
        cmd.extend(["--label", ",".join(labels)])
    if reviewers:
        cmd.extend(["--reviewer", ",".join(reviewers)])
    if assignees:
        cmd.extend(["--assignee", ",".join(assignees)])

    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
    if result.returncode != 0:
        if "already exists" in result.stderr:
            logger.info("PR already exists, updating body")
            update_pr_body(repo_path, branch, body)
            return ""
        raise RuntimeError(f"Failed to create PR: {result.stderr}")
    pr_url = result.stdout.strip()
    logger.info(f"Created PR: {pr_url}")
    return pr_url


def file_has_git_changes(repo: Repo, file_path: Path, base_ref: str = "HEAD") -> bool:
    rel_path = str(file_path.relative_to(repo.working_dir))
    diff = repo.git.diff("--name-only", base_ref, "--", rel_path)
    return bool(diff.strip())


def get_changed_files(repo: Repo, base_ref: str = "HEAD") -> list[Path]:
    diff = repo.git.diff("--name-only", base_ref)
    if not diff.strip():
        return []
    repo_root = Path(repo.working_dir)
    return [repo_root / p for p in diff.strip().split("\n")]


def get_file_content_at_ref(repo: Repo, file_path: Path, ref: str) -> str | None:
    rel_path = str(file_path.relative_to(repo.working_dir))
    with suppress(GitCommandError):
        return repo.git.show(f"{ref}:{rel_path}")
    return None
