<!-- === DO_NOT_EDIT: pkg-ext header === -->
# config

<!-- === OK_EDIT: pkg-ext header === -->

<!-- === DO_NOT_EDIT: pkg-ext symbols === -->
- [`AutoMergeConfig`](#automergeconfig_def)
- [Destination](./destination.md)
- [HeaderConfig](./headerconfig.md)
- [`MergeMethod`](#mergemethod_def)
- [PRDefaults](./prdefaults.md)
- [PathMapping](./pathmapping.md)
- [SrcConfig](./srcconfig.md)
- [SyncMode](./syncmode.md)
<!-- === OK_EDIT: pkg-ext symbols === -->
<!-- === DO_NOT_EDIT: pkg-ext symbol_details_header === -->
## Symbol Details
<!-- === OK_EDIT: pkg-ext symbol_details_header === -->
<!-- === DO_NOT_EDIT: pkg-ext automergeconfig_def === -->
<a id="automergeconfig_def"></a>

### class: `AutoMergeConfig`
- [source](../../path_sync/_internal/models.py#L39)
> **Since:** 0.7.0

```python
class AutoMergeConfig(BaseModel):
    method: MergeMethod = <MergeMethod.MERGE: 'merge'>
    delete_branch: bool = True
    poll_interval_seconds: int = 30
    timeout_seconds: int = 900
```

| Field | Type | Default | Since |
|---|---|---|---|
| method | `MergeMethod` | `<MergeMethod.MERGE: 'merge'>` | 0.7.0 |
| delete_branch | `bool` | `True` | 0.7.0 |
| poll_interval_seconds | `int` | `30` | 0.7.0 |
| timeout_seconds | `int` | `900` | 0.7.0 |

### Changes

| Version | Change |
|---------|--------|
| 0.7.0 | Made public |
<!-- === OK_EDIT: pkg-ext automergeconfig_def === -->
<!-- === DO_NOT_EDIT: pkg-ext mergemethod_def === -->
<a id="mergemethod_def"></a>

### class: `MergeMethod`
- [source](../../path_sync/_internal/models.py#L33)
> **Since:** 0.7.0

```python
class MergeMethod(StrEnum):
    ...
```

### Changes

| Version | Change |
|---------|--------|
| 0.7.0 | Made public |
<!-- === OK_EDIT: pkg-ext mergemethod_def === -->

