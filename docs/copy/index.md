<!-- === DO_NOT_EDIT: pkg-ext header === -->
# copy

<!-- === OK_EDIT: pkg-ext header === -->

<!-- === DO_NOT_EDIT: pkg-ext symbols === -->
- [`copy`](#copy_def)
- [CopyOptions](./copyoptions.md)
<!-- === OK_EDIT: pkg-ext symbols === -->


<!-- === DO_NOT_EDIT: pkg-ext copy_def === -->
<a id="copy_def"></a>

### cli_command: `copy`
- [source](../../path_sync/_internal/cmd_copy.py#L66)
> **Since:** 0.4.1

```python
def copy(*, name: str = '', config_path_opt: str = '', src_root_opt: str = '', dest_filter: str = '', dry_run: bool = False, force_overwrite: bool = False, detailed_exit_code: bool = False, no_checkout: bool = False, checkout_from_default: bool = False, skip_commit: bool = False, no_prompt: bool = False, no_pr: bool = False, pr_title: str = '', pr_labels: str = '', pr_reviewers: str = '', pr_assignees: str = '', skip_orphan_cleanup: bool = False, skip_verify: bool = False, no_wait: bool = False, no_auto_merge: bool = False) -> None:
    ...
```

Copy files from SRC to DEST repositories.

**CLI Options:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `-n`, `--name` | `str` | `''` | Config name (used with src-root to find config) |
| `-c`, `--config-path` | `str` | `''` | Full path to config file (alternative to --name) |
| `--src-root` | `str` | `''` | Source repo root (default: find git root from cwd) |
| `-d`, `--dest` | `str` | `''` | Filter destinations (comma-separated) |
| `--dry-run` | `bool` | `False` | Preview without writing |
| `--force-overwrite` | `bool` | `False` | Overwrite files even if header removed (opted out) |
| `--detailed-exit-code` | `bool` | `False` | Exit 0=no changes, 1=changes, 2=error |
| `--no-checkout` | `bool` | `False` | Skip branch switching before sync |
| `--checkout-from-default` | `bool` | `False` | Reset to origin/default before sync (for CI) |
| `--skip-commit`, `--local` | `bool` | `False` | No git operations after sync (no commit/push/PR) |
| `-y`, `--no-prompt` | `bool` | `False` | Skip confirmations (for CI) |
| `--no-pr` | `bool` | `False` | Push but skip PR creation |
| `--pr-title` | `str` | `''` | Override PR title (supports {name}, {dest_name}) |
| `--pr-labels` | `str` | `''` | Comma-separated PR labels |
| `--pr-reviewers` | `str` | `''` | Comma-separated PR reviewers |
| `--pr-assignees` | `str` | `''` | Comma-separated PR assignees |
| `--skip-orphan-cleanup` | `bool` | `False` | Skip deletion of orphaned synced files |
| `--skip-verify` | `bool` | `False` | Skip verification steps after syncing |
| `--no-wait` | `bool` | `False` | Enable auto-merge but skip polling for merge completion |
| `--no-auto-merge` | `bool` | `False` | Skip auto-merge even when configured |

### Changes

| Version | Change |
|---------|--------|
| 0.7.4 | fix(copy): skip PR close when running with --local/--skip-commit |
| 0.7.1 | fix(cmd_copy): add warning for unknown comment prefix in sync process |
| 0.6.0 | fix(copy): apply skip_sections when creating new files with sections |
| 0.6.0 | fix(copy): commit synced files before running verify steps |
| 0.4.1 | Made public |
| 0.3.5 | fix: --no-checkout was checked before --dry-run, so the dry-run flag was ignored when both were passed. |
| 0.3.2 | fix: handle binary file copying and improve error handling for text reading |
<!-- === OK_EDIT: pkg-ext copy_def === -->
