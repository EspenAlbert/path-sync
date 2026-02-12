# HeaderConfig

<!-- === DO_NOT_EDIT: pkg-ext headerconfig_def === -->
## class: HeaderConfig
- [source](../../path_sync/_internal/models.py#L122)
> **Since:** 0.3.0

```python
class HeaderConfig(BaseModel):
    comment_prefixes: dict[str, str] = ...
    comment_suffixes: dict[str, str] = ...
```
<!-- === OK_EDIT: pkg-ext headerconfig_def === -->

### Fields

| Field | Type | Default | Since |
|---|---|---|---|
| comment_prefixes | `dict[str, str]` | `...` | 0.3.0 |
| comment_suffixes | `dict[str, str]` | `...` | 0.3.0 |

<!-- === DO_NOT_EDIT: pkg-ext headerconfig_changes === -->
### Changes

| Version | Change |
|---------|--------|
| 0.4.1 | added base class 'BaseModel' |
| 0.3.0 | Made public |
<!-- === OK_EDIT: pkg-ext headerconfig_changes === -->