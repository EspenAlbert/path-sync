from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, Field

from path_sync._internal.models import Destination, SrcConfig, resolve_config_path
from path_sync._internal.yaml_utils import load_yaml_model


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
    on_fail: OnFailStrategy = OnFailStrategy.SKIP
    steps: list[VerifyStep] = Field(default_factory=list)


class UpdateEntry(BaseModel):
    workdir: str = "."
    command: str


class PRConfig(BaseModel):
    branch: str
    title: str
    labels: list[str] = Field(default_factory=list)
    auto_merge: bool = False


class DepConfig(BaseModel):
    CONFIG_EXT: ClassVar[str] = ".dep.yaml"

    name: str
    from_config: str
    include_destinations: list[str] = Field(default_factory=list)
    exclude_destinations: list[str] = Field(default_factory=list)
    updates: list[UpdateEntry]
    verify: VerifyConfig = Field(default_factory=VerifyConfig)
    pr: PRConfig

    def load_destinations(self, repo_root: Path) -> list[Destination]:
        src_config_path = resolve_config_path(repo_root, self.from_config)
        src_config = load_yaml_model(src_config_path, SrcConfig)
        destinations = src_config.destinations
        if self.include_destinations:
            destinations = [d for d in destinations if d.name in self.include_destinations]
        if self.exclude_destinations:
            destinations = [d for d in destinations if d.name not in self.exclude_destinations]
        return destinations


def resolve_dep_config_path(repo_root: Path, name: str) -> Path:
    return repo_root / ".github" / f"{name}{DepConfig.CONFIG_EXT}"
