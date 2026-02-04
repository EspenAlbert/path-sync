from __future__ import annotations

import logging
import tempfile
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path

LOG_FORMAT = "%(message)s"


@contextmanager
def capture_log(name: str) -> Generator[Callable[[], str]]:
    """Capture path_sync logger output to a temp file.

    Args:
        name: Used for temp file naming (e.g., repo name for debugging).

    Yields:
        Callable that flushes the handler and returns log content.
    """
    with tempfile.TemporaryDirectory(prefix="path-sync-") as tmpdir:
        log_path = Path(tmpdir) / f"{name}.log"
        file_handler = logging.FileHandler(log_path, mode="w")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root_logger = logging.getLogger("path_sync")
        root_logger.addHandler(file_handler)
        try:

            def read_log() -> str:
                file_handler.flush()
                return log_path.read_text() if log_path.exists() else ""

            yield read_log
        finally:
            file_handler.close()
            root_logger.removeHandler(file_handler)
