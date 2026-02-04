# Destination

<!-- === DO_NOT_EDIT: pkg-ext destination_def === -->
## class: Destination
- [source](../../path_sync/_internal/models.py#L122)
> **Since:** 0.3.0

```python
class Destination(BaseModel):
    name: str
    repo_url: str = ''
    dest_path_relative: str
    copy_branch: str = ''
    default_branch: str = 'main'
    skip_sections: dict[str, list[str]] = ...
    skip_file_patterns: set[str] = ...
```
<!-- === OK_EDIT: pkg-ext destination_def === -->

### Fields

| Field | Type | Default | Since |
|---|---|---|---|
| name | `str` | - | 0.3.0 |
| repo_url | `str` | `''` | 0.3.0 |
| dest_path_relative | `str` | - | 0.3.0 |
| copy_branch | `str` | `''` | 0.3.0 |
| default_branch | `str` | `'main'` | 0.3.0 |
| skip_sections | `dict[str, list[str]]` | `...` | 0.3.0 |
| skip_file_patterns | `set[str]` | `...` | 0.3.0 |

<!-- === DO_NOT_EDIT: pkg-ext destination_changes === -->
### Changes

| Version | Change |
|---------|--------|
| unreleased | added base class 'BaseModel' |
| 0.4.0 | field 'name' default removed (was: PydanticUndefined) |
| 0.4.0 | field 'dest_path_relative' default removed (was: PydanticUndefined) |
| 0.3.0 | Made public |
<!-- === OK_EDIT: pkg-ext destination_changes === -->