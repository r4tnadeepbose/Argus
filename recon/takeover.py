"""Dangling-CNAME subdomain takeover detection."""

from __future__ import annotations

import re
import ssl
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from .constants import HTTP_TIMEOUT, USER_AGENT
from .fingerprints import service_for_cname
from .models import HostResult, TakeoverInfo
from .runner import CommandRunner
from .tools import tool_path

_IP_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")


class TakeoverChecker:
    """Flag hosts whose CNAME points at an unclaimed SaaS resource."""

    def __init__(self, runner: CommandRunner,
                 log: Callable[[str], None] | None = None,
                 on_update: Callable[[], None] | None = None):
        self.runner = runner
        self.log = log or (lambda _msg: None)
        self.on_update = on_update or (lambda: None)

    def check(self, hosts: list[str], results: dict[str, HostResult]) -> dict[str, TakeoverInfo]:
        if not hosts:
            return {}
        self.log(f"\n=== Takeover check ({len(hosts)} hosts) ===")
        cnames = self._collect_cnames(hosts, results)

        candidates: dict[str, tuple[str, Any]] = {}
        for host, names in cnames.items():
            for cname in sorted(names):
                info = service_for_cname(cname)
                if info:
                    candidates[host] = (cname, info)
                    break
        self.log(f"  [*] {len(candidates)} host(s) point at takeover-prone services")

        takeovers: dict[str, TakeoverInfo] = {}
        for host, (cname, info) in sorted(candidates.items()):
            if not self.runner.active():
                return takeovers
            self.log(f"  [?] {host} -> {cname} ({info['service']})")
            verdict, status, url = self._probe(host, info)
            if not verdict:
                self.log("  [ok] service responded - not dangling")
                continue
            self.log(f"  [!] {verdict} takeover: {host} ({info['service']})")
            cur = results.get(host, {})
            cur["url"] = cur.get("url") or url
            cur["status"] = cur.get("status") or status
            cur["takeover"] = verdict
            cur["service"] = info["service"]
            if not cur.get("cname"):
                cur["cname"] = sorted(cnames.get(host, []))
            results[host] = cur
            takeovers[host] = {"service": info["service"], "cname": cname, "verdict": verdict}
            self.on_update()
        self.log(f"[+] takeover candidates flagged: {len(takeovers)}")
        return takeovers

    # ---------- dns ----------
    def _collect_cnames(self, hosts: list[str],
                        results: dict[str, HostResult]) -> dict[str, set[str]]:
        cnames: dict[str, set[str]] = {}
        for host, row in results.items():
            for cname in row.get("cname") or []:
                cname = str(cname).strip().rstrip(".").lower()
                if cname:
                    cnames.setdefault(host, set()).add(cname)

        dnsx = tool_path("dnsx")
        if not dnsx:
            self.log("  [i] dnsx not available - using httpx CNAMEs only")
            return cnames

        for offset in range(0, len(hosts), 500):
            if not self.runner.active():
                return cnames
            batch = hosts[offset:offset + 500]
            lines = self.runner.run(
                [dnsx, "-silent", "-no-color", "-cname", "-resp"],
                input_data="\n".join(batch) + "\n",
                label=f"dnsx cname ({offset + 1}-{offset + len(batch)})",
                stream=False,
            )
            for line in lines:
                parsed = self._parse_cname_line(line)
                if parsed is None:
                    continue
                host, value = parsed
                if _IP_RE.match(value):
                    continue
                cnames.setdefault(host, set()).add(value)
        return cnames

    @staticmethod
    def _parse_cname_line(line: str) -> tuple[str, str] | None:
        """Parse dnsx output.

        dnsx -cname -resp prints ``host [CNAME] [target]``; older builds print
        ``host [CNAME target]`` or ``host [target]``.
        """
        line = line.strip()
        match = re.match(r"^(\S+)\s+\[CNAME\]\s+\[(.+)\]", line, flags=re.I)
        if match:
            return match.group(1).lower(), match.group(2).strip().rstrip(".").lower()

        match = re.match(r"^(\S+)\s+\[(.+)\]$", line)
        if not match:
            return None
        value = re.sub(r"^CNAME\s+", "", match.group(2).strip(), flags=re.I)
        return match.group(1).lower(), value.rstrip(".").lower()

    # ---------- http ----------
    @staticmethod
    def fetch(url: str) -> tuple[int, str]:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT,
                                        context=context) as response:
                return response.status, response.read(200_000).decode("utf-8", "ignore")
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, exc.read(200_000).decode("utf-8", "ignore")
            except Exception:  # noqa: BLE001 - body is best-effort
                return exc.code, ""
        except Exception:  # noqa: BLE001 - DNS/TLS/connection failures mean "not serving"
            return 0, ""

    def _probe(self, host: str, info: Any) -> tuple[str | None, int, str]:
        for scheme in ("https", "http"):
            url = f"{scheme}://{host}"
            status, body = self.fetch(url)
            if status:
                low = body.lower()
                if any(marker in low for marker in info["markers"]):
                    return "LIKELY", status, url
                return None, status, url
        return "POSSIBLE", 0, f"https://{host}"
