"""Shared prompt utilities for interactive CLI commands."""

from __future__ import annotations

import sys


def prompt_confirm(message: str, no_prompt: bool = False) -> bool:
    """Prompt user for confirmation.

    Args:
        message: The prompt message to display
        no_prompt: If True, auto-confirms without prompting

    Returns:
        True if confirmed, False otherwise.
        Auto-confirms in non-interactive mode (CI) or when no_prompt=True.
    """
    if no_prompt or not sys.stdin.isatty():
        return True
    try:
        response = input(f"{message} [y/n]: ").strip().lower()
        return response == "y"
    except (EOFError, KeyboardInterrupt):
        return False
