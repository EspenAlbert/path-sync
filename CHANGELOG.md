# Changelog

## 0.7.3 2026-02-13T07-25Z

### __Root__
- fix(copy): skip entire sync when open PR is already from newer source [7a0d75](https://github.com/EspenAlbert/path-sync/commit/7a0d75)

### Config
- `config.PRDefaults`: field 'body_template' default: 'Synced from [{src_repo_name}]({src_repo_url}) @ `{src_sha_short}`\n\n<details>\n<summary>Sync Log</summary>\n\n```\n{sync_log}\n```\n\n</details>\n' -> '<!-- path-sync: sha={src_sha_short} ts={src_commit_ts} -->\nSynced from [{src_repo_name}]({src_repo_url}) @ `{src_sha_short}` ({src_commit_ts})\n\n<details>\n<summary>Sync Log</summary>\n\n```\n{sync_log}\n```\n\n</details>\n'
- `config.SrcConfig`: added optional field 'force_resync' (default: False)
- `config.SrcConfig`: added optional field 'keep_pr_on_no_changes' (default: False)

### Dep_Update
- `dep_update.DepConfig`: added optional field 'keep_pr_on_no_changes' (default: False)


## 0.7.2 2026-02-12T19-28Z

### Config
- `config.SrcConfig`: added optional field 'path_groups' (default: ...)
- `config.Destination`: added optional field 'include_groups' (default: ...)


## 0.7.1 2026-02-12T18-21Z

### Copy
- fix(cmd_copy): add warning for unknown comment prefix in sync process [01bca8](https://github.com/EspenAlbert/path-sync/commit/01bca8)


## 0.7.0 2026-02-11T08-22Z

### Config
- New class `MergeMethod`
- New class `AutoMergeConfig`
- `config.SrcConfig`: added optional field 'auto_merge' (default: None)

### Copy
- `copy.CopyOptions`: added optional field 'no_wait' (default: False)
- `copy.CopyOptions`: added optional field 'no_auto_merge' (default: False)

### Dep_Update
- BREAKING `dep_update.PRConfig`: removed field 'auto_merge'
- `dep_update.DepConfig`: added optional field 'auto_merge' (default: None)


## 0.6.2 2026-02-10T15-29Z

### Other Changes
- Chore: updated dependencies to supported indented markers


## 0.6.1 2026-02-09T09-09Z

### __Root__
- fix: ignore submodule dirty state and reduce token scope for PR updates [007dcf](https://github.com/EspenAlbert/path-sync/commit/007dcf)


## 0.6.0 2026-02-06T11-00Z

### Config
- `config.Destination`: added optional field 'verify' (default: None)
- `config.SrcConfig`: added optional field 'verify' (default: None)
- `config.SrcConfig`: added optional field 'wrap_synced_files' (default: False)
- `config.PathMapping`: added optional field 'wrap' (default: None)

### Copy
- BREAKING `copy.CopyOptions`: removed field 'local'
- `copy.CopyOptions`: added optional field 'skip_verify' (default: False)
- fix(copy): apply skip_sections when creating new files with sections [15a9e3](https://github.com/EspenAlbert/path-sync/commit/15a9e3)
- `copy.CopyOptions`: added optional field 'skip_commit' (default: False)

### Dep_Update
- `dep_update.VerifyConfig`: field 'on_fail' default: <OnFailStrategy.SKIP: 'skip'> -> <OnFailStrategy.WARN: 'warn'>


## 0.5.0 2026-02-04T09-49Z

### Config
- `config.PRDefaults`: added base class 'PRFieldsBase'

### Copy
- BREAKING `copy.CopyOptions`: removed field 'pr_reviewers'
- BREAKING `copy.CopyOptions`: removed field 'pr_assignees'
- BREAKING `copy.CopyOptions`: removed field 'pr_labels'
- New function `copy`
- `copy.CopyOptions`: added optional field 'assignees' (default: None)
- `copy.CopyOptions`: added optional field 'labels' (default: None)
- `copy.CopyOptions`: added optional field 'reviewers' (default: None)

### Dep_Update
- `dep_update.PRConfig`: added optional field 'reviewers' (default: ...)
- `dep_update.PRConfig`: added optional field 'assignees' (default: ...)
- `dep_update.PRConfig`: added base class 'PRFieldsBase'
- fix(dep-update): handle corrupted git repos and reset existing repos to default branch [6be625](https://github.com/EspenAlbert/path-sync/commit/6be625)

### Validate_No_Changes
- New function `validate_no_changes`


## 0.4.1 2026-02-04T09-44Z

### Config
- `config.SyncMode`: added base class 'StrEnum'
- `config.SrcConfig`: added base class 'BaseModel'
- `config.HeaderConfig`: added base class 'BaseModel'
- `config.PathMapping`: added base class 'BaseModel'
- `config.PRDefaults`: added base class 'BaseModel'
- `config.Destination`: added base class 'BaseModel'

### Copy
- `copy.CopyOptions`: added base class 'BaseModel'

### Dep_Update
- `dep_update.DepConfig`: added base class 'BaseModel'
- `dep_update.UpdateEntry`: added base class 'BaseModel'
- `dep_update.CommitConfig`: added base class 'BaseModel'
- `dep_update.VerifyStep`: added base class 'BaseModel'
- `dep_update.VerifyStep`: field 'commit' default added: None
- `dep_update.VerifyStep`: field 'on_fail' default added: None
- `dep_update.OnFailStrategy`: added base class 'StrEnum'
- `dep_update.VerifyConfig`: added base class 'BaseModel'
- `dep_update.PRConfig`: added base class 'BaseModel'


## 0.4.0 2026-01-27T07-56Z

### Config
- BREAKING `config.PathMapping`: field 'src_path' default removed (was: PydanticUndefined)
- BREAKING `config.SrcConfig`: field 'name' default removed (was: PydanticUndefined)
- BREAKING `config.Destination`: field 'dest_path_relative' default removed (was: PydanticUndefined)
- BREAKING `config.Destination`: field 'name' default removed (was: PydanticUndefined)

### Dep_Update
- New function `dep_update`
- New class `OnFailStrategy`
- New class `CommitConfig`
- New class `VerifyStep`
- New class `VerifyConfig`
- New class `UpdateEntry`
- New class `PRConfig`
- New class `DepConfig`


## 0.3.5 2026-01-24T19-46Z

### Copy
- fix: --no-checkout was checked before --dry-run, so the dry-run flag was ignored when both were passed. [0401d1](https://github.com/EspenAlbert/path-sync/commit/0401d1)


## 0.3.4 2026-01-18T18-29Z

### Config
- fix: Adds support for skipping files per destination in path sync [4025a8](https://github.com/EspenAlbert/path-sync/commit/4025a8)


## 0.3.3 2026-01-15T05-37Z

### Config
- fix: allows exclude_file_patterns [2b56e6](https://github.com/EspenAlbert/path-sync/commit/2b56e6)


## 0.3.2 2026-01-14T14-55Z

### Copy
- fix: handle binary file copying and improve error handling for text reading [082f15](https://github.com/EspenAlbert/path-sync/commit/082f15)


## 0.3.1 2026-01-14T13-40Z

### __Root__
- fix: updates sdist include pattern and add py.typed file [128df2](https://github.com/EspenAlbert/path-sync/commit/128df2)


## 0.3.0 2026-01-14T08-41Z

### Config
- New class SyncMode
- New class PathMapping
- New class HeaderConfig
- New class PRDefaults
- New class Destination
- New class SrcConfig

### Copy
- New class CopyOptions
