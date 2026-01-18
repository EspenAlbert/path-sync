<!-- === DO_NOT_EDIT: pkg-ext header === -->
# copy

<!-- === OK_EDIT: pkg-ext header === -->

<!-- === DO_NOT_EDIT: pkg-ext symbols === -->
- [`CopyOptions`](#copyoptions_def)
<!-- === OK_EDIT: pkg-ext symbols === -->

<!-- === DO_NOT_EDIT: pkg-ext symbol_details_header === -->
## Symbol Details
<!-- === OK_EDIT: pkg-ext symbol_details_header === -->

<!-- === DO_NOT_EDIT: pkg-ext copyoptions_def === -->
### class: `CopyOptions`
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
| pr_labels | `str` | `''` | 0.3.0 |
| pr_reviewers | `str` | `''` | 0.3.0 |
| pr_assignees | `str` | `''` | 0.3.0 |
<!-- === OK_EDIT: pkg-ext copyoptions_def === -->