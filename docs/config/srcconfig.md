# SrcConfig

<!-- === DO_NOT_EDIT: pkg-ext srcconfig_def === -->
## class: SrcConfig
- [source](../../path_sync/_internal/models.py#L133)
> **Since:** 0.3.0

```python
class SrcConfig(BaseModel):
    name: str
    git_remote: str = 'origin'
    src_repo_url: str = ''
    schedule: str = '0 6 * * *'
    header_config: HeaderConfig = ...
    pr_defaults: PRDefaults = ...
    paths: list[PathMapping] = ...
    destinations: list[Destination] = ...
```
<!-- === OK_EDIT: pkg-ext srcconfig_def === -->

### Fields

| Field | Type | Default | Since |
|---|---|---|---|
| name | `str` | - | 0.3.0 |
| git_remote | `str` | `'origin'` | 0.3.0 |
| src_repo_url | `str` | `''` | 0.3.0 |
| schedule | `str` | `'0 6 * * *'` | 0.3.0 |
| header_config | `HeaderConfig` | `...` | 0.3.0 |
| pr_defaults | `PRDefaults` | `...` | 0.3.0 |
| paths | `list[PathMapping]` | `...` | 0.3.0 |
| destinations | `list[Destination]` | `...` | 0.3.0 |

<!-- === DO_NOT_EDIT: pkg-ext srcconfig_changes === -->
### Changes

| Version | Change |
|---------|--------|
| 0.3.0 | Made public |
| unreleased | field 'name' default removed (was: PydanticUndefined) |
<!-- === OK_EDIT: pkg-ext srcconfig_changes === -->