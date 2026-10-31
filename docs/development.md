# Development

## Setup

```bash
python -m pip install -r requirements-dev.txt
```

No runtime dependencies. Tests never invoke external binaries or networks.

## Tests

```bash
python -m pytest                 # all tests
python -m pytest -q tests/test_pipeline.py
python -m pytest --cov=recon     # with coverage (UI modules omitted)
```

Test layout:

| File | Covers |
|---|---|
| `tests/test_fingerprints.py` | CNAME suffix matching and normalisation |
| `tests/test_state.py` | state/results persistence, resume pointer, legacy files |
| `tests/test_takeover.py` | verdict logic, dnsx parsing, httpx-CNAME fallback |
| `tests/test_pipeline.py` | full run, stop/resume, cycle limits, wordlist defaults |
| `tests/test_wordlists.py` | loader fallbacks and comment handling |

The pipeline tests subclass `ReconPipeline` and override `_subfinder`, `_httpx`
and `_dnsx`, which is the intended seam for new stages too.

## Lint

```bash
ruff check .
ruff format --check .   # optional
```

Rules are configured in `pyproject.toml` (line length 100).

## Adding a feature

1. Put logic in the narrowest module (`takeover.py`, `state.py`, …), not in the UI.
2. Keep the UI layer to widgets + threading; schedule cross-thread updates with
   `root.after(0, ...)`.
3. Add a test that fails before your change.
4. Update `CHANGELOG.md` and the relevant `docs/` page.

## Using the pipeline headlessly

```python
from recon.pipeline import PipelineConfig, ReconPipeline
from recon.runner import CommandRunner
from recon.state import RunStore

store = RunStore()
runner = CommandRunner(log=print, should_run=lambda: True)
cfg = PipelineConfig(domain="example.com", cycles=2)
pipeline = ReconPipeline(cfg, runner, store, log=print, run_id="manual")
pipeline.run()
print(len(pipeline.results))
```

This uses the real binaries and writes to `runs/manual/`.

## Releasing

1. Bump `__version__` in `recon/__init__.py` and `version` in `pyproject.toml`.
2. Update `CHANGELOG.md`.
3. Run `python -m pytest` and `ruff check .`.
4. Tag: `git tag vX.Y.Z` and push.

## Style

- Type hints on public functions; no third-party imports at module import time
  in the core package (Tkinter only inside `recon/ui` and `recon/app.py`).
- Comments explain *why*, not *what*.
- Keep functions small; prefer a new small module over a growing one.
