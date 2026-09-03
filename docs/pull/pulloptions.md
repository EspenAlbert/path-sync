# PullOptions

<!-- === DO_NOT_EDIT: pkg-ext pulloptions_def === -->
## class: PullOptions
- [source](../../path_sync/_internal/cmd_pull.py#L45)
> **Since:** 0.8.0

```python
class PullOptions(BaseModel):
    dry_run: bool = False
    dest_only: bool = False
    include: list[str] = ...
    exclude: list[str] = ...
```
<!-- === OK_EDIT: pkg-ext pulloptions_def === -->

### Fields

| Field | Type | Default | Since |
|---|---|---|---|
| dry_run | `bool` | `False` | unreleased |
| dest_only | `bool` | `False` | unreleased |
| include | `list[str]` | `...` | unreleased |
| exclude | `list[str]` | `...` | unreleased |

<!-- === DO_NOT_EDIT: pkg-ext pulloptions_changes === -->
### Changes

| Version | Change |
|---------|--------|
| 0.8.0 | removed field 'show_only' |
| 0.8.0 | Made public |
<!-- === OK_EDIT: pkg-ext pulloptions_changes === -->