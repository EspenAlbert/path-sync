# PRDefaults

<!-- === DO_NOT_EDIT: pkg-ext prdefaults_def === -->
## class: PRDefaults
- [source](../../path_sync/_internal/models.py#L122)
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
<!-- === OK_EDIT: pkg-ext prdefaults_def === -->

### Fields

| Field | Type | Default | Since |
|---|---|---|---|
| labels | `list[str]` | `...` | 0.3.0 |
| reviewers | `list[str]` | `...` | 0.3.0 |
| assignees | `list[str]` | `...` | 0.3.0 |
| title | `str` | `'chore: sync {name} files'` | 0.3.0 |
| body_template | `str` | `'Synced from [{src_repo_name}]({src_repo_url}) @ `{src_sha_short}`\n\n<details>\n<summary>Sync Log</summary>\n\n```\n{sync_log}\n```\n\n</details>\n'` | 0.3.0 |
| body_suffix | `str` | `''` | 0.3.0 |

<!-- === DO_NOT_EDIT: pkg-ext prdefaults_changes === -->
### Changes

| Version | Change |
|---------|--------|
| 0.4.1 | added base class 'BaseModel' |
| 0.4.1 | added base class 'PRFieldsBase' |
| 0.3.0 | Made public |
<!-- === OK_EDIT: pkg-ext prdefaults_changes === -->