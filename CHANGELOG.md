# Changelog

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
