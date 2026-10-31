"""Typed containers for scan results and resume state."""

from __future__ import annotations

from typing import Any, TypedDict


class HostResult(TypedDict, total=False):
    """One live (or takeover-flagged) host."""

    url: str
    status: int
    title: str
    tech: list[str]
    cname: list[str]
    screenshot: str
    takeover: str
    service: str


class TakeoverInfo(TypedDict):
    """A host whose CNAME points at an unclaimed service."""

    service: str
    cname: str
    verdict: str


# Free-form JSON persisted to runs/<id>/state.json.
ResumeState = dict[str, Any]
