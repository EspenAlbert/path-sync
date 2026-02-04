# DepConfig

<!-- === DO_NOT_EDIT: pkg-ext depconfig_def === -->
## class: DepConfig
- [source](../../path_sync/_internal/models_dep.py#L46)
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
| unreleased | added base class 'BaseModel' |
| 0.4.0 | Made public |
<!-- === OK_EDIT: pkg-ext depconfig_changes === -->