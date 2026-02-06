from pathlib import Path

import pytest

from path_sync import sections

JUSTFILE = Path("justfile")

JUSTFILE_CONTENT = """\
# path-sync copy -n python-template

# === OK_EDIT: path-sync header ===
# Custom variables

# === DO_NOT_EDIT: path-sync standard ===
pre-push: lint test
# === OK_EDIT: path-sync standard ===

# === DO_NOT_EDIT: path-sync coverage ===
cov:
  uv run pytest --cov
# === OK_EDIT: path-sync coverage ===
"""


def test_parse_sections():
    result = sections.parse_sections(JUSTFILE_CONTENT, JUSTFILE)
    assert len(result) == 2
    assert result[0].id == "standard"
    assert result[0].content == "pre-push: lint test"
    assert result[1].id == "coverage"
    assert "uv run pytest --cov" in result[1].content


def test_parse_sections_no_markers():
    assert not sections.parse_sections("just plain content\nno markers", JUSTFILE)


def test_parse_sections_nested_error():
    content = """\
# === DO_NOT_EDIT: path-sync outer ===
# === DO_NOT_EDIT: path-sync inner ===
# === OK_EDIT: path-sync inner ===
# === OK_EDIT: path-sync outer ===
"""
    with pytest.raises(ValueError, match="Nested section"):
        sections.parse_sections(content, JUSTFILE)


def test_parse_sections_unclosed_error():
    content = "# === DO_NOT_EDIT: path-sync test ===\nsome content"
    with pytest.raises(ValueError, match="Unclosed section"):
        sections.parse_sections(content, JUSTFILE)


def test_parse_sections_standalone_ok_edit():
    content = "# === OK_EDIT: path-sync header ===\nsome content\n# === OK_EDIT: path-sync footer ==="
    assert not sections.parse_sections(content, JUSTFILE)


def test_has_sections():
    assert sections.has_sections(JUSTFILE_CONTENT, JUSTFILE)
    assert not sections.has_sections("plain content", JUSTFILE)


def test_wrap_in_default_section():
    result = sections.wrap_in_default_section("content here", JUSTFILE)
    assert "DO_NOT_EDIT: path-sync default" in result
    assert "content here" in result
    assert result.endswith("# === OK_EDIT: path-sync default ===")


def test_parse_sections_content():
    result = sections.parse_sections(JUSTFILE_CONTENT, JUSTFILE)
    result_dict = {s.id: s.content for s in result}
    assert result_dict == {
        "standard": "pre-push: lint test",
        "coverage": "cov:\n  uv run pytest --cov",
    }


def test_replace_sections_updates_content():
    dest = """\
# === DO_NOT_EDIT: path-sync standard ===
old content
# === OK_EDIT: path-sync standard ==="""
    src = [
        sections.Section(id="standard", parts=[sections.SectionPart(content="new content", start_line=1, end_line=1)])
    ]
    result = sections.replace_sections(dest, src, JUSTFILE)
    assert "new content" in result
    assert "old content" not in result


def test_replace_sections_preserves_ok_edit():
    dest = """\
# custom header
# === DO_NOT_EDIT: path-sync standard ===
old
# === OK_EDIT: path-sync standard ===
# my custom stuff"""
    src = [sections.Section(id="standard", parts=[sections.SectionPart(content="new", start_line=1, end_line=1)])]
    result = sections.replace_sections(dest, src, JUSTFILE)
    assert "# custom header" in result
    assert "# my custom stuff" in result


def test_replace_sections_skip():
    dest = """\
# === DO_NOT_EDIT: path-sync standard ===
keep this
# === OK_EDIT: path-sync standard ==="""
    src = [sections.Section(id="standard", parts=[sections.SectionPart(content="replaced", start_line=1, end_line=1)])]
    result = sections.replace_sections(dest, src, JUSTFILE, skip_sections=["standard"])
    assert "keep this" in result
    assert "replaced" not in result


def test_replace_sections_adds_new():
    dest = "# plain file"
    src = [sections.Section(id="newid", parts=[sections.SectionPart(content="new content", start_line=1, end_line=1)])]
    result = sections.replace_sections(dest, src, JUSTFILE)
    assert "DO_NOT_EDIT: path-sync newid" in result
    assert "new content" in result


def test_replace_sections_keeps_dest_only():
    dest = """\
# === DO_NOT_EDIT: path-sync custom ===
my custom section
# === OK_EDIT: path-sync custom ==="""
    result = sections.replace_sections(dest, {}, JUSTFILE, keep_deleted_sections=True)
    assert "my custom section" in result
    assert "DO_NOT_EDIT: path-sync custom" in result


def test_markdown_sections():
    md_path = Path("test.md")
    content = """\
<!-- === DO_NOT_EDIT: path-sync heading === -->
# Title
<!-- === OK_EDIT: path-sync heading === -->
"""
    assert sections.has_sections(content, md_path)
    result = sections.parse_sections(content, md_path)
    assert result[0].id == "heading"
    assert result[0].content == "# Title"

    new_content = sections.replace_sections(
        content,
        [sections.Section(id="heading", parts=[sections.SectionPart(content="# New Title", start_line=1, end_line=1)])],
        md_path,
    )
    assert "# New Title" in new_content


RESUMABLE_SECTION_CONTENT = """\
# === DO_NOT_EDIT: path-sync job-snapshot ===
plan-snapshot-tests:
  runs-on: ubuntu-latest
# === OK_EDIT: path-sync job-snapshot ===
  env:
    # User-managed credentials
    API_KEY: ${{ secrets.API_KEY }}
# === DO_NOT_EDIT: path-sync job-snapshot ===
  steps:
    - uses: actions/checkout@v4
# === OK_EDIT: path-sync job-snapshot ===
"""


def test_parse_resumable_section():
    """Parse a section with OK_EDIT in the middle (pause/resume pattern)."""
    result = sections.parse_sections(RESUMABLE_SECTION_CONTENT, JUSTFILE)
    assert len(result) == 1
    section = result[0]
    assert section.id == "job-snapshot"
    # Section should have 2 parts (before and after the gap)
    assert len(section.parts) == 2
    # First part: job header
    assert "runs-on: ubuntu-latest" in section.parts[0].content
    # Second part: steps
    assert "actions/checkout" in section.parts[1].content
    # Gap content (env) should NOT be in the section content
    assert "API_KEY" not in section.content
    # Gap content is in the first part's content_after
    assert section.parts[0].content_after is not None
    assert "API_KEY" in section.parts[0].content_after


def test_replace_resumable_section_preserves_user_content():
    """Replace sections should preserve user content between resumable parts."""
    src_sections = {
        "job-snapshot": sections.parse_sections(RESUMABLE_SECTION_CONTENT, JUSTFILE),
    }
    # Destination with user-modified gap content
    dest = """\
# === DO_NOT_EDIT: path-sync job-snapshot ===
plan-snapshot-tests:
  runs-on: ubuntu-latest
# === OK_EDIT: path-sync job-snapshot ===
  env:
    # User added more secrets
    API_KEY: ${{ secrets.API_KEY }}
    DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
# === DO_NOT_EDIT: path-sync job-snapshot ===
  steps:
    - uses: actions/checkout@v4
# === OK_EDIT: path-sync job-snapshot ===
"""
    result = sections.replace_sections(dest, src_sections["job-snapshot"], JUSTFILE)
    # User's additional secret should be preserved
    assert "DB_PASSWORD" in result
    # Managed content should still be present
    assert "runs-on: ubuntu-latest" in result
    assert "actions/checkout" in result
