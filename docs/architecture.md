# Architecture

Recon is split into small, UI-independent modules so the pipeline can be tested
without a display or external binaries.

## Module map

| Module | Responsibility |
|---|---|
| `recon/app.py` | Entry point; creates the Tk root and window. |
| `recon/constants.py` | Paths (`runs/`, `resume.cfg`), tool locations, chunk size, timeout. |
| `recon/tools.py` | Resolve external binaries (configured path, then `PATH`). |
| `recon/wordlists.py` | Built-in prefix list and wordlist file loader. |
| `recon/models.py` | `HostResult`, `TakeoverInfo`, `ResumeState` types. |
| `recon/fingerprints.py` | CNAME suffix → service + page markers. |
| `recon/runner.py` | `CommandRunner`: subprocess execution, streaming logs, kill switch. |
| `recon/state.py` | `RunStore`: atomic state/history writes and resume pointer. |
| `recon/takeover.py` | `TakeoverChecker`: CNAME collection, HTTP fingerprinting. |
| `recon/pipeline.py` | `ReconPipeline`: the recursive scan. |
| `recon/ui/main_window.py` | Widgets, threading, export/copy actions. |
| `recon/ui/results_table.py` | Sortable host table. |
| `recon/ui/log_panel.py` | Queue-backed log widget. |

## Data flow

```
Tk main thread                       worker thread
──────────────                       ─────────────
start() ──► build PipelineConfig
         └► ReconPipeline ─────────► run()
                                      ├─ _subfinder ─┐
                                      ├─ _httpx     ├─ CommandRunner ─► binaries
                                      ├─ _dnsx      ┘
                                      ├─ _save_state ─► RunStore ─► runs/<id>/state.json
                                      └─ TakeoverChecker ─► dnsx + urllib
        ◄── on_update() ── root.after(0, _refresh)
```

- The worker never touches Tk directly. `on_update` is scheduled with
  `root.after(0, ...)` and the log panel is fed through a `queue.Queue`.
- `CommandRunner.active()` reads `ReconApp.is_running`; **Stop** flips that flag
  and kills the running process, so the pipeline exits at the next checkpoint.
- State is written *before* each dnsx chunk so a stop mid-chunk is retried on
  resume, not skipped.

## Pipeline stages

1. **Passive** (`_passive_pass`): subfinder per unvisited root.
2. **Probe**: `probe_set = (new_subs | pending_probe) - probed`; httpx parses
   JSON lines into `HostResult` entries.
3. **Brute** (`_brute_pass`): chunked dnsx under each live host. Resolved names
   go to `pending_probe` and become next cycle's roots.
4. **Takeover**: see [takeover-checks.md](takeover-checks.md).
5. **Persistence**: `results.json` always; `resume.cfg` marked `finished` only on
   clean completion.

Two sets prevent mistakes: `seen_hosts` deduplicates discovery, while `probed`
records what actually reached httpx. That distinction lets DNS-resolved hosts
be probed in the next cycle without re-discovering them.

## Threading rules

- Only the Tk main thread mutates widgets.
- Shared result dictionaries are mutated by the worker and copied by the table
  renderer before iteration.
- The `is_running` flag is the single cancellation signal.

## Extension points

- **New takeover service**: add an entry to `TAKEOVER_SERVICES`.
- **Different probe logic**: override `ReconPipeline._httpx` (used by tests).
- **Alternate front-end (CLI/web)**: reuse `ReconPipeline` + `RunStore` directly;
  no UI imports required.
- **Persistence**: `RunStore` takes explicit `runs_dir`/`resume_file` paths,
  which is how tests isolate state.
