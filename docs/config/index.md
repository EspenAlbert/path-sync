<!-- === DO_NOT_EDIT: pkg-ext header === -->
# config

<!-- === OK_EDIT: pkg-ext header === -->

<!-- === DO_NOT_EDIT: pkg-ext symbols === -->
- [`Destination`](#destination_def)
- [`HeaderConfig`](#headerconfig_def)
- [`PRDefaults`](#prdefaults_def)
- [`PathMapping`](#pathmapping_def)
- [`SrcConfig`](#srcconfig_def)
- [`SyncMode`](#syncmode_def)
<!-- === OK_EDIT: pkg-ext symbols === -->

<!-- === DO_NOT_EDIT: pkg-ext symbol_details_header === -->
## Symbol Details
<!-- === OK_EDIT: pkg-ext symbol_details_header === -->

<!-- === DO_NOT_EDIT: pkg-ext destination_def === -->
<a id="destination_def"></a>

### class: `Destination`
- [source](../../path_sync/_internal/models.py#L117)
> **Since:** 0.3.0

```python
class Destination(BaseModel):
    name: str = PydanticUndefined
    repo_url: str = ''
    dest_path_relative: str = PydanticUndefined
    copy_branch: str = ''
    default_branch: str = 'main'
    skip_sections: dict[str, list[str]] = ...
    skip_file_patterns: set[str] = ...
```

| Field | Type | Default | Since |
|---|---|---|---|
| name | `str` | `PydanticUndefined` | 0.3.0 |
| repo_url | `str` | `''` | 0.3.0 |
| dest_path_relative | `str` | `PydanticUndefined` | 0.3.0 |
| copy_branch | `str` | `''` | 0.3.0 |
| default_branch | `str` | `'main'` | 0.3.0 |
| skip_sections | `dict[str, list[str]]` | `...` | 0.3.0 |
| skip_file_patterns | `set[str]` | `...` | 0.3.0 |
<!-- === OK_EDIT: pkg-ext destination_def === -->
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
<!-- === OK_EDIT: pkg-ext headerconfig_def === -->
<!-- === DO_NOT_EDIT: pkg-ext prdefaults_def === -->
<a id="prdefaults_def"></a>

### class: `PRDefaults`
- [source](../../path_sync/_internal/models.py#L88)
> **Since:** 0.3.0

```python
class PRDefaults(BaseModel):
    title: str = 'chore: sync {name} files'
    body_template: str = 'Synced from [{src_repo_name}]({src_repo_url}) @ `{src_sha_short}`\n\n<details>\n<summary>Sync Log</summary>\n\n```\n{sync_log}\n```\n\n</details>\n'
    body_suffix: str = ''
    labels: list[str] = ...
    reviewers: list[str] = ...
    assignees: list[str] = ...
```

| Field | Type | Default | Since |
|---|---|---|---|
| title | `str` | `'chore: sync {name} files'` | 0.3.0 |
| body_template | `str` | `'Synced from [{src_repo_name}]({src_repo_url}) @ `{src_sha_short}`\n\n<details>\n<summary>Sync Log</summary>\n\n```\n{sync_log}\n```\n\n</details>\n'` | 0.3.0 |
| body_suffix | `str` | `''` | 0.3.0 |
| labels | `list[str]` | `...` | 0.3.0 |
| reviewers | `list[str]` | `...` | 0.3.0 |
| assignees | `list[str]` | `...` | 0.3.0 |
<!-- === OK_EDIT: pkg-ext prdefaults_def === -->
<!-- === DO_NOT_EDIT: pkg-ext pathmapping_def === -->
<a id="pathmapping_def"></a>

### class: `PathMapping`
- [source](../../path_sync/_internal/models.py#L38)
> **Since:** 0.3.0

```python
class PathMapping(BaseModel):
    src_path: str = PydanticUndefined
    dest_path: str = ''
    sync_mode: SyncMode = <SyncMode.SYNC: 'sync'>
    exclude_dirs: set[str] = ...
    exclude_file_patterns: set[str] = ...
```

| Field | Type | Default | Since |
|---|---|---|---|
| src_path | `str` | `PydanticUndefined` | 0.3.0 |
| dest_path | `str` | `''` | 0.3.0 |
| sync_mode | `SyncMode` | `<SyncMode.SYNC: 'sync'>` | 0.3.0 |
| exclude_dirs | `set[str]` | `...` | 0.3.0 |
| exclude_file_patterns | `set[str]` | `...` | 0.3.0 |
<!-- === OK_EDIT: pkg-ext pathmapping_def === -->
<!-- === DO_NOT_EDIT: pkg-ext srcconfig_def === -->
<a id="srcconfig_def"></a>

### class: `SrcConfig`
- [source](../../path_sync/_internal/models.py#L133)
> **Since:** 0.3.0

```python
class SrcConfig(BaseModel):
    name: str = PydanticUndefined
    git_remote: str = 'origin'
    src_repo_url: str = ''
    schedule: str = '0 6 * * *'
    header_config: HeaderConfig = ...
    pr_defaults: PRDefaults = ...
    paths: list[PathMapping] = ...
    destinations: list[Destination] = ...
```

| Field | Type | Default | Since |
|---|---|---|---|
| name | `str` | `PydanticUndefined` | 0.3.0 |
| git_remote | `str` | `'origin'` | 0.3.0 |
| src_repo_url | `str` | `''` | 0.3.0 |
| schedule | `str` | `'0 6 * * *'` | 0.3.0 |
| header_config | `HeaderConfig` | `...` | 0.3.0 |
| pr_defaults | `PRDefaults` | `...` | 0.3.0 |
| paths | `list[PathMapping]` | `...` | 0.3.0 |
| destinations | `list[Destination]` | `...` | 0.3.0 |
<!-- === OK_EDIT: pkg-ext srcconfig_def === -->
<!-- === DO_NOT_EDIT: pkg-ext syncmode_def === -->
<a id="syncmode_def"></a>

### class: `SyncMode`
- [source](../../path_sync/_internal/models.py#L32)
> **Since:** 0.3.0

```python
class SyncMode(StrEnum):
    ...
```
<!-- === OK_EDIT: pkg-ext syncmode_def === -->