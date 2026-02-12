import pytest

from path_sync._internal.models import Destination, PathMapping, SrcConfig


def _dest(name: str, include_groups: list[str] | None = None) -> Destination:
    return Destination(
        name=name,
        dest_path_relative=f"code/{name}",
        include_groups=include_groups or [],
    )


def _config(
    path_groups: dict[str, list[PathMapping]] | None = None,
    destinations: list[Destination] | None = None,
) -> SrcConfig:
    return SrcConfig(
        name="test",
        paths=[PathMapping(src_path="shared.txt")],
        path_groups=path_groups or {},
        destinations=destinations or [],
    )


def test_resolve_paths_no_groups():
    config = _config()
    dest = _dest("a")
    assert config.resolve_paths(dest) is config.paths


def test_resolve_paths_with_groups():
    region_paths = [PathMapping(src_path="regions/dev.txt"), PathMapping(src_path="regions/prod.txt")]
    config = _config(
        path_groups={"regions": region_paths},
        destinations=[_dest("a", include_groups=["regions"]), _dest("b")],
    )
    a_paths = config.resolve_paths(config.destinations[0])
    assert len(a_paths) == 3
    assert a_paths[0].src_path == "shared.txt"
    assert a_paths[1].src_path == "regions/dev.txt"

    b_paths = config.resolve_paths(config.destinations[1])
    assert b_paths is config.paths


def test_resolve_paths_multiple_groups():
    region_paths = [PathMapping(src_path="regions/dev.txt")]
    extra_paths = [PathMapping(src_path="extras/lint.cfg")]
    config = _config(
        path_groups={"regions": region_paths, "extras": extra_paths},
        destinations=[_dest("a", include_groups=["regions", "extras"])],
    )
    paths = config.resolve_paths(config.destinations[0])
    assert len(paths) == 3
    assert [p.src_path for p in paths] == ["shared.txt", "regions/dev.txt", "extras/lint.cfg"]


def test_validation_rejects_unknown_group():
    with pytest.raises(ValueError, match="unknown path_group 'missing'"):
        _config(destinations=[_dest("a", include_groups=["missing"])])


def test_validation_rejects_duplicate_group():
    with pytest.raises(ValueError, match="duplicate include_group 'regions'"):
        _config(
            path_groups={"regions": [PathMapping(src_path="r.txt")]},
            destinations=[_dest("a", include_groups=["regions", "regions"])],
        )
