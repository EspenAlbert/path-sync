import io

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
    """Make an omitted `encoding` mean cp1252, as on Windows with Python < 3.15."""

    def text_encoding(encoding, stacklevel=2):
        return encoding or "cp1252"

    monkeypatch.setattr(io, "text_encoding", text_encoding)
