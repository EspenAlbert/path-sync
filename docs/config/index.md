<!-- === DO_NOT_EDIT: pkg-ext header === -->
# config

<!-- === OK_EDIT: pkg-ext header === -->

<!-- === DO_NOT_EDIT: pkg-ext symbols === -->
- [Destination](./destination.md)
- [`HeaderConfig`](#headerconfig_def)
- [`PRDefaults`](#prdefaults_def)
- [PathMapping](./pathmapping.md)
- [SrcConfig](./srcconfig.md)
- [`SyncMode`](#syncmode_def)
<!-- === OK_EDIT: pkg-ext symbols === -->

<!-- === DO_NOT_EDIT: pkg-ext symbol_details_header === -->
## Symbol Details
<!-- === OK_EDIT: pkg-ext symbol_details_header === -->

<!-- === DO_NOT_EDIT: pkg-ext headerconfig_def === -->
<a id="headerconfig_def"></a>

### class: `HeaderConfig`
- [source](../../path_sync/_internal/models.py#L69)
> **Since:** 0.3.0

```python
class HeaderConfig(BaseModel):
    comment_prefixes: dict[str, str] = ...
    comment_suffixes: dict[str, str] = ...
```

| Field | Type | Default | Since |
|---|---|---|---|
| comment_prefixes | `dict[str, str]` | `...` | 0.3.0 |
| comment_suffixes | `dict[str, str]` | `...` | 0.3.0 |

### Changes

| Version | Change |
|---------|--------|
| 0.3.0 | Made public |
<!-- === OK_EDIT: pkg-ext headerconfig_def === -->
<!-- === DO_NOT_EDIT: pkg-ext prdefaults_def === -->
<a id="prdefaults_def"></a>

### class: `PRDefaults`
- [source](../../path_sync/_internal/models.py#L96)
> **Since:** 0.3.0

```python
class PRDefaults(PRFieldsBase):
    labels: list[str] = ...
    reviewers: list[str] = ...
    assignees: list[str] = ...
    title: str = 'chore: sync {name} files'
    body_template: str = 'Synced from [{src_repo_name}]({src_repo_url}) @ `{src_sha_short}`\n\n<details>\n<summary>Sync Log</summary>\n\n```\n{sync_log}\n```\n\n</details>\n'
    body_suffix: str = ''
```

| Field | Type | Default | Since |
|---|---|---|---|
| labels | `list[str]` | `...` | 0.3.0 |
| reviewers | `list[str]` | `...` | 0.3.0 |
| assignees | `list[str]` | `...` | 0.3.0 |
| title | `str` | `'chore: sync {name} files'` | 0.3.0 |
| body_template | `str` | `'Synced from [{src_repo_name}]({src_repo_url}) @ `{src_sha_short}`\n\n<details>\n<summary>Sync Log</summary>\n\n```\n{sync_log}\n```\n\n</details>\n'` | 0.3.0 |
| body_suffix | `str` | `''` | 0.3.0 |

### Changes

| Version | Change |
|---------|--------|
| 0.3.0 | Made public |
<!-- === OK_EDIT: pkg-ext prdefaults_def === -->
<!-- === DO_NOT_EDIT: pkg-ext syncmode_def === -->
<a id="syncmode_def"></a>

### class: `SyncMode`
- [source](../../path_sync/_internal/models.py#L32)
> **Since:** 0.3.0

```python
class SyncMode(StrEnum):
    ...
```

### Changes

| Version | Change |
|---------|--------|
| 0.3.0 | Made public |
<!-- === OK_EDIT: pkg-ext syncmode_def === -->