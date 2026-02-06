# VerifyConfig

<!-- === DO_NOT_EDIT: pkg-ext verifyconfig_def === -->
## class: VerifyConfig
- [source](../../path_sync/_internal/models.py#L55)
> **Since:** 0.4.0

```python
class VerifyConfig(BaseModel):
    on_fail: OnFailStrategy = <OnFailStrategy.WARN: 'warn'>
    steps: list[VerifyStep] = ...
```
<!-- === OK_EDIT: pkg-ext verifyconfig_def === -->

### Fields

| Field | Type | Default | Since |
|---|---|---|---|
| on_fail | `OnFailStrategy` | `<OnFailStrategy.SKIP: 'skip'>` | 0.4.0 |
| steps | `list[VerifyStep]` | `...` | 0.4.0 |

<!-- === DO_NOT_EDIT: pkg-ext verifyconfig_changes === -->
### Changes

| Version | Change |
|---------|--------|
| 0.6.0 | field 'on_fail' default: <OnFailStrategy.SKIP: 'skip'> -> <OnFailStrategy.WARN: 'warn'> |
| 0.4.1 | added base class 'BaseModel' |
| 0.4.0 | Made public |
<!-- === OK_EDIT: pkg-ext verifyconfig_changes === -->