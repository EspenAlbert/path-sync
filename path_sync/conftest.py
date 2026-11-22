import io
import subprocess
import sys

import pytest
from git import Repo


@pytest.fixture
def tmp_repo(tmp_path):
    """Create a temporary git repo."""

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    repo = Repo.init(repo_path)
    (repo_path / ".gitkeep").write_text("")
    repo.index.add([".gitkeep"])
    repo.index.commit("Initial commit")
    return repo_path


@pytest.fixture
def locale_cp1252(monkeypatch):
    """Make an omitted `encoding` mean cp1252, as on Windows with Python < 3.15.

    `io.text_encoding` serves `open`, `pathlib` and `logging`; `subprocess._text_encoding` serves `subprocess`.
    """

    def text_encoding(encoding=None, stacklevel=2):
        return encoding or "cp1252"

    monkeypatch.setattr(io, "text_encoding", text_encoding)
    monkeypatch.setattr(subprocess, "_text_encoding", text_encoding)


@pytest.fixture
def commands_print_utf8(request, monkeypatch):
    """Make every `subprocess.run` command print "Ángel ✓" as UTF-8 to stdout and stderr.

    The command exits with `request.param` (default 0).
    """
    returncode = getattr(request, "param", 0)
    run = subprocess.run
    script = (
        "import sys; text = sys.argv[1].encode(); "
        "sys.stdout.buffer.write(text); sys.stderr.buffer.write(text); sys.exit(int(sys.argv[2]))"
    )

    def run_printing_utf8(cmd, **kwargs):
        return run([sys.executable, "-c", script, "Ángel ✓", str(returncode)], **kwargs)

    monkeypatch.setattr(subprocess, "run", run_printing_utf8)
