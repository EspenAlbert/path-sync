# PRConfig

<!-- === DO_NOT_EDIT: pkg-ext prconfig_def === -->
## class: PRConfig
- [source](../../path_sync/_internal/models_dep.py#L40)
> **Since:** 0.4.0

```python
class PRConfig(PRFieldsBase):
    labels: list[str] = ...
    reviewers: list[str] = ...
    assignees: list[str] = ...
    branch: str
    title: str
    auto_merge: bool = False
```
<!-- === OK_EDIT: pkg-ext prconfig_def === -->

### Fields

| Field | Type | Default | Since |
|---|---|---|---|
| labels | `list[str]` | `...` | 0.4.0 |
| reviewers | `list[str]` | `...` | unreleased |
| assignees | `list[str]` | `...` | unreleased |
| branch | `str` | - | 0.4.0 |
| title | `str` | - | 0.4.0 |
| auto_merge | `bool` | `False` | 0.4.0 |

<!-- === DO_NOT_EDIT: pkg-ext prconfig_changes === -->
### Changes

| Version | Change |
|---------|--------|
| unreleased | added optional field 'reviewers' (default: ...) |
| unreleased | added optional field 'assignees' (default: ...) |
| unreleased | added base class 'PRFieldsBase' |
| 0.4.0 | Made public |
<!-- === OK_EDIT: pkg-ext prconfig_changes === -->