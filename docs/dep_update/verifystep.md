# VerifyStep

<!-- === DO_NOT_EDIT: pkg-ext verifystep_def === -->
## class: VerifyStep
- [source](../../path_sync/_internal/models_dep.py#L24)
> **Since:** 0.4.0

```python
class VerifyStep(BaseModel):
    run: str
    commit: CommitConfig | None = None
    on_fail: OnFailStrategy | None = None
```
<!-- === OK_EDIT: pkg-ext verifystep_def === -->

### Fields

| Field | Type | Default | Since |
|---|---|---|---|
| run | `str` | - | 0.4.0 |
| commit | `CommitConfig | None` | `None` | unreleased |
| on_fail | `OnFailStrategy | None` | `None` | unreleased |

<!-- === DO_NOT_EDIT: pkg-ext verifystep_changes === -->
### Changes

| Version | Change |
|---------|--------|
| unreleased | field 'on_fail' default added: None |
| unreleased | field 'commit' default added: None |
| unreleased | added base class 'BaseModel' |
| 0.4.0 | Made public |
<!-- === OK_EDIT: pkg-ext verifystep_changes === -->