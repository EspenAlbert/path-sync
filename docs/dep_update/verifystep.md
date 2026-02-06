# VerifyStep

<!-- === DO_NOT_EDIT: pkg-ext verifystep_def === -->
## class: VerifyStep
- [source](../../path_sync/_internal/models.py#L49)
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
| 0.4.1 | field 'on_fail' default added: None |
| 0.4.1 | field 'commit' default added: None |
| 0.4.1 | added base class 'BaseModel' |
| 0.4.0 | Made public |
<!-- === OK_EDIT: pkg-ext verifystep_changes === -->