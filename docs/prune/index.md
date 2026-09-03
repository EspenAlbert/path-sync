<!-- === DO_NOT_EDIT: pkg-ext header === -->
# prune

<!-- === OK_EDIT: pkg-ext header === -->

<!-- === DO_NOT_EDIT: pkg-ext symbols === -->
- [`prune`](#prune_def)
<!-- === OK_EDIT: pkg-ext symbols === -->

<!-- === DO_NOT_EDIT: pkg-ext prune_def === -->
<a id="prune_def"></a>

### cli_command: `prune`
- [source](../../path_sync/_internal/cmd_prune.py#L54)
> **Since:** unreleased

```python
def prune(
    *,
    name: str = "",
    config_path_opt: str = "",
    src_root_opt: str = "",
    dest_name: str = ...,
    dry_run: bool = False,
    include: list[str] = [],
    exclude: list[str] = [],
) -> None: ...
```

Delete dest-only files after one confirm.

Quote glob patterns (e.g. -i '.cursor/*').

**CLI Options:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `-n`, `--name` | `str` | `''` | Config name |
| `-c`, `--config-path` | `str` | `''` | Full path to config file |
| `--src-root` | `str` | `''` | Source repo root |
| `-d`, `--dest` | `str` | *required* | Destination name (exactly one) |
| `--dry-run` | `bool` | `False` | Print candidates without deleting |
| `-i`, `--include` | `list[str]` | `[]` | Keep paths matching pattern |
| `-e`, `--exclude` | `list[str]` | `[]` | Drop paths matching pattern |

### Changes

| Version | Change |
|---------|--------|
| unreleased | Made public |
<!-- === OK_EDIT: pkg-ext prune_def === -->