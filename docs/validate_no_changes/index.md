<!-- === DO_NOT_EDIT: pkg-ext header === -->
# validate_no_changes

<!-- === OK_EDIT: pkg-ext header === -->

<!-- === DO_NOT_EDIT: pkg-ext symbols === -->
- [`validate_no_changes`](#validate_no_changes_def)
<!-- === OK_EDIT: pkg-ext symbols === -->

<!-- === DO_NOT_EDIT: pkg-ext validate_no_changes_def === -->
<a id="validate_no_changes_def"></a>

### cli_command: `validate_no_changes`
- [source](../../path_sync/_internal/cmd_validate.py#L16)
> **Since:** 0.4.1

```python
def validate_no_changes(*, branch: str = 'main', skip_sections_opt: str = '', src_root_opt: str = '') -> None:
    ...
```

Validate no unauthorized changes to synced files.

**CLI Options:**

| Flag | Type | Default | Env Var | Description |
|---|---|---|---|---|
| `-b`, `--branch` | `str` | `'main'` | `GITHUB_BASE_REF` | Branch to compare against (default: main; uses GITHUB_BASE_REF when set and -b not passed) |
| `--skip-sections` | `str` | `''` | - | Comma-separated path:section_id pairs to skip (e.g., 'justfile:coverage,pyproject.toml:default') |
| `--src-root` | `str` | `''` | - | Source repo root (default: find git root from cwd) |

### Changes

| Version | Change |
|---------|--------|
| unreleased | fix: Allows using GITHUB_BASE_REF when validating no changes |
| 0.4.1 | Made public |
<!-- === OK_EDIT: pkg-ext validate_no_changes_def === -->