"""Run persistence: resume pointer, full state, history and results."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .constants import RESUME_FILE, RUNS_DIR


class RunStore:
    """Owns everything written under ``runs/`` plus the ``resume.cfg`` pointer."""

    def __init__(self, runs_dir: str | Path | None = None,
                 resume_file: str | Path | None = None):
        self.runs_dir = Path(runs_dir) if runs_dir else Path(RUNS_DIR)
        self.resume_file = Path(resume_file) if resume_file else Path(RESUME_FILE)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    # ---------- paths ----------
    def run_dir(self, run_id: str | None) -> Path:
        return self.runs_dir / run_id if run_id else self.runs_dir

    def state_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "state.json"

    def results_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "results.json"

    def shot_dir(self, run_id: str | None) -> str:
        path = self.run_dir(run_id)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    # ---------- writing ----------
    @staticmethod
    def atomic_write(path: str | Path, text: str) -> None:
        path = Path(path)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)

    def save_state(self, state: dict[str, Any]) -> None:
        run_id = state.get("run_id")
        if not run_id:
            return
        path = self.state_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.atomic_write(path, json.dumps(state, indent=1))

        phase = state.get("phase") or "passive"
        live_parents = state.get("live_parents") or []
        cursor = int(state.get("parent_cursor") or 0)
        resume_from = live_parents[cursor] if phase == "brute" and cursor < len(live_parents) else "-"
        from datetime import datetime

        self.atomic_write(self.resume_file, "\n".join([
            f"run_id={run_id}",
            f"domain={state.get('domain')}",
            f"cycle={state.get('cycle')}",
            f"resume_from={resume_from}",
            f"index={state.get('index')}",
            "status=running",
            f"updated_at={datetime.now().isoformat(timespec='seconds')}",
        ]) + "\n")

    def write_results(self, run_id: str, domain: str,
                      results: dict[str, Any], takeovers: dict[str, Any]) -> None:
        if not run_id:
            return
        from datetime import datetime

        data = {
            "run_id": run_id,
            "domain": domain,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "results": results,
            "takeovers": takeovers,
        }
        path = self.results_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.atomic_write(path, json.dumps(data, indent=2))

    def mark_finished(self, run_id: str, domain: str | None = None) -> None:
        from datetime import datetime

        self.atomic_write(self.resume_file, "\n".join([
            f"run_id={run_id}",
            f"domain={domain or ''}",
            "status=finished",
            f"updated_at={datetime.now().isoformat(timespec='seconds')}",
        ]) + "\n")

    # ---------- reading ----------
    @staticmethod
    def parse_cfg(path: str | Path) -> dict[str, str]:
        data: dict[str, str] = {}
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    data[key.strip()] = value.strip()
        except OSError:
            pass
        return data

    def read_resume_cfg(self) -> dict[str, str]:
        return self.parse_cfg(self.resume_file)

    def load_state(self, run_id: str) -> dict[str, Any] | None:
        try:
            with open(self.state_path(run_id), encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None

    def resumable(self) -> tuple[dict[str, str], dict[str, Any]] | None:
        """Return ``(resume_cfg, state)`` when an unfinished run can be resumed."""
        cfg = self.read_resume_cfg()
        run_id = cfg.get("run_id")
        if not run_id or cfg.get("status") == "finished":
            return None
        state = self.load_state(run_id)
        if state is None:
            return None
        return cfg, state

    def run_ids(self) -> list[str]:
        """Newest-first list of run identifiers present on disk."""
        if not self.runs_dir.is_dir():
            return []
        return sorted(
            (p.name for p in self.runs_dir.iterdir() if p.is_dir()),
            reverse=True,
        )
