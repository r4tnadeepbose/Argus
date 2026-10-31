#!/usr/bin/env python3
<<<<<<< HEAD
"""Launcher for the recon GUI.

The implementation lives in the ``recon`` package; this file exists so the
tool can still be started with ``python recon_gui.py``.
"""

from recon.app import main

if __name__ == "__main__":
    main()
=======
"""
recon_gui.py - Subdomain recon GUI with proper recursion.

Pipeline per cycle:
  1. subfinder -d <root> -all      -> passive subdomains of the root
  2. httpx -mc <codes>             -> keep only hosts matching status filter
  3. dnsx + wordlist               -> brute-force prefixes under each live host
  4. those resolved names become the next cycle's roots -> repeat up to N cycles

Tools are looked up by absolute path first (TOOL_PATHS), then PATH as fallback.
This avoids the "process was launched before PATH changed" problem entirely.

Requires: subfinder, httpx, dnsx installed somewhere.
"""

import json
import os
import queue
import re
import shutil
import subprocess
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext, ttk


# ---------- tool discovery ----------
# Absolute paths are tried first. Add or change these if you move the binaries.
TOOL_PATHS = {
    "subfinder": r"C:\Users\boser\go\bin\subfinder.exe",
    "httpx":     r"C:\Users\boser\go\bin\httpx.exe",
    "dnsx":      r"C:\Users\boser\go\bin\dnsx.exe",
}


def tool_path(name):
    """Return absolute path to a tool if it exists, else fall back to PATH lookup."""
    p = TOOL_PATHS.get(name)
    if p and os.path.isfile(p):
        return p
    return shutil.which(name)


# ---------- built-in wordlist ----------
BUILTIN_WORDLIST = [
    "www", "api", "dev", "staging", "stage", "test", "uat", "qa", "prod",
    "admin", "portal", "app", "apps", "beta", "alpha", "demo", "sandbox",
    "internal", "intranet", "vpn", "mail", "smtp", "webmail", "cdn",
    "static", "assets", "img", "images", "media", "auth", "sso", "login",
    "account", "accounts", "oauth", "db", "database", "cache", "queue",
    "monitor", "metrics", "grafana", "kibana", "logs", "ci", "cd",
    "jenkins", "gitlab", "git", "build", "deploy", "docs", "wiki", "help",
    "support", "status", "health", "m", "mobile", "old", "new",
    "v1", "v2", "v3",
]


class ReconApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Subdomain Recon - passive + active recursion")
        self.root.geometry("980x740")

        self.proc = None
        self.is_running = False
        self.log_queue = queue.Queue()
        self.results = {}          # host -> {url, status}
        self.seen_roots = set()    # domains already fed to subfinder
        self.seen_hosts = set()    # every hostname ever probed/resolved

        self._build_ui()
        self._poll_log()
        self._preflight()

    # ---------- UI ----------
    def _build_ui(self):
        row1 = ttk.Frame(self.root, padding=10)
        row1.pack(fill=tk.X)

        ttk.Label(row1, text="Target:").grid(row=0, column=0, sticky=tk.W)
        self.domain_var = tk.StringVar(value="zepto.com")
        ttk.Entry(row1, textvariable=self.domain_var, width=32).grid(row=0, column=1, padx=(6, 12))

        ttk.Label(row1, text="Cycles:").grid(row=0, column=2)
        self.cycles_var = tk.StringVar(value="3")
        ttk.Spinbox(row1, from_=1, to=10, textvariable=self.cycles_var, width=4).grid(row=0, column=3, padx=(6, 12))

        ttk.Label(row1, text="Status:").grid(row=0, column=4)
        self.status_var = tk.StringVar(value="200,301,302,403")
        ttk.Entry(row1, textvariable=self.status_var, width=18).grid(row=0, column=5, padx=(6, 0))

        row2 = ttk.Frame(self.root, padding=(10, 0))
        row2.pack(fill=tk.X)
        self.use_all = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text="subfinder -all", variable=self.use_all).pack(side=tk.LEFT)
        self.use_brute = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text="dnsx brute-force recursion", variable=self.use_brute).pack(side=tk.LEFT, padx=(16, 0))

        ttk.Label(row2, text="Wordlist:").pack(side=tk.LEFT, padx=(16, 4))
        self.wordlist_var = tk.StringVar(value="")
        ttk.Entry(row2, textvariable=self.wordlist_var, width=40).pack(side=tk.LEFT)
        ttk.Button(row2, text="Browse", command=self._pick_wordlist).pack(side=tk.LEFT, padx=(4, 0))

        btns = ttk.Frame(self.root, padding=10)
        btns.pack(fill=tk.X)
        self.start_btn = ttk.Button(btns, text="Start", command=self.start)
        self.start_btn.pack(side=tk.LEFT)
        self.stop_btn = ttk.Button(btns, text="Stop", command=self.stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=8)
        ttk.Button(btns, text="Export JSON", command=self.export).pack(side=tk.LEFT, padx=8)
        ttk.Button(btns, text="Clear log", command=self.clear_log).pack(side=tk.LEFT)

        logf = ttk.LabelFrame(self.root, text="Log", padding=8)
        logf.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.log_area = scrolledtext.ScrolledText(logf, state=tk.DISABLED, height=28,
                                                   font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def _pick_wordlist(self):
        p = filedialog.askopenfilename(
            title="Choose wordlist",
            filetypes=[("Text", "*.txt"), ("All files", "*.*")],
        )
        if p:
            self.wordlist_var.set(p)

    # ---------- logging ----------
    def log(self, msg):
        self.log_queue.put(msg)

    def _poll_log(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_area.config(state=tk.NORMAL)
                self.log_area.insert(tk.END, msg + "\n")
                self.log_area.see(tk.END)
                self.log_area.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.root.after(80, self._poll_log)

    def clear_log(self):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.delete("1.0", tk.END)
        self.log_area.config(state=tk.DISABLED)

    # ---------- preflight ----------
    def _preflight(self):
        self.log("=== Preflight ===")
        missing = []
        for t in ("subfinder", "httpx", "dnsx"):
            p = tool_path(t)
            if p:
                self.log(f"  [ok] {t} -> {p}")
            else:
                self.log(f"  [MISSING] {t} not found")
                missing.append(t)
        if missing:
            self.log(f"[!] Missing tools: {', '.join(missing)}")
            self.log(f"    Expected at: {TOOL_PATHS}")
            self.log("    Fix TOOL_PATHS at the top of this file, or install the binaries.")
        self.log("")

    # ---------- subprocess runner ----------
    def _run(self, cmd, input_data=None, label=None):
        """Run cmd, stream stdout into the log. Returns list of output lines."""
        if not self.is_running:
            return []
        self.log(f"$ {label or cmd}")
        lines = []
        try:
            self.proc = subprocess.Popen(
                cmd, shell=True,
                stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1,
            )
            if input_data is not None:
                try:
                    self.proc.stdin.write(input_data)
                    self.proc.stdin.close()
                except BrokenPipeError:
                    pass
            for line in self.proc.stdout:
                line = line.rstrip()
                if line:
                    lines.append(line)
                    self.log(f"  {line}")
            err = self.proc.stderr.read().strip()
            if err:
                self.log(f"  [stderr] {err[:500]}")
            self.proc.wait()
            return lines
        except Exception as e:
            self.log(f"  [error] {e}")
            return lines
        finally:
            self.proc = None

    # ---------- stages ----------
    def _subfinder(self, domain, use_all):
        sf = tool_path("subfinder")
        if not sf:
            self.log("[!] subfinder not available")
            return set()
        flags = "-silent" + (" -all" if use_all else "")
        out = self._run(f'"{sf}" -d {domain} {flags}', label=f"subfinder {domain}")
        return set(out)

    def _httpx(self, hosts, codes):
        if not hosts:
            return {}
        hx = tool_path("httpx")
        if not hx:
            self.log("[!] httpx not available")
            return {}
        code_str = ",".join(codes)
        data = "\n".join(hosts) + "\n"
        lines = self._run(
            f'"{hx}" -silent -status-code -no-color -mc {code_str}',
            input_data=data, label=f"httpx -mc {code_str}",
        )
        found = {}
        for line in lines:
            m = re.match(r"^(https?://\S+)\s+\[(\d+)\]", line)
            if not m:
                continue
            url, code = m.group(1), int(m.group(2))
            host = re.sub(r"^https?://", "", url).split("/")[0].split(":")[0]
            found[host] = {"url": url, "status": code}
        return found

    def _dnsx(self, fqdns):
        if not fqdns:
            return set()
        dx = tool_path("dnsx")
        if not dx:
            self.log("[!] dnsx not available")
            return set()
        data = "\n".join(fqdns) + "\n"
        out = self._run(f'"{dx}" -silent -no-color', input_data=data, label="dnsx")
        return set(out)

    def _load_wordlist(self):
        path = self.wordlist_var.get().strip()
        if path:
            if not os.path.isfile(path):
                self.log(f"[!] Wordlist not found: {path} - using built-in")
                return BUILTIN_WORDLIST
            with open(path, encoding="utf-8", errors="ignore") as f:
                words = [l.strip() for l in f if l.strip() and not l.startswith("#")]
            self.log(f"[*] Loaded {len(words)} prefixes from {path}")
            return words
        self.log(f"[*] Using built-in wordlist ({len(BUILTIN_WORDLIST)} prefixes)")
        return BUILTIN_WORDLIST

    # ---------- pipeline ----------
    def start(self):
        if self.is_running:
            return
        domain = self.domain_var.get().strip().lower()
        if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", domain):
            messagebox.showerror("Invalid", "Enter a valid domain like example.com")
            return
        if not tool_path("subfinder") or not tool_path("httpx"):
            messagebox.showerror(
                "Missing tools",
                "subfinder and/or httpx not found.\n\n"
                "Check TOOL_PATHS at the top of recon_gui.py."
            )
            return
        try:
            cycles = int(self.cycles_var.get())
        except ValueError:
            messagebox.showerror("Invalid", "Cycles must be a number.")
            return
        codes = [c.strip() for c in self.status_var.get().split(",") if c.strip().isdigit()]
        if not codes:
            messagebox.showerror("Invalid", "Provide status codes like 200,403.")
            return

        self.results.clear()
        self.seen_roots.clear()
        self.seen_hosts.clear()
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.log(f"=== Run: {domain} | cycles={cycles} | status={','.join(codes)} "
                 f"| {datetime.now().isoformat(timespec='seconds')} ===\n")

        threading.Thread(
            target=self._pipeline,
            args=(domain, cycles, codes, self.use_all.get(),
                  self.use_brute.get(), self._load_wordlist()),
            daemon=True,
        ).start()

    def stop(self):
        self.is_running = False
        self.log("[!] Stop requested.")
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.kill()
            except Exception:
                pass

    def _pipeline(self, root_domain, max_cycles, codes, use_all, use_brute, wordlist):
        try:
            current_parents = [root_domain]

            for cycle in range(1, max_cycles + 1):
                if not self.is_running:
                    break
                self.log(f"\n===== Cycle {cycle}/{max_cycles} =====")

                # ---- passive pass: subfinder on any new parent roots ----
                new_subs = set()
                for root in current_parents:
                    if root in self.seen_roots:
                        continue
                    self.seen_roots.add(root)
                    found = self._subfinder(root, use_all)
                    self.log(f"[+] subfinder {root}: {len(found)}")
                    new_subs |= found

                # ---- probe ----
                probe_set = new_subs - self.seen_hosts
                if cycle == 1:
                    probe_set.add(root_domain)
                if not probe_set:
                    self.log("[*] no new hosts to probe - stopping.")
                    break
                self.log(f"[*] probing {len(probe_set)} host(s)")
                hits = self._httpx(probe_set, codes)
                self.seen_hosts.update(probe_set)
                for h, info in hits.items():
                    self.results[h] = info
                    self.log(f"  [live] {info['url']} [{info['status']}]")
                self.log(f"[+] {len(hits)} live host(s) this cycle")

                if not use_brute or cycle == max_cycles:
                    break
                if not hits:
                    self.log("[*] no live hosts, cannot recurse - stopping.")
                    break

                # ---- active pass: brute-force prefixes under each live host ----
                candidates = []
                for parent in hits:
                    for prefix in wordlist:
                        fqdn = f"{prefix}.{parent}"
                        if fqdn not in self.seen_hosts:
                            candidates.append(fqdn)
                if not candidates:
                    self.log("[*] no new candidates - stopping.")
                    break
                self.log(f"[*] dnsx testing {len(candidates)} candidate(s)")
                resolved = self._dnsx(candidates)
                self.log(f"[+] {len(resolved)} resolved")
                if not resolved:
                    self.log("[*] nothing new resolved - stopping.")
                    break

                self.seen_hosts.update(resolved)
                current_parents = sorted(resolved)

            # ---- summary ----
            self.log("\n=== Summary ===")
            if self.results:
                for h in sorted(self.results):
                    info = self.results[h]
                    self.log(f"  {info['status']:>3}  {info['url']}")
            else:
                self.log("  (no hosts matched)")
            self.log(f"Total live: {len(self.results)}")
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))

    # ---------- export ----------
    def export(self):
        if not self.results:
            messagebox.showinfo("Nothing", "Run a scan first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile=f"recon_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        if not path:
            return
        with open(path, "w") as f:
            json.dump(self.results, f, indent=2, sort_keys=True)
        self.log(f"[+] Saved {len(self.results)} result(s) to {path}")


if __name__ == "__main__":
    try:
        root = tk.Tk()
        try:
            ttk.Style().theme_use("clam")
        except Exception:
            pass
        ReconApp(root)
        root.mainloop()
    except ModuleNotFoundError as e:
        print(f"[!] {e}. This Python build has no Tkinter.")
        print("    Try: C:\\Users\\boser\\AppData\\Local\\Programs\\Python\\Python313\\python.exe recon_gui.py")
>>>>>>> 7e7ddf86d73b1be5c8c229c89b1646adb03920ce
