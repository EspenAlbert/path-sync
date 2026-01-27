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
> **Since:** unreleased

```python
class CommitConfig(BaseModel):
    message: str
    add_paths: list[str] = ...
```

| Field | Type | Default | Since |
|---|---|---|---|
| message | `str` | - | unreleased |
| add_paths | `list[str]` | `...` | unreleased |
<!-- === OK_EDIT: pkg-ext commitconfig_def === -->
<!-- === DO_NOT_EDIT: pkg-ext depconfig_def === -->
<a id="depconfig_def"></a>

### class: `DepConfig`
- [source](../../path_sync/_internal/models_dep.py#L47)
> **Since:** unreleased

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
| name | `str` | - | unreleased |
| from_config | `str` | - | unreleased |
| include_destinations | `list[str]` | `...` | unreleased |
| exclude_destinations | `list[str]` | `...` | unreleased |
| updates | `list[UpdateEntry]` | - | unreleased |
| verify | `VerifyConfig` | `...` | unreleased |
| pr | `PRConfig` | - | unreleased |
<!-- === OK_EDIT: pkg-ext depconfig_def === -->
<!-- === DO_NOT_EDIT: pkg-ext onfailstrategy_def === -->
<a id="onfailstrategy_def"></a>

### class: `OnFailStrategy`
- [source](../../path_sync/_internal/models_dep.py#L13)
> **Since:** unreleased

```python
class OnFailStrategy(StrEnum):
    ...
```
<!-- === OK_EDIT: pkg-ext onfailstrategy_def === -->
<!-- === DO_NOT_EDIT: pkg-ext prconfig_def === -->
<a id="prconfig_def"></a>

### class: `PRConfig`
- [source](../../path_sync/_internal/models_dep.py#L40)
> **Since:** unreleased

```python
class PRConfig(BaseModel):
    branch: str
    title: str
    labels: list[str] = ...
    auto_merge: bool = False
```

| Field | Type | Default | Since |
|---|---|---|---|
| branch | `str` | - | unreleased |
| title | `str` | - | unreleased |
| labels | `list[str]` | `...` | unreleased |
| auto_merge | `bool` | `False` | unreleased |
<!-- === OK_EDIT: pkg-ext prconfig_def === -->
<!-- === DO_NOT_EDIT: pkg-ext updateentry_def === -->
<a id="updateentry_def"></a>

### class: `UpdateEntry`
- [source](../../path_sync/_internal/models_dep.py#L35)
> **Since:** unreleased

```python
class UpdateEntry(BaseModel):
    workdir: str = '.'
    command: str
```

| Field | Type | Default | Since |
|---|---|---|---|
| workdir | `str` | `'.'` | unreleased |
| command | `str` | - | unreleased |
<!-- === OK_EDIT: pkg-ext updateentry_def === -->
<!-- === DO_NOT_EDIT: pkg-ext verifyconfig_def === -->
<a id="verifyconfig_def"></a>

### class: `VerifyConfig`
- [source](../../path_sync/_internal/models_dep.py#L30)
> **Since:** unreleased

```python
class VerifyConfig(BaseModel):
    on_fail: OnFailStrategy = <OnFailStrategy.SKIP: 'skip'>
    steps: list[VerifyStep] = ...
```

| Field | Type | Default | Since |
|---|---|---|---|
| on_fail | `OnFailStrategy` | `<OnFailStrategy.SKIP: 'skip'>` | unreleased |
| steps | `list[VerifyStep]` | `...` | unreleased |
<!-- === OK_EDIT: pkg-ext verifyconfig_def === -->
<!-- === DO_NOT_EDIT: pkg-ext verifystep_def === -->
<a id="verifystep_def"></a>

### class: `VerifyStep`
- [source](../../path_sync/_internal/models_dep.py#L24)
> **Since:** unreleased

```python
class VerifyStep(BaseModel):
    run: str
    commit: CommitConfig | None
    on_fail: OnFailStrategy | None
```

| Field | Type | Default | Since |
|---|---|---|---|
| run | `str` | - | unreleased |
| commit | `CommitConfig | None` | - | unreleased |
| on_fail | `OnFailStrategy | None` | - | unreleased |
<!-- === OK_EDIT: pkg-ext verifystep_def === -->
<!-- === DO_NOT_EDIT: pkg-ext dep_update_def === -->
<a id="dep_update_def"></a>

### cli_command: `dep_update`
- [source](../../path_sync/_internal/cmd_dep_update.py#L66)
> **Since:** unreleased

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