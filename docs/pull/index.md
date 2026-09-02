<!-- === DO_NOT_EDIT: pkg-ext header === -->
# pull

<!-- === OK_EDIT: pkg-ext header === -->

<!-- === DO_NOT_EDIT: pkg-ext symbols === -->
- [`pull`](#pull_def)
- [PullOptions](./pulloptions.md)
<!-- === OK_EDIT: pkg-ext symbols === -->

<!-- === DO_NOT_EDIT: pkg-ext pull_def === -->
<a id="pull_def"></a>

### cli_command: `pull`
- [source](../../path_sync/_internal/cmd_pull.py#L356)
> **Since:** unreleased

```python
def pull(
    *,
    name: str = "",
    config_path_opt: str = "",
    src_root_opt: str = "",
    dest_name: str = ...,
    dry_run: bool = False,
    dest_only: bool = False,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> None: ...
```

Harvest newer mapped dest files into src after one confirm.

--dest-only also copies dest-only files. Quote glob patterns (e.g. -i '.cursor/*').

**CLI Options:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `-n`, `--name` | `str` | `''` | Config name |
| `-c`, `--config-path` | `str` | `''` | Full path to config file |
| `--src-root` | `str` | `''` | Source repo root |
| `-d`, `--dest` | `str` | *required* | Destination name (exactly one) |
| `--dry-run` | `bool` | `False` | Print candidates without writing (same as non-TTY) |
| `--dest-only` | `bool` | `False` | Also harvest dest files with no src counterpart |

### Changes

| Version | Change |
|---------|--------|
| unreleased | Made public |
<!-- === OK_EDIT: pkg-ext pull_def === -->