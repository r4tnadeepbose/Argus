# Troubleshooting

## "subfinder and/or httpx not found"

The app prints a **Preflight** section in the log with resolved paths.

1. Check that the binaries exist.
2. Set absolute paths in `TOOL_PATHS` (`recon/constants.py`).
3. On Linux/macOS ensure `$(go env GOPATH)/bin` is on `PATH`.
4. Restart the app after changing the environment.

## The window does not open

- Confirm Tkinter: `python -c "import tkinter; print(tkinter.TkVersion)"`.
- On Linux install `python3-tk`; run from a graphical session, not a bare SSH
  shell.
- If you use a Python from the Microsoft Store, try the python.org installer.

## The scan looks stuck after "httpx ... host(s)"

httpx processes hosts concurrently but large inputs (10k+ hosts) still take
minutes. Since 1.0.1 the log shows:

- `[httpx] [0:00:10] | RPS: ... | Requests: N | Hosts: x/y (z%)` every ~10s,
- `[live] https://host [200]` lines as hosts are confirmed,
- `[i] httpx ... still running (30s)` every 30 seconds.

If those lines appear, it is working. To make runs faster: disable screenshots,
lower **Cycles**, use a smaller wordlist, or reduce the host set.

dnsx brute force only starts after httpx finishes. Its own progress appears per
chunk (`dnsx 400 under api.example.com`), followed by `[+] N new resolved`.

## No hosts are found

- Check the target spelling (apex domain only, e.g. `example.com`).
- Confirm `subfinder` works by itself, then `httpx`.
- Subfinder sources may be rate-limited; try again or check its config.
- The status filter may be too narrow — start with `200,301,302,403`.

## Screenshots are missing

- `httpx -ss` needs Chrome/Chromium. Install it, or disable **Screenshots**.
- If Chrome is present but httpx cannot find it, use httpx's
  `-chrome`/browser flags manually to verify your installation.

## Takeover column is empty

- `dnsx` must be available for the full CNAME pass; without it only httpx CNAMEs
  are checked.
- Not every CNAME service is covered; see
  [takeover-checks.md](takeover-checks.md) to add fingerprints.

## Resume is disabled after a stop

- `resume.cfg` must contain a `run_id` and the matching
  `runs/<run_id>/state.json` must exist.
- A run that finished cleanly is marked `status=finished` and cannot be resumed.
- Legacy `resume.cfg` files (only `resume_from`/`index`) are ignored by design.

## A resumed run seems to skip hosts

- The cursor is the per-host wordlist position. If you stopped mid-chunk, that
  chunk is retried — hosts already probed are not repeated.
- If you edited the wordlist after stopping, the embedded copy is used.

## The GUI freezes

All scanning runs in a worker thread, so the window should stay responsive. If
it does not, check the log for a very large httpx/dnsx output burst. Report the
steps and the tool versions.

## Log shows `[stderr]` lines

Often harmless (progress or warning messages). If a command fails, the relevant
`[error]` line is printed directly above.

## Everything is slow

- Disable screenshots.
- Lower **Cycles**.
- Use a smaller, targeted wordlist.
- Expect large lists (thousands of prefixes × many hosts) to take time.

## Still stuck?

Open an issue using the bug template and include OS, Python version, tool
versions and sanitized log lines. Do not post real hostnames or internal data.
