# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-10-31

### Fixed
- Large httpx runs no longer look frozen: every live hit is logged, httpx
  `-stats` progress is forwarded to the log, and a heartbeat fire every 30s.
- stderr is drained on a helper thread, preventing pipe deadlock on chatty tools.
- dnsx 1.3 CNAME output (`host [CNAME] [target]`) is parsed correctly; takeover
  checks previously found zero candidates.
- The results table updates while httpx is still probing.

## [1.0.0] - 2026-10-31

### Added
- Package split: `recon/` (pipeline, runner, state, takeover, fingerprints, UI).
- httpx JSON parsing: status, title, technology stack, CNAME and optional screenshots.
- Resumable runs: per-run state in `runs/<id>/state.json`, pointer in `resume.cfg`.
- Run history: every run saves `results.json` and screenshots under `runs/<id>/`.
- Subdomain takeover checks for ~30 SaaS fingerprints (dangling CNAMEs).
- Results table, progress bar, JSON/CSV export, copy URLs, open screenshot.
- Test suite (pytest), CI workflow, developer docs and helper scripts.

### Fixed
- Commands are executed as argument lists instead of `shell=True` strings.
- DNS-resolved hosts are now also probed with httpx, not only used as subfinder roots.
- An interrupted dnsx chunk is retried after resuming instead of being skipped.

## [0.1.0] - 2026-10-30

### Added
- Initial single-file GUI (`recon_gui.py`): subfinder → httpx → dnsx recursion,
  status filtering, built-in wordlist, JSON export.
