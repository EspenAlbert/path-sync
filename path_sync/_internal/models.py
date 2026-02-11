from __future__ import annotations

import fnmatch
import glob as glob_mod
from enum import StrEnum
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, Field

LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"

DEFAULT_EXCLUDE_DIRS: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
    }
)


def _default_exclude_dirs() -> set[str]:
    return set(DEFAULT_EXCLUDE_DIRS)


class MergeMethod(StrEnum):
    SQUASH = "squash"
    MERGE = "merge"
    REBASE = "rebase"


class AutoMergeConfig(BaseModel):
    method: MergeMethod = MergeMethod.MERGE
    delete_branch: bool = True
    poll_interval_seconds: int = 30
    timeout_seconds: int = 900


class SyncMode(StrEnum):
    SYNC = "sync"
    REPLACE = "replace"
    SCAFFOLD = "scaffold"


class OnFailStrategy(StrEnum):
    SKIP = "skip"
    FAIL = "fail"
    WARN = "warn"


class CommitConfig(BaseModel):
    message: str
    add_paths: list[str] = Field(default_factory=lambda: ["."])


class VerifyStep(BaseModel):
    run: str
    commit: CommitConfig | None = None
    on_fail: OnFailStrategy | None = None


class VerifyConfig(BaseModel):
    on_fail: OnFailStrategy = OnFailStrategy.WARN
    steps: list[VerifyStep] = Field(default_factory=list)


class PathMapping(BaseModel):
    src_path: str
    dest_path: str = ""
    sync_mode: SyncMode = SyncMode.SYNC
    exclude_dirs: set[str] = Field(default_factory=_default_exclude_dirs)
    exclude_file_patterns: set[str] = Field(default_factory=set)
    wrap: bool | None = None

    def should_wrap(self, config_default: bool) -> bool:
        return self.wrap if self.wrap is not None else config_default

    def resolved_dest_path(self) -> str:
        return self.dest_path or self.src_path

    def is_excluded(self, path: Path) -> bool:
        if self.exclude_dirs & set(path.parts):
            return True
        return any(fnmatch.fnmatch(path.name, pat) for pat in self.exclude_file_patterns)

    def expand_dest_paths(self, repo_root: Path) -> list[Path]:
        dest_path = self.resolved_dest_path()
        pattern = repo_root / dest_path

        if "*" in dest_path:
            return [Path(p) for p in glob_mod.glob(str(pattern), recursive=True)]
        if pattern.is_dir():
            return [p for p in pattern.rglob("*") if p.is_file()]
        if pattern.exists():
            return [pattern]
        return []


HEADER_TEMPLATE = "path-sync copy -n {config_name}"


class HeaderConfig(BaseModel):
    comment_prefixes: dict[str, str] = Field(default_factory=dict)
    comment_suffixes: dict[str, str] = Field(default_factory=dict)


DEFAULT_BODY_TEMPLATE = """\
Synced from [{src_repo_name}]({src_repo_url}) @ `{src_sha_short}`

<details>
<summary>Sync Log</summary>

```
{sync_log}
```

</details>
"""


class PRFieldsBase(BaseModel):
    """Common PR fields shared by copy and dep-update commands."""

    labels: list[str] = Field(default_factory=list)
    reviewers: list[str] = Field(default_factory=list)
    assignees: list[str] = Field(default_factory=list)


class PRDefaults(PRFieldsBase):
    title: str = "chore: sync {name} files"
    body_template: str = DEFAULT_BODY_TEMPLATE
    body_suffix: str = ""

    def format_body(
        self,
        src_repo_url: str,
        src_sha: str,
        sync_log: str,
        dest_name: str,
    ) -> str:
        src_repo_name = src_repo_url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
        body = self.body_template.format(
            src_repo_url=src_repo_url,
            src_repo_name=src_repo_name,
            src_sha=src_sha,
            src_sha_short=src_sha[:8],
            sync_log=sync_log,
            dest_name=dest_name,
        )
        if self.body_suffix:
            body = f"{body}\n---\n{self.body_suffix}"
        return body


class Destination(BaseModel):
    name: str
    repo_url: str = ""
    dest_path_relative: str
    copy_branch: str = ""
    default_branch: str = "main"
    skip_sections: dict[str, list[str]] = Field(default_factory=dict)
    skip_file_patterns: set[str] = Field(default_factory=set)
    verify: VerifyConfig | None = None

    def resolved_copy_branch(self, config_name: str) -> str:
        return self.copy_branch or f"sync/{config_name}"

    def is_skipped(self, dest_key: str) -> bool:
        return any(fnmatch.fnmatch(dest_key, pat) for pat in self.skip_file_patterns)

    def resolve_verify(self, fallback: VerifyConfig | None) -> VerifyConfig:
        return self.verify if self.verify is not None else (fallback or VerifyConfig())


class SrcConfig(BaseModel):
    CONFIG_EXT: ClassVar[str] = ".src.yaml"

    name: str
    git_remote: str = "origin"
    src_repo_url: str = ""
    schedule: str = "0 6 * * *"
    header_config: HeaderConfig = Field(default_factory=HeaderConfig)
    pr_defaults: PRDefaults = Field(default_factory=PRDefaults)
    paths: list[PathMapping] = Field(default_factory=list)
    destinations: list[Destination] = Field(default_factory=list)
    verify: VerifyConfig | None = None
    wrap_synced_files: bool = False
    auto_merge: AutoMergeConfig | None = None

    def find_destination(self, name: str) -> Destination:
        for dest in self.destinations:
            if dest.name == name:
                return dest
        raise ValueError(f"Destination not found: {name}")


def resolve_config_path(repo_root: Path, name: str) -> Path:
    return repo_root / ".github" / f"{name}{SrcConfig.CONFIG_EXT}"


def find_repo_root(start_path: Path) -> Path:
    current = start_path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise ValueError(f"No git repository found from {start_path}")
