"""Recursive subdomain enumeration pipeline.

Per cycle:
  1. subfinder on each new parent root
  2. httpx status/tech/title/CNAME filtering
  3. dnsx brute-force under each live host (chunked, resumable)
  4. resolved names feed the next cycle

The pipeline is UI-agnostic: it talks through a :class:`CommandRunner`, a
:class:`RunStore` and callbacks, which makes it testable headlessly.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from .constants import CHUNK
from .models import HostResult, ResumeState, TakeoverInfo
from .runner import CommandRunner
from .state import RunStore
from .takeover import TakeoverChecker
from .tools import tool_path
from .wordlists import DEFAULT_WORDLIST


@dataclass
class PipelineConfig:
    """Everything needed to drive one scan."""

    domain: str
    cycles: int = 3
    codes: list[int] = field(default_factory=lambda: [200, 301, 302, 403])
    use_all: bool = True
    use_brute: bool = True
    use_shots: bool = True
    use_takeover: bool = True
    wordlist_path: str = ""
    wordlist: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.wordlist:
            self.wordlist = list(DEFAULT_WORDLIST)


class ReconPipeline:
    def __init__(
        self,
        cfg: PipelineConfig,
        runner: CommandRunner,
        store: RunStore,
        log: Callable[[str], None],
        on_update: Callable[[], None] | None = None,
        run_id: str | None = None,
    ):
        self.cfg = cfg
        self.runner = runner
        self.store = store
        self.log = log
        self.on_update = on_update or (lambda: None)
        self.run_id = run_id
        self.completed = False

        self.results: dict[str, HostResult] = {}
        self.takeovers: dict[str, TakeoverInfo] = {}
        self.seen_roots: set[str] = set()
        self.seen_hosts: set[str] = set()
        self.probed: set[str] = set()
        self.pending_probe: set[str] = set()

    # ---------- entry point ----------
    def run(self, resume_state: ResumeState | None = None) -> bool:
        if resume_state:
            self._restore(resume_state)
            cycle = int(resume_state.get("cycle") or 1)
            phase = resume_state.get("phase") or "passive"
            current_parents = list(resume_state.get("current_parents") or [self.cfg.domain])
            live_parents = list(resume_state.get("live_parents") or [])
            parent_cursor = int(resume_state.get("parent_cursor") or 0)
            index = int(resume_state.get("index") or 0)
            cycle_resolved = set(resume_state.get("cycle_resolved") or [])
            self.log(f"[*] Resumed {self.run_id} at cycle {cycle} ({phase}), "
                     f"{len(self.results)} result(s)")
            self.on_update()
        else:
            cycle = 1
            phase = "passive"
            current_parents = [self.cfg.domain]
            live_parents: list[str] = []
            parent_cursor = 0
            index = 0
            cycle_resolved: set[str] = set()

        try:
            while cycle <= self.cfg.cycles and self.runner.active():
                if phase == "passive":
                    self.log(f"\n===== Cycle {cycle}/{self.cfg.cycles} =====")
                    new_subs = self._passive_pass(current_parents)
                    if not self.runner.active():
                        break

                    probe_set = (new_subs | self.pending_probe) - self.probed
                    self.pending_probe = set()
                    if cycle == 1 and self.cfg.domain not in self.probed:
                        probe_set.add(self.cfg.domain)

                    hits: dict[str, HostResult] = {}
                    if probe_set:
                        self.log(f"[*] probing {len(probe_set)} host(s)")
                        hits = self._httpx(probe_set, self.cfg.codes, self.cfg.use_shots)
                        self.seen_hosts.update(probe_set)
                        self.probed.update(probe_set)
                        self._merge_hits(hits)
                    self.log(f"[+] {len(hits)} live host(s) this cycle")

                    live_parents = sorted(hits)
                    parent_cursor = 0
                    index = 0
                    phase = "brute"
                    self._save_state(phase, cycle, current_parents, live_parents,
                                     0, 0, cycle_resolved)
                if not self.runner.active():
                    break

                if self.cfg.use_brute and cycle < self.cfg.cycles and live_parents:
                    cycle_resolved = self._brute_pass(
                        cycle, current_parents, live_parents, parent_cursor, index,
                        cycle_resolved)
                    if not self.runner.active():
                        break

                if not cycle_resolved:
                    self.log("[*] nothing new resolved - stopping.")
                    break
                current_parents = sorted(cycle_resolved)
                cycle_resolved = set()
                phase = "passive"
                cycle += 1
                self._save_state(phase, cycle, current_parents, [], 0, 0, [])

            if self.runner.active():
                if self.cfg.use_takeover:
                    self._run_takeover()
                self.completed = self.runner.active()
            self._summary()
        finally:
            if self.run_id:
                self.store.write_results(self.run_id, self.cfg.domain,
                                         self.results, self.takeovers)
        return self.completed

    # ---------- stages ----------
    def _passive_pass(self, parents: list[str]) -> set[str]:
        found_all: set[str] = set()
        for root in parents:
            if not self.runner.active():
                break
            if root in self.seen_roots:
                continue
            self.seen_roots.add(root)
            found = self._subfinder(root, self.cfg.use_all)
            self.log(f"[+] subfinder {root}: {len(found)}")
            found_all |= found
        return found_all

    def _brute_pass(
        self,
        cycle: int,
        current_parents: list[str],
        live_parents: list[str],
        parent_cursor: int,
        index: int,
        cycle_resolved: set[str],
    ) -> set[str]:
        for position in range(parent_cursor, len(live_parents)):
            if not self.runner.active():
                break
            parent = live_parents[position]
            words = self.cfg.wordlist[index:] if position == parent_cursor else self.cfg.wordlist
            cursor = index if position == parent_cursor else 0
            while cursor < len(words):
                if not self.runner.active():
                    break
                chunk = words[cursor:cursor + CHUNK]
                fqdns = [f"{word}.{parent}" for word in chunk
                         if f"{word}.{parent}" not in self.seen_hosts]
                # Persist before the call so a mid-chunk stop resumes here.
                self._save_state("brute", cycle, current_parents, live_parents,
                                 position, cursor, cycle_resolved)
                if fqdns:
                    self.log(f"[*] dnsx {len(fqdns)} under {parent} (word idx {cursor})")
                    resolved = self._dnsx(fqdns)
                    if not self.runner.active():
                        break
                    fresh = resolved - self.seen_hosts
                    self.seen_hosts.update(fresh)
                    self.pending_probe |= fresh
                    cycle_resolved |= fresh
                    self.log(f"[+] {len(fresh)} new resolved")
                cursor += CHUNK
                index = cursor
                self._save_state("brute", cycle, current_parents, live_parents,
                                 position, cursor, cycle_resolved)
            if self.runner.active():
                index = 0
                self._save_state("brute", cycle, current_parents, live_parents,
                                 position + 1, 0, cycle_resolved)
        return cycle_resolved

    def _run_takeover(self) -> None:
        hosts = sorted(set(self.seen_hosts) | set(self.results))
        checker = TakeoverChecker(self.runner, self.log, on_update=self.on_update)
        self.takeovers = checker.check(hosts, self.results)

    # ---------- tools ----------
    def _subfinder(self, domain: str, use_all: bool) -> set[str]:
        binary = tool_path("subfinder")
        if not binary:
            self.log("[!] subfinder not available")
            return set()
        cmd = [binary, "-d", domain, "-silent"] + (["-all"] if use_all else [])
        out = self.runner.run(cmd, label=f"subfinder {domain}")
        return {line.strip().lower() for line in out if line.strip()}

    def _httpx(self, hosts: set[str] | list[str], codes: list[int],
               use_shots: bool) -> dict[str, HostResult]:
        if not hosts:
            return {}
        binary = tool_path("httpx")
        if not binary:
            self.log("[!] httpx not available")
            return {}
        code_str = ",".join(str(code) for code in codes)
        cmd = [binary, "-silent", "-json", "-no-color", "-status-code",
               "-title", "-td", "-cname", "-stats", "-si", "10", "-duc",
               "-mc", code_str]
        if use_shots:
            cmd.append("-ss")
        data = "\n".join(sorted(hosts)) + "\n"
        self.log(f"[*] httpx {len(hosts)} host(s) -mc {code_str}"
                 + (" -ss" if use_shots else ""))
        self.log("  httpx prints progress every 10s; large lists take a while.")

        allowed = set(codes)
        found: dict[str, HostResult] = {}
        live_count = 0

        def handle_line(line: str) -> None:
            nonlocal live_count
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                return
            parsed = self._parse_httpx(payload, allowed)
            if not parsed:
                return
            host, entry = parsed
            found[host] = entry
            current = self.results.get(host, {})
            current.update(entry)
            self.results[host] = current  # type: ignore[assignment]
            live_count += 1
            if live_count <= 100 or live_count % 100 == 0:
                self.log(f"  [live] {entry.get('url') or host} "
                         f"[{entry.get('status')}]")
            if live_count % 25 == 0:
                self.on_update()

        self.runner.run(
            cmd, input_data=data, label=f"httpx -mc {code_str}", stream=False,
            cwd=self.store.shot_dir(self.run_id), line_handler=handle_line,
            live_stderr=True, stats_prefix="[httpx]", heartbeat=30)
        self.log(f"[+] httpx live: {len(found)}")
        return found

    def _parse_httpx(self, payload: dict, allowed: set[int]) -> tuple[str, HostResult] | None:
        try:
            status = int(payload.get("status_code"))
        except (TypeError, ValueError):
            return None
        url = payload.get("url") or ""
        host = (urlsplit(url).hostname or "").lower()
        if not host or status not in allowed:
            return None
        screenshot = payload.get("screenshot") or ""
        if screenshot and not os.path.isabs(screenshot):
            screenshot = os.path.abspath(
                os.path.join(self.store.shot_dir(self.run_id), screenshot))
        entry: HostResult = {
            "url": url,
            "status": status,
            "title": (payload.get("title") or "").strip(),
            "tech": [str(item) for item in (payload.get("tech") or [])],
            "cname": [str(item) for item in (payload.get("cname") or [])],
            "screenshot": screenshot,
            "takeover": self.results.get(host, {}).get("takeover", ""),
        }
        return host, entry

    def _dnsx(self, fqdns: list[str]) -> set[str]:
        if not fqdns:
            return set()
        binary = tool_path("dnsx")
        if not binary:
            self.log("[!] dnsx not available")
            return set()
        data = "\n".join(fqdns) + "\n"
        out = self.runner.run([binary, "-silent", "-no-color"], input_data=data,
                              label=f"dnsx ({len(fqdns)})", stream=False)
        return {line.strip().lower() for line in out if line.strip()}

    # ---------- results ----------
    def _merge_hits(self, hits: dict[str, HostResult]) -> None:
        for host, info in hits.items():
            current = self.results.get(host, {})
            current.update(info)
            self.results[host] = current  # type: ignore[assignment]
        self.on_update()

    def _summary(self) -> None:
        self.log("\n=== Summary ===")
        if self.results:
            for host in sorted(self.results):
                row = self.results[host]
                line = f"  {str(row.get('status') or '-'):>3}  {row.get('url') or host}"
                if row.get("takeover"):
                    line += f"  [!] {row['takeover']} takeover"
                self.log(line)
        else:
            self.log("  (no hosts matched)")
        self.log(f"Total live: {len(self.results)} | takeovers: {len(self.takeovers)}")

    # ---------- persistence ----------
    def _save_state(self, phase: str, cycle: int, current_parents: list[str],
                    live_parents: list[str], parent_cursor: int, index: int,
                    cycle_resolved: set[str] | list[str]) -> None:
        if not self.run_id:
            return
        state: ResumeState = {
            "run_id": self.run_id,
            "domain": self.cfg.domain,
            "cycles": self.cfg.cycles,
            "codes": self.cfg.codes,
            "use_all": self.cfg.use_all,
            "use_brute": self.cfg.use_brute,
            "use_shots": self.cfg.use_shots,
            "use_takeover": self.cfg.use_takeover,
            "wordlist_path": self.cfg.wordlist_path,
            "wordlist": self.cfg.wordlist,
            "phase": phase,
            "cycle": cycle,
            "current_parents": list(current_parents),
            "live_parents": list(live_parents),
            "parent_cursor": parent_cursor,
            "index": index,
            "cycle_resolved": sorted(cycle_resolved),
            "seen_roots": sorted(self.seen_roots),
            "seen_hosts": sorted(self.seen_hosts),
            "probed": sorted(self.probed),
            "pending_probe": sorted(self.pending_probe),
            "results": self.results,
            "takeovers": self.takeovers,
        }
        self.store.save_state(state)

    def _restore(self, state: ResumeState) -> None:
        if not self.run_id:
            self.run_id = state.get("run_id")
        self.results = state.get("results") or {}
        self.takeovers = state.get("takeovers") or {}
        self.seen_roots = set(state.get("seen_roots") or [])
        self.seen_hosts = set(state.get("seen_hosts") or [])
        self.probed = set(state.get("probed") or [])
        self.pending_probe = set(state.get("pending_probe") or [])
