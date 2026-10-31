"""External tool discovery."""

from __future__ import annotations

import shutil

from .constants import TOOL_PATHS


def tool_path(name: str) -> str | None:
    """Return an absolute path to *name*, or fall back to a PATH lookup."""
    configured = TOOL_PATHS.get(name)
    if configured:
        import os

        if os.path.isfile(configured):
            return configured
    return shutil.which(name)


def missing_tools(names: tuple[str, ...] = ("subfinder", "httpx", "dnsx")) -> list[str]:
    return [name for name in names if not tool_path(name)]
