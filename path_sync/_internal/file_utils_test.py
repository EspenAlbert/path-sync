from __future__ import annotations

from path_sync._internal.file_utils import ensure_parents_write_text


def test_ensure_parents_write_text_writes_lf(tmp_path):
    path = tmp_path / "sub" / "file.txt"
    ensure_parents_write_text(path, "one\ntwo\n")
    assert path.read_bytes() == b"one\ntwo\n"
