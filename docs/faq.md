# FAQ

### Is it legal to use this?

Only on domains you own or are explicitly authorized to test. Authorization can
come from ownership or from a program's published scope. When in doubt, get
written permission. See the notice in the [README](../README.md).

### Does Recon send my data anywhere?

No. The application has no telemetry and no network calls other than running
`subfinder`, `httpx`, `dnsx` and fetching pages for takeover checks. Results
stay in `runs/`.

### Why are there no Python dependencies?

Everything is built on the standard library (Tkinter, `subprocess`,
`urllib`, `csv`, `json`). This keeps installation simple and reduces supply-chain
surface. `requirements.txt` is intentionally empty.

### Can I use it on Linux or macOS?

Yes — the code is cross-platform. You need `python3-tk`, the ProjectDiscovery
binaries on `PATH`, and an X11/Wayland session for the GUI. Screenshots need
Chrome.

### Where do I change the tool paths?

`recon/constants.py` → `TOOL_PATHS`. Absolute paths are tried first, then
`PATH`.

### What does "cycles" mean?

Cycle 1 scans the target. Each later cycle takes newly resolved hosts as roots
and repeats passive discovery + brute force. Higher cycles = more coverage and
much more runtime.

### Why do some rows show a takeover verdict?

The CNAME points at an unclaimed SaaS resource. See
[takeover-checks.md](takeover-checks.md) for the difference between `LIKELY` and
`POSSIBLE`, and verify manually before reporting.

### Can I add my own takeover fingerprints?

Yes: extend `TAKEOVER_SERVICES` in `recon/fingerprints.py`. Tests live in
`tests/test_fingerprints.py`.

### Why is my old `resume.cfg` ignored?

Resuming requires a full state file tied to a `run_id`. A legacy file with only
`resume_from`/`index` cannot be reconstructed; the app logs a note and ignores
it.

### Do I need subfinder API keys?

Subfinder works with free sources out of the box. Configure its own
`provider-config.yaml` if you want more sources.

### Does Stop lose my results?

No. State is written continuously and partial results are saved to
`runs/<run_id>/results.json`; use **Resume** to continue.

### How many files does a run produce?

One directory under `runs/` with `state.json`, `results.json` and a screenshots
folder (if enabled).

### Can I run it headless / from a script?

The GUI needs a display, but the pipeline is UI-independent. Instantiate
`recon.pipeline.ReconPipeline` with a `CommandRunner` and `RunStore` from your
own script; see `docs/development.md`.
