<!-- === DO_NOT_EDIT: pkg-ext header === -->
# dep_update

<!-- === OK_EDIT: pkg-ext header === -->

<!-- === DO_NOT_EDIT: pkg-ext symbols === -->
- [`CommitConfig`](#commitconfig_def)
- [`DepConfig`](#depconfig_def)
- [`OnFailStrategy`](#onfailstrategy_def)
- [`PRConfig`](#prconfig_def)
- [`UpdateEntry`](#updateentry_def)
- [`VerifyConfig`](#verifyconfig_def)
- [`VerifyStep`](#verifystep_def)
- [`dep_update`](#dep_update_def)
<!-- === OK_EDIT: pkg-ext symbols === -->

<!-- === DO_NOT_EDIT: pkg-ext symbol_details_header === -->
## Symbol Details
<!-- === OK_EDIT: pkg-ext symbol_details_header === -->

<!-- === DO_NOT_EDIT: pkg-ext commitconfig_def === -->
<a id="commitconfig_def"></a>

### class: `CommitConfig`
- [source](../../path_sync/_internal/models_dep.py#L19)
> **Since:** 0.4.0

```python
class CommitConfig(BaseModel):
    message: str
    add_paths: list[str] = ...
```

| Field | Type | Default | Since |
|---|---|---|---|
| message | `str` | - | 0.4.0 |
| add_paths | `list[str]` | `...` | 0.4.0 |
<!-- === OK_EDIT: pkg-ext commitconfig_def === -->
<!-- === DO_NOT_EDIT: pkg-ext depconfig_def === -->
<a id="depconfig_def"></a>

### class: `DepConfig`
- [source](../../path_sync/_internal/models_dep.py#L47)
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

| Field | Type | Default | Since |
|---|---|---|---|
| name | `str` | - | 0.4.0 |
| from_config | `str` | - | 0.4.0 |
| include_destinations | `list[str]` | `...` | 0.4.0 |
| exclude_destinations | `list[str]` | `...` | 0.4.0 |
| updates | `list[UpdateEntry]` | - | 0.4.0 |
| verify | `VerifyConfig` | `...` | 0.4.0 |
| pr | `PRConfig` | - | 0.4.0 |
<!-- === OK_EDIT: pkg-ext depconfig_def === -->
<!-- === DO_NOT_EDIT: pkg-ext onfailstrategy_def === -->
<a id="onfailstrategy_def"></a>

### class: `OnFailStrategy`
- [source](../../path_sync/_internal/models_dep.py#L13)
> **Since:** 0.4.0

```python
class OnFailStrategy(StrEnum):
    ...
```
<!-- === OK_EDIT: pkg-ext onfailstrategy_def === -->
<!-- === DO_NOT_EDIT: pkg-ext prconfig_def === -->
<a id="prconfig_def"></a>

### class: `PRConfig`
- [source](../../path_sync/_internal/models_dep.py#L40)
> **Since:** 0.4.0

```python
class PRConfig(BaseModel):
    branch: str
    title: str
    labels: list[str] = ...
    auto_merge: bool = False
```

| Field | Type | Default | Since |
|---|---|---|---|
| branch | `str` | - | 0.4.0 |
| title | `str` | - | 0.4.0 |
| labels | `list[str]` | `...` | 0.4.0 |
| auto_merge | `bool` | `False` | 0.4.0 |
<!-- === OK_EDIT: pkg-ext prconfig_def === -->
<!-- === DO_NOT_EDIT: pkg-ext updateentry_def === -->
<a id="updateentry_def"></a>

### class: `UpdateEntry`
- [source](../../path_sync/_internal/models_dep.py#L35)
> **Since:** 0.4.0

```python
class UpdateEntry(BaseModel):
    workdir: str = '.'
    command: str
```

| Field | Type | Default | Since |
|---|---|---|---|
| workdir | `str` | `'.'` | 0.4.0 |
| command | `str` | - | 0.4.0 |
<!-- === OK_EDIT: pkg-ext updateentry_def === -->
<!-- === DO_NOT_EDIT: pkg-ext verifyconfig_def === -->
<a id="verifyconfig_def"></a>

### class: `VerifyConfig`
- [source](../../path_sync/_internal/models_dep.py#L30)
> **Since:** 0.4.0

```python
class VerifyConfig(BaseModel):
    on_fail: OnFailStrategy = <OnFailStrategy.SKIP: 'skip'>
    steps: list[VerifyStep] = ...
```

| Field | Type | Default | Since |
|---|---|---|---|
| on_fail | `OnFailStrategy` | `<OnFailStrategy.SKIP: 'skip'>` | 0.4.0 |
| steps | `list[VerifyStep]` | `...` | 0.4.0 |
<!-- === OK_EDIT: pkg-ext verifyconfig_def === -->
<!-- === DO_NOT_EDIT: pkg-ext verifystep_def === -->
<a id="verifystep_def"></a>

### class: `VerifyStep`
- [source](../../path_sync/_internal/models_dep.py#L24)
> **Since:** 0.4.0

```python
class VerifyStep(BaseModel):
    run: str
    commit: CommitConfig | None
    on_fail: OnFailStrategy | None
```

| Field | Type | Default | Since |
|---|---|---|---|
| run | `str` | - | 0.4.0 |
| commit | `CommitConfig | None` | - | 0.4.0 |
| on_fail | `OnFailStrategy | None` | - | 0.4.0 |
<!-- === OK_EDIT: pkg-ext verifystep_def === -->
<!-- === DO_NOT_EDIT: pkg-ext dep_update_def === -->
<a id="dep_update_def"></a>

### cli_command: `dep_update`
- [source](../../path_sync/_internal/cmd_dep_update.py#L66)
> **Since:** 0.4.0

```python
def dep_update(*, name: str = ..., dest_filter: str = '', work_dir: str = '', dry_run: bool = False, skip_verify: bool = False, src_root_opt: str = '') -> None:
    ...
```

Run dependency updates across repositories.

**CLI Options:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `-n`, `--name` | `str` | *required* | Config name |
| `-d`, `--dest` | `str` | `''` | Filter destinations (comma-separated) |
| `--work-dir` | `str` | `''` | Directory for cloning repos |
| `--dry-run` | `bool` | `False` | Preview without creating PRs |
| `--skip-verify` | `bool` | `False` | Skip verification steps |
| `--src-root` | `str` | `''` | Source repo root |
<!-- === OK_EDIT: pkg-ext dep_update_def === -->