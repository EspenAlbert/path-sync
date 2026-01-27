"""Shared CLI options for commands."""

from __future__ import annotations

import typer


def pr_reviewers_option() -> str:
    return typer.Option("", "--pr-reviewers", help="Comma-separated PR reviewers")


def pr_assignees_option() -> str:
    return typer.Option("", "--pr-assignees", help="Comma-separated PR assignees")


def pr_labels_option() -> str:
    return typer.Option("", "--pr-labels", help="Comma-separated PR labels")


def split_csv(value: str) -> list[str] | None:
    """Split comma-separated string, returns None if empty."""
    return value.split(",") if value else None
