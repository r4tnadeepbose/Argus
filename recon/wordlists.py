"""Prefix wordlists used by the brute-force stage."""

from __future__ import annotations

from pathlib import Path

DEFAULT_WORDLIST: tuple[str, ...] = (
    "www", "api", "dev", "staging", "stage", "test", "uat", "qa", "prod",
    "admin", "portal", "app", "apps", "beta", "alpha", "demo", "sandbox",
    "internal", "intranet", "vpn", "mail", "smtp", "webmail", "cdn",
    "static", "assets", "img", "images", "media", "auth", "sso", "login",
    "account", "accounts", "oauth", "db", "database", "cache", "queue",
    "monitor", "metrics", "grafana", "kibana", "logs", "ci", "cd",
    "jenkins", "gitlab", "git", "build", "deploy", "docs", "wiki", "help",
    "support", "status", "health", "m", "mobile", "old", "new",
    "v1", "v2", "v3",
)


def load_wordlist(path: str | None) -> tuple[list[str], str]:
    """Load prefixes from *path*.

    Returns ``(words, source)`` where *source* is a human-readable description.
    Falls back to :data:`DEFAULT_WORDLIST` when the path is empty, missing or
    contains no usable entries.
    """
    if not path:
        return list(DEFAULT_WORDLIST), f"built-in ({len(DEFAULT_WORDLIST)} prefixes)"

    p = Path(path)
    if not p.is_file():
        return list(DEFAULT_WORDLIST), f"built-in ({len(DEFAULT_WORDLIST)} prefixes)"

    words: list[str] = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            words.append(line)
    if not words:
        return list(DEFAULT_WORDLIST), f"built-in ({len(DEFAULT_WORDLIST)} prefixes)"
    return words, f"{p} ({len(words)} prefixes)"
