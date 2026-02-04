# UpdateEntry

<!-- === DO_NOT_EDIT: pkg-ext updateentry_def === -->
## class: UpdateEntry
- [source](../../path_sync/_internal/models_dep.py#L35)
> **Since:** 0.4.0

```python
class UpdateEntry(BaseModel):
    workdir: str = '.'
    command: str
```
<!-- === OK_EDIT: pkg-ext updateentry_def === -->

### Fields

| Field | Type | Default | Since |
|---|---|---|---|
| workdir | `str` | `'.'` | 0.4.0 |
| command | `str` | - | 0.4.0 |

<!-- === DO_NOT_EDIT: pkg-ext updateentry_changes === -->
### Changes

| Version | Change |
|---------|--------|
| unreleased | added base class 'BaseModel' |
| 0.4.0 | Made public |
<!-- === OK_EDIT: pkg-ext updateentry_changes === -->