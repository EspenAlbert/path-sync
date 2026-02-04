<!-- === DO_NOT_EDIT: pkg-ext header === -->
# dep_update

<!-- === OK_EDIT: pkg-ext header === -->

<!-- === DO_NOT_EDIT: pkg-ext symbols === -->
- [`dep_update`](#dep_update_def)
- [CommitConfig](./commitconfig.md)
- [DepConfig](./depconfig.md)
- [OnFailStrategy](./onfailstrategy.md)
- [PRConfig](./prconfig.md)
- [UpdateEntry](./updateentry.md)
- [VerifyConfig](./verifyconfig.md)
- [VerifyStep](./verifystep.md)
<!-- === OK_EDIT: pkg-ext symbols === -->


<!-- === DO_NOT_EDIT: pkg-ext dep_update_def === -->
<a id="dep_update_def"></a>

### cli_command: `dep_update`
- [source](../../path_sync/_internal/cmd_dep_update.py#L66)
> **Since:** 0.4.0

```python
def dep_update(*, name: str = ..., dest_filter: str = '', work_dir: str = '', dry_run: bool = False, skip_verify: bool = False, src_root_opt: str = '') -> None:
    ...
```

Run dependency updates across repositories.

**CLI Options:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `-n`, `--name` | `str` | *required* | Config name |
| `-d`, `--dest` | `str` | `''` | Filter destinations (comma-separated) |
| `--work-dir` | `str` | `''` | Directory for cloning repos |
| `--dry-run` | `bool` | `False` | Preview without creating PRs |
| `--skip-verify` | `bool` | `False` | Skip verification steps |
| `--src-root` | `str` | `''` | Source repo root |

### Changes

| Version | Change |
|---------|--------|
| 0.4.0 | Made public |
<!-- === OK_EDIT: pkg-ext dep_update_def === -->