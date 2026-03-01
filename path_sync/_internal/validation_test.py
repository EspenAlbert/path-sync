from __future__ import annotations

import pytest

from path_sync._internal.validation import parse_skip_sections


def test_parse_skip_sections_empty_string_returns_empty():
    assert parse_skip_sections("") == {}


def test_parse_skip_sections_single_entry():
    assert parse_skip_sections("justfile:coverage") == {"justfile": {"coverage"}}


def test_parse_skip_sections_multiple_entries_same_path():
    result = parse_skip_sections("justfile:coverage,justfile:default")
    assert result == {"justfile": {"coverage", "default"}}


def test_parse_skip_sections_multiple_paths():
    result = parse_skip_sections("justfile:coverage,pyproject.toml:default")
    assert result == {"justfile": {"coverage"}, "pyproject.toml": {"default"}}


def test_parse_skip_sections_strips_whitespace():
    assert parse_skip_sections("  a:b  ,  c:d  ") == {"a": {"b"}, "c": {"d"}}


def test_parse_skip_sections_rsplit_uses_last_colon():
    assert parse_skip_sections("path:to:section_id") == {"path:to": {"section_id"}}


def test_parse_skip_sections_invalid_format_raises():
    with pytest.raises(ValueError, match="Invalid format 'no_colon'"):
        parse_skip_sections("no_colon")
