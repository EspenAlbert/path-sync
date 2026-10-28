<!-- === DO_NOT_EDIT: pkg-ext header === -->
# merge

<!-- === OK_EDIT: pkg-ext header === -->

<!-- === DO_NOT_EDIT: pkg-ext symbols === -->
- [`merge`](#merge_def)
<!-- === OK_EDIT: pkg-ext symbols === -->

<!-- === DO_NOT_EDIT: pkg-ext merge_def === -->
<a id="merge_def"></a>

### cli_command: `merge`
- [source](../../path_sync/_internal/cmd_merge.py#L401)
> **Since:** unreleased

```python
def merge(
    *,
    name: str = "",
    config_path_opt: str = "",
    src_root_opt: str = "",
    dest_filter: list[str] = [],
    dry_run: bool = False,
    include: list[str] = [],
    exclude: list[str] = [],
) -> None: ...
```

Reconcile destination changes into src before the next copy.

Recovers the last-synced base from both repos' histories, prefers the changed side, and
combines non-overlapping changes. Writes and commits src, then prints the copy hint.
merge never runs copy.

**CLI Options:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `-n`, `--name` | `str` | `''` | Config name |
| `-c`, `--config-path` | `str` | `''` | Full path to config file |
| `--src-root` | `str` | `''` | Source repo root |
| `-d`, `--dest` | `list[str]` | `[]` | Destination filter (repeatable or comma-separated) |
| `--dry-run` | `bool` | `False` | Print classifications without writing |
| `-i`, `--include` | `list[str]` | `[]` | Keep paths matching pattern |
| `-e`, `--exclude` | `list[str]` | `[]` | Drop paths matching pattern |

### Changes

| Version | Change |
|---------|--------|
| unreleased | Made public |
<!-- === OK_EDIT: pkg-ext merge_def === -->