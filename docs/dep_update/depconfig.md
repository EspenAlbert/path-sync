# DepConfig

<!-- === DO_NOT_EDIT: pkg-ext depconfig_def === -->
## class: DepConfig
- [source](../../path_sync/_internal/models_dep.py#L29)
> **Since:** 0.4.0

```python
class DepConfig(BaseModel):
    name: str
    from_config: str
    include_destinations: list[str] = ...
    exclude_destinations: list[str] = ...
    updates: list[UpdateEntry]
    verify: VerifyConfig = ...
    pr: PRConfig
    auto_merge: AutoMergeConfig | None = None
    keep_pr_on_no_changes: bool = False
```
<!-- === OK_EDIT: pkg-ext depconfig_def === -->

### Fields

| Field | Type | Default | Since |
|---|---|---|---|
| name | `str` | - | 0.4.0 |
| from_config | `str` | - | 0.4.0 |
| include_destinations | `list[str]` | `...` | 0.4.0 |
| exclude_destinations | `list[str]` | `...` | 0.4.0 |
| updates | `list[UpdateEntry]` | - | 0.4.0 |
| verify | `VerifyConfig` | `...` | 0.4.0 |
| pr | `PRConfig` | - | 0.4.0 |

<!-- === DO_NOT_EDIT: pkg-ext depconfig_changes === -->
### Changes

| Version | Change |
|---------|--------|
| 0.7.3 | added optional field 'keep_pr_on_no_changes' (default: False) |
| 0.7.0 | added optional field 'auto_merge' (default: None) |
| 0.4.1 | added base class 'BaseModel' |
| 0.4.0 | Made public |
<!-- === OK_EDIT: pkg-ext depconfig_changes === -->