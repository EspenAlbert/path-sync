# SrcConfig

<!-- === DO_NOT_EDIT: pkg-ext srcconfig_def === -->
## class: SrcConfig
- [source](../../path_sync/_internal/models.py#L209)
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
    path_groups: dict[str, list[PathMapping]] = ...
    destinations: list[Destination] = ...
    verify: VerifyConfig | None = None
    wrap_synced_files: bool = False
    auto_merge: AutoMergeConfig | None = None
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
| 0.7.2 | added optional field 'path_groups' (default: ...) |
| 0.7.0 | added optional field 'auto_merge' (default: None) |
| 0.6.0 | added optional field 'wrap_synced_files' (default: False) |
| 0.6.0 | added optional field 'verify' (default: None) |
| 0.4.1 | added base class 'BaseModel' |
| 0.4.0 | field 'name' default removed (was: PydanticUndefined) |
| 0.3.0 | Made public |
<!-- === OK_EDIT: pkg-ext srcconfig_changes === -->