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
- [source](../../path_sync/_internal/models.py#L38)
> **Since:** unreleased

```python
class AutoMergeConfig(BaseModel):
    method: MergeMethod = <MergeMethod.MERGE: 'merge'>
    delete_branch: bool = True
    poll_interval_seconds: int = 30
    timeout_seconds: int = 900
```

| Field | Type | Default | Since |
|---|---|---|---|
| method | `MergeMethod` | `<MergeMethod.MERGE: 'merge'>` | unreleased |
| delete_branch | `bool` | `True` | unreleased |
| poll_interval_seconds | `int` | `30` | unreleased |
| timeout_seconds | `int` | `900` | unreleased |

### Changes

| Version | Change |
|---------|--------|
| unreleased | Made public |
<!-- === OK_EDIT: pkg-ext automergeconfig_def === -->
<!-- === DO_NOT_EDIT: pkg-ext mergemethod_def === -->
<a id="mergemethod_def"></a>

### class: `MergeMethod`
- [source](../../path_sync/_internal/models.py#L32)
> **Since:** unreleased

```python
class MergeMethod(StrEnum):
    ...
```

### Changes

| Version | Change |
|---------|--------|
| unreleased | Made public |
<!-- === OK_EDIT: pkg-ext mergemethod_def === -->

