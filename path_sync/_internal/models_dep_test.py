from pathlib import Path

import yaml

from path_sync._internal.models import (
    AutoMergeConfig,
    CommitConfig,
    OnFailStrategy,
    VerifyConfig,
    VerifyStep,
)
from path_sync._internal.models_dep import (
    DepConfig,
    PRConfig,
    UpdateEntry,
    resolve_dep_config_path,
)


def test_dep_config_parsing():
    config = DepConfig(
        name="uv-deps",
        from_config="python-template",
        include_destinations=["repo1", "repo2"],
        updates=[UpdateEntry(command="uv lock --upgrade")],
        verify=VerifyConfig(
            on_fail=OnFailStrategy.SKIP,
            steps=[
                VerifyStep(run="just fmt", commit=CommitConfig(message="style: format")),
                VerifyStep(run="just test", on_fail=OnFailStrategy.WARN),
            ],
        ),
        pr=PRConfig(branch="deps/uv-lock", title="chore: update uv.lock"),
        auto_merge=AutoMergeConfig(),
    )
    assert config.name == "uv-deps"
    assert config.updates[0].workdir == "."
    assert len(config.verify.steps) == 2
    assert config.verify.steps[0].commit
    assert config.verify.steps[0].commit.add_paths == ["."]
    assert config.auto_merge


def test_dep_config_from_yaml(tmp_path: Path):
    config_yaml = """
name: uv-deps
from_config: python-template
exclude_destinations:
  - legacy-repo
updates:
  - command: uv lock --upgrade
  - workdir: sub
    command: uv lock --upgrade
verify:
  on_fail: skip
  steps:
    - run: just fmt
      commit:
        message: "style: format"
        add_paths: [".", "!.venv"]
    - run: just test
      on_fail: warn
pr:
  branch: deps/uv-lock
  title: "chore: update dependencies"
  labels:
    - dependencies
auto_merge:
  method: squash
"""
    config_path = tmp_path / "test.dep.yaml"
    config_path.write_text(config_yaml)
    data = yaml.safe_load(config_path.read_text())
    config = DepConfig.model_validate(data)

    assert config.from_config == "python-template"
    assert "legacy-repo" in config.exclude_destinations
    assert config.updates[1].workdir == "sub"
    assert config.verify.steps[0].commit
    assert config.verify.steps[0].commit.add_paths == [".", "!.venv"]
    assert config.verify.steps[1].on_fail == OnFailStrategy.WARN


def test_resolve_dep_config_path(tmp_path: Path):
    path = resolve_dep_config_path(tmp_path, "uv-deps")
    assert path == tmp_path / ".github" / "uv-deps.dep.yaml"


def test_load_destinations_with_include_filter(tmp_path: Path):
    src_config_yaml = """
name: python-template
destinations:
  - name: repo1
    dest_path_relative: code/repo1
  - name: repo2
    dest_path_relative: code/repo2
  - name: repo3
    dest_path_relative: code/repo3
"""
    github_dir = tmp_path / ".github"
    github_dir.mkdir()
    (github_dir / "python-template.src.yaml").write_text(src_config_yaml)

    config = DepConfig(
        name="test",
        from_config="python-template",
        include_destinations=["repo1", "repo3"],
        updates=[UpdateEntry(command="echo")],
        pr=PRConfig(branch="test", title="test"),
    )

    destinations = config.load_destinations(tmp_path)

    assert len(destinations) == 2
    assert [d.name for d in destinations] == ["repo1", "repo3"]


def test_load_destinations_with_exclude_filter(tmp_path: Path):
    src_config_yaml = """
name: python-template
destinations:
  - name: repo1
    dest_path_relative: code/repo1
  - name: legacy-repo
    dest_path_relative: code/legacy
  - name: repo2
    dest_path_relative: code/repo2
"""
    github_dir = tmp_path / ".github"
    github_dir.mkdir()
    (github_dir / "python-template.src.yaml").write_text(src_config_yaml)

    config = DepConfig(
        name="test",
        from_config="python-template",
        exclude_destinations=["legacy-repo"],
        updates=[UpdateEntry(command="echo")],
        pr=PRConfig(branch="test", title="test"),
    )

    destinations = config.load_destinations(tmp_path)

    assert len(destinations) == 2
    assert "legacy-repo" not in [d.name for d in destinations]
