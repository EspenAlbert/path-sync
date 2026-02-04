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
> **Since:** unreleased

```python
def validate_no_changes(*, branch: str = 'main', skip_sections_opt: str = '', src_root_opt: str = '') -> None:
    ...
```

Validate no unauthorized changes to synced files.

**CLI Options:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `-b`, `--branch` | `str` | `'main'` | Default branch to compare against |
| `--skip-sections` | `str` | `''` | Comma-separated path:section_id pairs to skip (e.g., 'justfile:coverage,pyproject.toml:default') |
| `--src-root` | `str` | `''` | Source repo root (default: find git root from cwd) |

### Changes

| Version | Change |
|---------|--------|
| unreleased | Made public |
<!-- === OK_EDIT: pkg-ext validate_no_changes_def === -->