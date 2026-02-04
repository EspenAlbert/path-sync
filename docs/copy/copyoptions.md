# CopyOptions

<!-- === DO_NOT_EDIT: pkg-ext copyoptions_def === -->
## class: CopyOptions
- [source](../../path_sync/_internal/cmd_copy.py#L72)
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
    pr_labels: str = ''
    pr_reviewers: str = ''
    pr_assignees: str = ''
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
| 0.4.1 | added base class 'BaseModel' |
| 0.3.0 | Made public |
<!-- === OK_EDIT: pkg-ext copyoptions_changes === -->