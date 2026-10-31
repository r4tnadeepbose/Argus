# Resume and Run History

## Why it exists

Brute forcing can take a long time. Recon writes enough state to continue a run
after **Stop**, a crash, or a closed window.

## Files

```
runs/
└── 20261031_141153/
    ├── state.json        # full resumable state
    ├── results.json      # results snapshot (written at the end / after stop)
    └── screenshots/      # httpx -ss output
resume.cfg                # pointer to the unfinished run
```

`resume.cfg` is intentionally human-readable:

```
run_id=20261031_141153
domain=example.com
cycle=2
resume_from=api.example.com
index=0
status=running
updated_at=2026-10-31T14:12:15
```

- `resume_from` is the live host currently being brute-forced.
- `index` is the position in the **per-host wordlist** (chunk cursor).
- `status=finished` disables **Resume** for completed runs.

## What is persisted

`state.json` contains the cycle, phase (`passive`/`brute`), current parent list,
live-host list, cursor, seen roots/hosts, probed hosts, pending probes, partial
results and takeover findings. The wordlist itself is embedded so resuming
still works if the file later changes.

## Resume guarantees

- A stop **before** a dnsx call re-runs that chunk on resume.
- A stop **mid-chunk** (process killed) also re-runs that chunk: the cursor is
  only advanced after the call completes and the run is still active.
- Hosts found in earlier cycles are not re-probed.
- Already-found takeover verdicts are preserved.

## Limitations

- If the tool binaries change version between stop and resume, results may
  differ.
- The state is not encrypted; it contains hostnames and page titles.
- Legacy `resume.cfg` files without a `run_id` are ignored (the app logs a note).

## Cleaning up

Delete a run directory to free space; **Resume** then reports no state. To
disable resume entirely, delete `resume.cfg` and the `runs/` directory.
