"""Main application window."""

from __future__ import annotations

import csv
import json
import os
import re
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from ..constants import RUNS_DIR, SOFTWARE_NAME, VERSION
from ..models import HostResult, ResumeState
from ..pipeline import PipelineConfig, ReconPipeline
from ..runner import CommandRunner
from ..state import RunStore
from ..tools import missing_tools, tool_path
from ..wordlists import load_wordlist
from .log_panel import LogPanel
from .results_table import ResultsTable

_DOMAIN_RE = re.compile(r"^[a-z0-9.-]+\.[a-z]{2,}$")


class ReconApp:
    def __init__(self, root: tk.Tk, store: RunStore | None = None):
        self.root = root
        self.store = store or RunStore()
        self.is_running = False
        self.pipeline: ReconPipeline | None = None
        self.runner: CommandRunner | None = None
        self._hint_logged = False

        self.root.title(f"{SOFTWARE_NAME} {VERSION} - subdomain recon")
        self.root.geometry("1180x820")

        self._build_ui()
        self._poll_log()
        self._preflight()
        self._load_resume_hint()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        row1 = ttk.Frame(self.root, padding=10)
        row1.pack(fill=tk.X)

        ttk.Label(row1, text="Target:").grid(row=0, column=0, sticky=tk.W)
        self.domain_var = tk.StringVar(value="zepto.com")
        ttk.Entry(row1, textvariable=self.domain_var, width=30).grid(
            row=0, column=1, padx=(6, 12))

        ttk.Label(row1, text="Cycles:").grid(row=0, column=2)
        self.cycles_var = tk.StringVar(value="3")
        ttk.Spinbox(row1, from_=1, to=10, textvariable=self.cycles_var, width=4).grid(
            row=0, column=3, padx=(6, 12))

        ttk.Label(row1, text="Status:").grid(row=0, column=4)
        self.status_var = tk.StringVar(value="200,301,302,403")
        ttk.Entry(row1, textvariable=self.status_var, width=18).grid(
            row=0, column=5, padx=(6, 12))

        self.shots_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row1, text="Screenshots (needs Chrome)",
                        variable=self.shots_var).grid(row=0, column=6, padx=(0, 12))
        self.takeover_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row1, text="Takeover check",
                        variable=self.takeover_var).grid(row=0, column=7)

        row2 = ttk.Frame(self.root, padding=(10, 0))
        row2.pack(fill=tk.X)
        self.use_all = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text="subfinder -all", variable=self.use_all).pack(side=tk.LEFT)
        self.use_brute = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text="dnsx brute-force recursion",
                        variable=self.use_brute).pack(side=tk.LEFT, padx=(16, 0))

        ttk.Label(row2, text="Wordlist:").pack(side=tk.LEFT, padx=(16, 4))
        self.wordlist_var = tk.StringVar(value="")
        ttk.Entry(row2, textvariable=self.wordlist_var, width=40).pack(side=tk.LEFT)
        ttk.Button(row2, text="Browse", command=self._pick_wordlist).pack(
            side=tk.LEFT, padx=(4, 0))

        buttons = ttk.Frame(self.root, padding=10)
        buttons.pack(fill=tk.X)
        self.start_btn = ttk.Button(buttons, text="Start", command=self.start)
        self.start_btn.pack(side=tk.LEFT)
        self.resume_btn = ttk.Button(buttons, text="Resume", command=self.resume,
                                     state=tk.DISABLED)
        self.resume_btn.pack(side=tk.LEFT, padx=8)
        self.stop_btn = ttk.Button(buttons, text="Stop", command=self.stop,
                                   state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)
        ttk.Separator(buttons, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(buttons, text="Export JSON",
                   command=lambda: self.export("json")).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Export CSV",
                   command=lambda: self.export("csv")).pack(side=tk.LEFT, padx=8)
        ttk.Button(buttons, text="Copy URLs", command=self.copy_urls).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Copy selected",
                   command=self.copy_selected).pack(side=tk.LEFT, padx=8)
        ttk.Button(buttons, text="Open screenshot",
                   command=self.open_shot).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Runs folder", command=self.open_runs).pack(
            side=tk.LEFT, padx=8)
        ttk.Button(buttons, text="Clear log", command=self.clear_log).pack(side=tk.LEFT)

        progress = ttk.Frame(self.root, padding=(10, 0))
        progress.pack(fill=tk.X)
        self.prog = ttk.Progressbar(progress, mode="indeterminate", length=220)
        self.prog.pack(side=tk.LEFT)
        self.stats_var = tk.StringVar(value="idle")
        ttk.Label(progress, textvariable=self.stats_var).pack(side=tk.LEFT, padx=12)

        paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 10))
        self.table = ResultsTable(paned, on_open=self._open_host)
        paned.add(self.table, weight=3)
        self.log_panel = LogPanel(paned, height=14)
        paned.add(self.log_panel, weight=2)

    def _pick_wordlist(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose wordlist",
            filetypes=[("Text", "*.txt"), ("All files", "*.*")])
        if path:
            self.wordlist_var.set(path)

    # ---------- logging ----------
    def _log(self, message: str) -> None:
        self.log_panel.append(message)

    def _poll_log(self) -> None:
        self.log_panel.drain()
        self.root.after(80, self._poll_log)

    def clear_log(self) -> None:
        self.log_panel.clear()

    def _ui(self, callback) -> None:
        self.root.after(0, callback)

    # ---------- preflight ----------
    def _preflight(self) -> None:
        self._log("=== Preflight ===")
        missing = missing_tools()
        for name in ("subfinder", "httpx", "dnsx"):
            path = tool_path(name)
            if path:
                self._log(f"  [ok] {name} -> {path}")
            else:
                self._log(f"  [MISSING] {name} not found")
        if missing:
            self._log(f"[!] Missing tools: {', '.join(missing)}")
            self._log("    Set TOOL_PATHS in recon/constants.py, or install them.")
        self._log("")

    # ---------- run lifecycle ----------
    def start(self) -> None:
        if self.is_running:
            return
        domain = self.domain_var.get().strip().lower()
        if not _DOMAIN_RE.match(domain):
            messagebox.showerror("Invalid", "Enter a valid domain like example.com")
            return
        if missing_tools(("subfinder", "httpx")):
            messagebox.showerror(
                "Missing tools",
                "subfinder and/or httpx not found.\n\n"
                "Set TOOL_PATHS in recon/constants.py.")
            return
        try:
            cycles = int(self.cycles_var.get())
        except ValueError:
            messagebox.showerror("Invalid", "Cycles must be a number.")
            return
        codes = [int(code) for code in self.status_var.get().split(",")
                 if code.strip().isdigit()]
        if not codes:
            messagebox.showerror("Invalid", "Provide status codes like 200,403.")
            return

        words, source = load_wordlist(self.wordlist_var.get().strip())
        self._log(f"[*] Loaded {source}")
        cfg = PipelineConfig(
            domain=domain, cycles=cycles, codes=codes,
            use_all=self.use_all.get(), use_brute=self.use_brute.get(),
            use_shots=self.shots_var.get(), use_takeover=self.takeover_var.get(),
            wordlist_path=self.wordlist_var.get().strip(), wordlist=words,
        )
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        pipeline = self._make_pipeline(cfg, run_id)
        self.store.shot_dir(run_id)
        self._refresh()
        self._begin_run(
            f"=== Run: {domain} | cycles={cycles} | status={','.join(map(str, codes))} "
            f"| {datetime.now().isoformat(timespec='seconds')} ===\n")
        threading.Thread(target=self._run_worker,
                         args=(pipeline, None), daemon=True).start()

    def resume(self) -> None:
        if self.is_running:
            return
        found = self.store.resumable()
        if not found:
            messagebox.showinfo("No resume", "No resumable run state found.")
            self._load_resume_hint()
            return
        _cfg, state = found
        try:
            cfg = PipelineConfig(
                domain=state["domain"],
                cycles=int(state["cycles"]),
                codes=[int(code) for code in state["codes"]],
                use_all=bool(state.get("use_all", True)),
                use_brute=bool(state.get("use_brute", True)),
                use_shots=bool(state.get("use_shots", True)),
                use_takeover=bool(state.get("use_takeover", True)),
                wordlist_path=state.get("wordlist_path", ""),
                wordlist=state.get("wordlist") or [],
            )
        except (KeyError, TypeError, ValueError) as exc:
            messagebox.showerror("Resume failed", f"Invalid state file:\n{exc}")
            return

        self._apply_cfg_to_ui(cfg)
        pipeline = self._make_pipeline(cfg, state["run_id"])
        self._refresh()
        self._begin_run(f"=== Resume: {state['run_id']} | cycle {state.get('cycle')} "
                        f"| phase {state.get('phase')} ===\n")
        threading.Thread(target=self._run_worker,
                         args=(pipeline, state), daemon=True).start()

    def _make_pipeline(self, cfg: PipelineConfig, run_id: str) -> ReconPipeline:
        runner = CommandRunner(self._log, lambda: self.is_running)
        pipeline = ReconPipeline(
            cfg, runner, store=self.store, log=self._log,
            on_update=lambda: self._ui(self._refresh), run_id=run_id)
        self.pipeline = pipeline
        self.runner = runner
        return pipeline

    def _apply_cfg_to_ui(self, cfg: PipelineConfig) -> None:
        self.domain_var.set(cfg.domain)
        self.cycles_var.set(str(cfg.cycles))
        self.status_var.set(",".join(str(code) for code in cfg.codes))
        self.use_all.set(cfg.use_all)
        self.use_brute.set(cfg.use_brute)
        self.shots_var.set(cfg.use_shots)
        self.takeover_var.set(cfg.use_takeover)
        self.wordlist_var.set(cfg.wordlist_path or "")

    def _begin_run(self, banner: str) -> None:
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.resume_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.prog.start(12)
        self._refresh()
        self._log(banner)

    def _run_worker(self, pipeline: ReconPipeline,
                    resume_state: ResumeState | None) -> None:
        try:
            pipeline.run(resume_state)
        except Exception as exc:  # noqa: BLE001 - report and keep the UI usable
            self._log(f"[!] run failed: {exc!r}")
        finally:
            self.is_running = False
            if pipeline.completed and pipeline.run_id:
                self.store.mark_finished(pipeline.run_id, pipeline.cfg.domain)
            self._ui(self._finish_ui)

    def _finish_ui(self) -> None:
        self.prog.stop()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self._refresh()
        self._load_resume_hint()

    def stop(self) -> None:
        if not self.is_running:
            return
        self.is_running = False
        self._log("[!] Stop requested - saving state so you can Resume.")
        if self.runner:
            self.runner.kill()

    # ---------- view ----------
    def _results(self) -> dict[str, HostResult]:
        return self.pipeline.results if self.pipeline else {}

    def _refresh(self) -> None:
        results = self._results()
        self.table.render(results)
        state = "running" if self.is_running else "idle"
        takeovers = len(self.pipeline.takeovers) if self.pipeline else 0
        self.stats_var.set(f"{state} | live: {len(results)} | takeovers: {takeovers}")

    def _load_resume_hint(self) -> None:
        found = self.store.resumable()
        usable = found is not None
        self.resume_btn.config(
            state=tk.NORMAL if usable and not self.is_running else tk.DISABLED)
        if usable and not self._hint_logged:
            _cfg, state = found
            self._hint_logged = True
            self._log(f"[*] Resumable run found: {state.get('run_id')} "
                      f"({state.get('domain')}, cycle {state.get('cycle')}) - "
                      f"press Resume.")
            return
        raw = self.store.read_resume_cfg()
        if not usable and raw and not raw.get("run_id") and not self._hint_logged:
            self._hint_logged = True
            self._log("[i] Legacy resume.cfg found (no run state) - ignored.")

    # ---------- export / copy / open ----------
    def export(self, kind: str = "json") -> None:
        results = self._results()
        if not results:
            messagebox.showinfo("Nothing", "Run a scan first.")
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if kind == "json":
            path = filedialog.asksaveasfilename(
                defaultextension=".json", filetypes=[("JSON", "*.json")],
                initialfile=f"recon_{stamp}.json", initialdir=str(RUNS_DIR))
            if not path:
                return
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(results, fh, indent=2, sort_keys=True)
        else:
            path = filedialog.asksaveasfilename(
                defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                initialfile=f"recon_{stamp}.csv", initialdir=str(RUNS_DIR))
            if not path:
                return
            fields = ["status", "host", "url", "title", "tech", "takeover",
                      "service", "screenshot"]
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                for host in sorted(results):
                    row = dict(results[host])
                    row["host"] = host
                    row["tech"] = ", ".join(row.get("tech") or [])
                    writer.writerow(row)
        self._log(f"[+] Saved {len(results)} result(s) to {path}")

    def copy_urls(self) -> None:
        urls = [(row.get("url") or f"https://{host}")
                for host, row in sorted(self._results().items())]
        if not urls:
            messagebox.showinfo("Nothing", "No live hosts to copy.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(urls))
        self._log(f"[+] Copied {len(urls)} URL(s) to clipboard")

    def copy_selected(self) -> None:
        selection = self.table.selected_hosts()
        if not selection:
            messagebox.showinfo("Nothing", "Select one or more rows first.")
            return
        results = self._results()
        urls = [(results.get(host, {}).get("url") or f"https://{host}")
                for host in selection]
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(urls))
        self._log(f"[+] Copied {len(urls)} selected URL(s)")

    def _open_host(self, host: str) -> None:
        url = self._results().get(host, {}).get("url") or f"https://{host}"
        webbrowser.open(url)

    def open_shot(self) -> None:
        results = self._results()
        for host in self.table.selected_hosts():
            path = results.get(host, {}).get("screenshot")
            if path and os.path.isfile(path):
                self._open_path(path)
                return
        messagebox.showinfo(
            "No screenshot",
            "No screenshot for the selected host.\n"
            "Enable 'Screenshots' before running (httpx -ss needs Chrome).")

    def open_runs(self) -> None:
        os.makedirs(RUNS_DIR, exist_ok=True)
        self._open_path(str(RUNS_DIR))

    @staticmethod
    def _open_path(path: str) -> None:
        try:
            if hasattr(os, "startfile"):
                os.startfile(path)  # noqa: S606 - local, user-requested
            else:
                webbrowser.open("file://" + os.path.abspath(path))
        except OSError:
            pass
