from __future__ import annotations

from path_sync._internal.models import Destination
from path_sync._internal.yaml_utils import load_yaml_model


def test_load_yaml_model_utf8_content(tmp_path, locale_cp1252):
    path = tmp_path / "dest.yaml"
    path.write_text("name: café\ndest_path_relative: ../Ángel ✓\n", encoding="utf-8")
    dest = load_yaml_model(path, Destination)
    assert dest.name == "café"
    assert dest.dest_path_relative == "../Ángel ✓"
