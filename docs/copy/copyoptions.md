# CopyOptions

<!-- === DO_NOT_EDIT: pkg-ext copyoptions_def === -->
## class: CopyOptions
- [source](../../path_sync/_internal/cmd_copy.py#L47)
> **Since:** 0.3.0

```python
class CopyOptions(BaseModel):
    dry_run: bool = False
    force_overwrite: bool = False
    no_checkout: bool = False
    checkout_from_default: bool = False
    skip_commit: bool = False
    no_prompt: bool = False
    no_pr: bool = False
    skip_orphan_cleanup: bool = False
    skip_verify: bool = False
    no_wait: bool = False
    no_auto_merge: bool = False
    pr_title: str = ''
    labels: list[str] | None = None
    reviewers: list[str] | None = None
    assignees: list[str] | None = None
```
<!-- === OK_EDIT: pkg-ext copyoptions_def === -->

### Fields

| Field | Type | Default | Since |
|---|---|---|---|
| dry_run | `bool` | `False` | 0.3.0 |
| force_overwrite | `bool` | `False` | 0.3.0 |
| no_checkout | `bool` | `False` | 0.3.0 |
| checkout_from_default | `bool` | `False` | 0.3.0 |
| local | `bool` | `False` | 0.3.0 |
| no_prompt | `bool` | `False` | 0.3.0 |
| no_pr | `bool` | `False` | 0.3.0 |
| skip_orphan_cleanup | `bool` | `False` | 0.3.0 |
| pr_title | `str` | `''` | 0.3.0 |
| labels | `list[str] | None` | `None` | unreleased |
| reviewers | `list[str] | None` | `None` | unreleased |
| assignees | `list[str] | None` | `None` | unreleased |

<!-- === DO_NOT_EDIT: pkg-ext copyoptions_changes === -->
### Changes

| Version | Change |
|---------|--------|
| unreleased | added optional field 'no_auto_merge' (default: False) |
| unreleased | added optional field 'no_wait' (default: False) |
| 0.6.0 | added optional field 'skip_commit' (default: False) |
| 0.6.0 | removed field 'local' |
| 0.6.0 | added optional field 'skip_verify' (default: False) |
| 0.4.1 | added base class 'BaseModel' |
| 0.4.1 | added optional field 'reviewers' (default: None) |
| 0.4.1 | added optional field 'labels' (default: None) |
| 0.4.1 | added optional field 'assignees' (default: None) |
| 0.4.1 | removed field 'pr_labels' |
| 0.4.1 | removed field 'pr_assignees' |
| 0.4.1 | removed field 'pr_reviewers' |
| 0.3.0 | Made public |
<!-- === OK_EDIT: pkg-ext copyoptions_changes === -->