# CopyOptions

<!-- === DO_NOT_EDIT: pkg-ext copyoptions_def === -->
## class: CopyOptions
- [source](../../path_sync/_internal/cmd_copy.py#L55)
> **Since:** 0.3.0

```python
class CopyOptions(BaseModel):
    dry_run: bool = False
    force_overwrite: bool = False
    no_checkout: bool = False
    checkout_from_default: bool = False
    local: bool = False
    no_prompt: bool = False
    no_pr: bool = False
    skip_orphan_cleanup: bool = False
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
| labels | `list[str] | None` | - | 0.3.0 |
| reviewers | `list[str] | None` | - | 0.3.0 |
| assignees | `list[str] | None` | - | 0.3.0 |

<!-- === DO_NOT_EDIT: pkg-ext copyoptions_changes === -->
### Changes

| Version | Change |
|---------|--------|
| unreleased | added optional field 'reviewers' (default: None) |
| unreleased | added optional field 'labels' (default: None) |
| unreleased | added optional field 'assignees' (default: None) |
| unreleased | added base class 'BaseModel' |
| unreleased | removed field 'pr_labels' |
| unreleased | removed field 'pr_assignees' |
| unreleased | removed field 'pr_reviewers' |
| 0.3.0 | Made public |
<!-- === OK_EDIT: pkg-ext copyoptions_changes === -->