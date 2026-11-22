from __future__ import annotations

import logging
import sys

from path_sync._internal.verify import run_command


def test_run_command_logs_utf8_output(tmp_path, caplog, locale_cp1252):
    caplog.set_level(logging.INFO)
    run_command(
        f'"{sys.executable}" -c "import sys; sys.stdout.buffer.write((chr(193) + chr(10003)).encode())"', tmp_path
    )
    assert "Á✓" in caplog.text


def test_run_command_replaces_undecodable_output(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    run_command(f'"{sys.executable}" -c "import sys; sys.stdout.buffer.write(bytes([255]))"', tmp_path)
    assert "\ufffd" in caplog.text
