# CommitConfig

<!-- === DO_NOT_EDIT: pkg-ext commitconfig_def === -->
## class: CommitConfig
- [source](../../path_sync/_internal/models.py#L57)
> **Since:** 0.4.0

```python
class CommitConfig(BaseModel):
    message: str
    add_paths: list[str] = ...
```
<!-- === OK_EDIT: pkg-ext commitconfig_def === -->

### Fields

| Field | Type | Default | Since |
|---|---|---|---|
| message | `str` | - | 0.4.0 |
| add_paths | `list[str]` | `...` | 0.4.0 |

<!-- === DO_NOT_EDIT: pkg-ext commitconfig_changes === -->
### Changes

| Version | Change |
|---------|--------|
| 0.4.1 | added base class 'BaseModel' |
| 0.4.0 | Made public |
<!-- === OK_EDIT: pkg-ext commitconfig_changes === -->