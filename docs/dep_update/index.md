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
- [source](../../path_sync/_internal/cmd_dep_update.py#L61)
> **Since:** 0.4.0

```python
def dep_update(*, name: str = ..., dest_filter: str = '', work_dir: str = '', dry_run: bool = False, skip_verify: bool = False, src_root_opt: str = '', pr_reviewers: str = '', pr_assignees: str = '') -> None:
    ...
```

Run dependency updates across repositories.

**CLI Options:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `-n`, `--name` | `str` | *required* | Config name |
| `-d`, `--dest` | `str` | `''` | Filter destinations (comma-separated) |
| `--work-dir` | `str` | `''` | Clone repos here (overrides dest_path_relative) |
| `--dry-run` | `bool` | `False` | Preview without creating PRs |
| `--skip-verify` | `bool` | `False` | Skip verification steps |
| `--src-root` | `str` | `''` | Source repo root |
| `--pr-reviewers` | `str` | `''` | Comma-separated PR reviewers |
| `--pr-assignees` | `str` | `''` | Comma-separated PR assignees |

### Changes

| Version | Change |
|---------|--------|
| unreleased | fix(dep-update): add user confirmation for removing invalid git repositories |
| unreleased | fix(dep-update): handle corrupted git repos and reset existing repos to default branch |
| 0.4.0 | Made public |
<!-- === OK_EDIT: pkg-ext dep_update_def === -->