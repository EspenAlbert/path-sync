# path-sync

[![PyPI](https://img.shields.io/pypi/v/path-sync)](https://pypi.org/project/path-sync/)
[![GitHub](https://img.shields.io/github/license/EspenAlbert/path-sync)](https://github.com/EspenAlbert/path-sync)
[![codecov](https://codecov.io/gh/EspenAlbert/path-sync/graph/badge.svg)](https://codecov.io/gh/EspenAlbert/path-sync)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://espenalbert.github.io/path-sync/)

Sync files from a source repo to multiple destination repos.

## Overview

**Problem**: You have shared config files (linter rules, CI templates, editor settings) that should be consistent across multiple repositories. Manual copying leads to drift.

**Solution**: path-sync provides one-way file syncing with clear ownership:

| Term | Definition |
|------|------------|
| **SRC** | Source repository containing the canonical files |
| **DEST** | Destination repository receiving synced files |
| **Header** | Comment added to synced files marking them as managed |
| **Section** | Marked region within a file for partial syncing |

**Key behaviors**:
- SRC owns synced content; DEST should not edit it
- Files with headers are updated on each sync
- Remove a header to opt-out (file becomes DEST-owned)
- Orphaned files (removed from SRC) are deleted in DEST

## Installation

```bash
# From PyPI
uvx path-sync --help

# Or install in project
uv pip install path-sync
```

## Quick Start

### 1. Bootstrap a source config

```bash
path-sync boot -n myconfig -d ../dest-repo1 -d ../dest-repo2 -p '.cursor/**/*.mdc'
```

Creates `.github/myconfig.src.yaml` with auto-detected git remote and destinations.

### 2. Copy files to destinations

```bash
path-sync copy -n myconfig
```

By default, prompts before each git operation. See [Usage Scenarios](#usage-scenarios) for common patterns.

| Flag | Description |
|------|-------------|
| `-d dest1,dest2` | Filter specific destinations |
| `--dry-run` | Preview without writing (requires existing repos) |
| `-y, --no-prompt` | Skip confirmations (for CI) |
| `--local` | No git ops after sync (no commit/push/PR) |
| `--no-checkout` | Skip branch switching (assumes already on correct branch) |
| `--checkout-from-default` | Reset to origin/default before sync |
| `--no-pr` | Push but skip PR creation |
| `--force-overwrite` | Overwrite files even if header removed (opted out) |
| `--detailed-exit-code` | Exit 0=no changes, 1=changes, 2=error |
| `--skip-orphan-cleanup` | Skip deletion of orphaned synced files |
| `--skip-verify` | Skip verification steps after syncing |
| `--pr-title` | Override PR title (supports `{name}`, `{dest_name}`) |
| `--pr-labels` | Comma-separated PR labels |
| `--pr-reviewers` | Comma-separated PR reviewers |
| `--pr-assignees` | Comma-separated PR assignees |

### 3. Validate (run in dest repo)

```bash
uvx path-sync validate-no-changes -b main
```

Options:
- `-b, --branch` - Default branch to compare against (default: main)
- `--skip-sections` - Comma-separated `path:section_id` pairs to skip (e.g., `justfile:coverage`)

## Usage Scenarios

| Scenario | Command |
|----------|---------|
| Interactive sync | `copy -n cfg` |
| CI fresh sync | `copy -n cfg --checkout-from-default -y` |
| Local preview | `copy -n cfg --dry-run` |
| Local test files | `copy -n cfg --local` |
| Already on branch | `copy -n cfg --no-checkout` |
| Push, manual PR | `copy -n cfg --no-pr -y` |
| Force opted-out | `copy -n cfg --force-overwrite` |

**Interactive prompt behavior**: Each git operation (checkout, commit, push, PR) prompts independently. Use `--no-checkout` to skip the branch switch prompt. Use `--local` to skip all git operations after sync.

## Section Markers

For partial file syncing (e.g., `justfile`, `pyproject.toml`), wrap sections with markers:

```makefile
# === DO_NOT_EDIT: path-sync default ===
lint:
    ruff check .
# === OK_EDIT ===
```

- **`DO_NOT_EDIT: path-sync {id}`** - Start of managed section with identifier
- **`OK_EDIT`** - End marker (content below is editable)

During sync, only content within markers is replaced. Destination can have extra sections.

Use `skip_sections` in destination config to exclude specific sections from sync:

```yaml
destinations:
  - name: dest1
    dest_path_relative: ../dest1
    skip_sections:
      justfile: [coverage]  # keep local coverage recipe
```

## Wrapping Synced Files

For files without section markers, `wrap_synced_files` automatically wraps content in a `synced` section. This lets destinations add content before/after the synced content.

**Without wrapping** (default):
```python
# path-sync copy -n myconfig
def hello():
    pass
```

**With wrapping** (`wrap_synced_files: true`):
```python
# path-sync copy -n myconfig
# === DO_NOT_EDIT: path-sync synced ===
def hello():
    pass
# === OK_EDIT: path-sync synced ===
```

Destinations can add content outside the section markers. Per-path override via `wrap: false`:

```yaml
wrap_synced_files: true
paths:
  - src_path: templates/base.py     # wrapped
  - src_path: .editorconfig
    wrap: false                     # not wrapped
```

## Skipping Files per Destination

Use `skip_file_patterns` to exclude files for specific destinations. Patterns match against the **destination path** (after `dest_path` remapping):

```yaml
paths:
  - src_path: scripts/
    dest_path: tools/  # remapped in destination
destinations:
  - name: dest1
    dest_path_relative: ../dest1
    skip_file_patterns:
      - "tools/internal/*"   # matches destination path, not src
      - "*.test.py"
      - "docs/draft.md"
```

Patterns use [fnmatch](https://docs.python.org/3/library/fnmatch.html) syntax (`*` matches any characters, `?` matches single character).

## Config Reference

**Source config** (`.github/{name}.src.yaml`):

```yaml
name: cursor
src_repo_url: https://github.com/user/src-repo
schedule: "0 6 * * *"
paths:
  - src_path: .cursor/**/*.mdc
  - src_path: templates/justfile
    dest_path: justfile
  - src_path: scripts/
    exclude_file_patterns:
      - "*.pyc"
      - "test_*.py"
destinations:
  - name: dest1
    repo_url: https://github.com/user/dest1
    dest_path_relative: ../dest1
    # copy_branch: sync/cursor  # defaults to sync/{config_name}
    default_branch: main
    skip_sections:
      justfile: [coverage]
    skip_file_patterns:
      - "scripts/internal/*"
```

| Field | Description |
|-------|-------------|
| `name` | Config identifier |
| `src_repo_url` | Source repo URL (auto-detected from git remote) |
| `schedule` | Cron for scheduled sync workflow |
| `paths` | Files/globs to sync (see path options below) |
| `destinations` | Target repos with sync settings |
| `header_config` | Comment style per extension (has defaults) |
| `pr_defaults` | PR title, labels, reviewers, assignees |
| `wrap_synced_files` | Wrap synced files in section markers (default: `false`) |
| `verify` | Verification steps to run after syncing (see [Verify Steps](#verify-steps-in-copy)) |

**Path options**:

| Field | Description |
|-------|-------------|
| `src_path` | Source file, directory, or glob pattern (required) |
| `dest_path` | Destination path (defaults to `src_path`) |
| `sync_mode` | `sync` (default), `replace`, or `scaffold` |
| `exclude_dirs` | Directory names to skip (defaults: `__pycache__`, `.git`, `.venv`, etc.) |
| `exclude_file_patterns` | Filename patterns to skip, supports globs (`*.pyc`, `test_*.py`) |
| `wrap` | Override global `wrap_synced_files` for this path (`true`/`false`) |

**Destination options**:

| Field | Description |
|-------|-------------|
| `name` | Destination identifier (required) |
| `repo_url` | Repo URL for cloning if not found locally |
| `dest_path_relative` | Path to destination repo relative to source (required) |
| `copy_branch` | Branch for sync (defaults to `sync/{config_name}`) |
| `default_branch` | Default branch to compare against (defaults to `main`) |
| `skip_sections` | Map of `{dest_path: [section_ids]}` to preserve locally |
| `skip_file_patterns` | Patterns to skip for this destination (matches dest path, fnmatch syntax) |
| `verify` | Per-destination verify config (overrides source-level verify) |

## Verify Steps in Copy

Run verification steps after syncing files. Synced files are committed first, then verify steps run and can make additional commits.

```yaml
name: myconfig
verify:
  on_fail: warn  # default: warn (also: skip, fail)
  steps:
    - run: just fmt
      commit:
        message: "style: format synced files"
        add_paths: ["."]
      on_fail: warn
    - run: just test
```

Per-destination override:

```yaml
destinations:
  - name: dest1
    dest_path_relative: ../dest1
    verify:
      steps:
        - run: npm run build
```

Use `--skip-verify` to disable verification steps.

## Header Format

Synced files have a header comment identifying the source config:

```python
# path-sync copy -n myconfig
```

Comment style is extension-aware:

| Extension | Format |
|-----------|--------|
| `.py`, `.sh`, `.yaml` | `# path-sync copy -n {name}` |
| `.go`, `.js`, `.ts` | `// path-sync copy -n {name}` |
| `.md`, `.mdc`, `.html` | `<!-- path-sync copy -n {name} -->` |

Remove this header to opt-out of future syncs for that file.

## GitHub Actions

### Source repo workflow

Create `.github/workflows/path_sync_copy.yaml`:

```yaml
name: path-sync copy
on:
  schedule:
    - cron: "0 6 * * *"
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uvx path-sync copy -n myconfig --checkout-from-default -y
        env:
          GH_TOKEN: ${{ secrets.GH_PAT }}
```

### Destination repo validation

Create `.github/workflows/path_sync_validate.yaml`:

```yaml
name: path-sync validate
on:
  push:
    branches-ignore:
      - main
      - sync/**
  pull_request:
    branches:
      - main

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v5
      - run: uvx path-sync validate-no-changes -b main
```

**Validation skips automatically when:**
- On a `sync/*` branch (path-sync uses `sync/{config_name}` by default)
- On the default branch (comparing against itself)

The workflow triggers exclude these branches too, reducing unnecessary CI runs.

### PAT Requirements

Create a **Fine-grained PAT** at <https://github.com/settings/tokens?type=beta>

| Permission | Scope |
|------------|-------|
| Contents | Read/write (push branches) |
| Pull requests | Read/write (create PRs) |
| Workflows | Read/write (if syncing `.github/workflows/`) |
| Metadata | Read (always required) |

Add as repository secret: `GH_PAT`

### Common Errors

| Error | Fix |
|-------|-----|
| `HTTP 404: Not Found` | Add repo to PAT's repository access |
| `HTTP 403: Resource not accessible` | Add Contents + Pull requests permissions |
| `GraphQL: Resource not accessible` | Use GH_PAT, not GITHUB_TOKEN |
| `HTTP 422: Required status check` | Exclude `sync/*` from branch protection |

## Dependency Updates

The `dep-update` command runs dependency updates across multiple repositories. It clones repos, runs update commands, verifies changes, and creates PRs.

### Quick Start

```bash
# Create config at .github/myconfig.dep.yaml (see example below)
# Then run:
path-sync dep-update -n myconfig

# Preview without creating PRs
path-sync dep-update -n myconfig --dry-run

# Filter specific destinations
path-sync dep-update -n myconfig -d repo1,repo2
```

### Dep Config Reference

**Config file**: `.github/{name}.dep.yaml`

```yaml
name: uv-deps
from_config: python-template  # references .github/python-template.src.yaml for destinations
exclude_destinations:
  - path-sync  # skip self

updates:
  - command: uv lock --upgrade
  - workdir: packages/sub  # optional subdirectory
    command: uv lock --upgrade

verify:
  on_fail: skip  # default strategy: skip, fail, warn
  steps:
    - run: uv sync
    - run: just fmt
      commit:
        message: "chore: format after update"
        add_paths: [".", "!uv.lock"]  # ! prefix excludes
      on_fail: warn
    - run: just test

pr:
  branch: deps/uv-lock-update
  title: "chore(deps): update uv.lock"
  labels: [dependencies]
  reviewers: []  # optional
  assignees: []  # optional
  auto_merge: true
```

| Field | Description |
|-------|-------------|
| `from_config` | Source config name for destination list |
| `include_destinations` | Only process these destinations |
| `exclude_destinations` | Skip these destinations |
| `updates` | Commands to run (in order) |
| `verify.on_fail` | Default failure strategy: `skip`, `fail`, `warn` |
| `verify.steps` | Verification commands with optional commit/on_fail |
| `pr.auto_merge` | Enable GitHub auto-merge after PR creation |

### CLI Flags

| Flag | Description |
|------|-------------|
| `-n, --name` | Config name (required) |
| `-d, --dest` | Filter destinations (comma-separated) |
| `--work-dir` | Clone directory for repos without `dest_path_relative` |
| `--dry-run` | Preview without creating PRs |
| `--skip-verify` | Skip verification steps |
| `--pr-reviewers` | Override PR reviewers (comma-separated) |
| `--pr-assignees` | Override PR assignees (comma-separated) |

### Failure Strategies

- **skip**: Skip PR for this repo, continue with others (default)
- **fail**: Stop all processing immediately
- **warn**: Create PR anyway with warning in body

Per-step `on_fail` overrides the verify-level default.

### GitHub Actions

```yaml
name: dep-update
on:
  schedule:
    - cron: "0 6 * * 1"  # Weekly Monday
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uvx path-sync dep-update -n myconfig
        env:
          GH_TOKEN: ${{ secrets.GH_PAT }}
```

## Alternatives Considered

| Tool | Why Not |
|------|---------|
| [repo-file-sync-action](https://github.com/BetaHuhn/repo-file-sync-action) | No local CLI, no validation |
| [Copier](https://copier.readthedocs.io/) | Merge-based (conflicts), no multi-dest |
| [Cruft](https://cruft.github.io/cruft/) | Patch-based, single dest |

**Why path-sync:**
- One SRC to many DEST repos
- Local CLI + CI support
- Section-level sync for shared files
- Validation enforced across repos
- Clear ownership (no merge conflicts)
