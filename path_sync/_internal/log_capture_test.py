from __future__ import annotations

import logging

from path_sync._internal.log_capture import capture_log


def test_capture_log_captures_logger_output():
    test_logger = logging.getLogger("path_sync.test")

    with capture_log("test") as read_log:
        test_logger.info("first message")
        test_logger.info("second message")
        content = read_log()

    assert "first message" in content
    assert "second message" in content


def test_capture_log_read_after_flush_includes_all():
    test_logger = logging.getLogger("path_sync.test2")

    with capture_log("test2") as read_log:
        test_logger.info("before flush")
        content1 = read_log()
        test_logger.info("after first read")
        content2 = read_log()

    assert "before flush" in content1
    assert "before flush" in content2
    assert "after first read" in content2
