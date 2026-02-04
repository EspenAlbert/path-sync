# PathMapping

<!-- === DO_NOT_EDIT: pkg-ext pathmapping_def === -->
## class: PathMapping
- [source](../../path_sync/_internal/models.py#L38)
> **Since:** 0.3.0

```python
class PathMapping(BaseModel):
    src_path: str
    dest_path: str = ''
    sync_mode: SyncMode = <SyncMode.SYNC: 'sync'>
    exclude_dirs: set[str] = ...
    exclude_file_patterns: set[str] = ...
```
<!-- === OK_EDIT: pkg-ext pathmapping_def === -->

### Fields

| Field | Type | Default | Since |
|---|---|---|---|
| src_path | `str` | - | 0.3.0 |
| dest_path | `str` | `''` | 0.3.0 |
| sync_mode | `SyncMode` | `<SyncMode.SYNC: 'sync'>` | 0.3.0 |
| exclude_dirs | `set[str]` | `...` | 0.3.0 |
| exclude_file_patterns | `set[str]` | `...` | 0.3.0 |

<!-- === DO_NOT_EDIT: pkg-ext pathmapping_changes === -->
### Changes

| Version | Change |
|---------|--------|
| unreleased | added base class 'BaseModel' |
| 0.4.0 | field 'src_path' default removed (was: PydanticUndefined) |
| 0.3.0 | Made public |
<!-- === OK_EDIT: pkg-ext pathmapping_changes === -->