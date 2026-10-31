# Usage

## Controls

| Control | Meaning |
|---|---|
| **Target** | Apex/root domain, e.g. `example.com`. Only domains you own or are authorized to test. |
| **Cycles** | Maximum recursion depth. Cycle 1 enumerates the target; later cycles repeat discovery under newly found hosts. |
| **Status** | Comma-separated HTTP codes httpx keeps, e.g. `200,301,302,403`. |
| **subfinder -all** | Use all passive sources (`-all`), slower but broader. |
| **dnsx brute-force recursion** | Actively test wordlist prefixes under each live host. |
| **Screenshots** | `httpx -ss`; requires Chrome. |
| **Takeover check** | Run dangling-CNAME detection after the scan. |
| **Wordlist** | Optional file of prefixes. Empty = built-in list. |
| **Start / Resume / Stop** | Control the run. Stop is safe: state is written continuously. |
| **Export JSON / CSV** | Save the current table. |
| **Copy URLs / Copy selected** | Put URLs on the clipboard. |
| **Open screenshot** | Open the selected host's capture. |
| **Runs folder** | Open `runs/` in the file manager. |

## What happens during a run

1. **Passive**: subfinder runs once per unvisited root (the target, then any
   resolved names from brute force). Results are deduplicated.
2. **Probe**: every new hostname (plus the target in cycle 1) goes through
   httpx with `-json -title -td -cname -mc <codes>`.
3. **Active**: for each live host, wordlist prefixes are appended and tested
   with dnsx in chunks (`CHUNK = 400`). Resolved names are queued for the next
   cycle's probe.
4. **Repeat** until the cycle limit is reached or nothing new is found.
5. **Takeover check** over every discovered host (if enabled).
6. **Summary** in the log; results are written to `runs/<run_id>/results.json`.

## Reading the table

- **status** – HTTP status from httpx (or last probe for takeover-only rows).
- **host** – hostname.
- **title** – page title.
- **tech** – detected technologies (`httpx -td`).
- **takeover** – `LIKELY` / `POSSIBLE`, empty otherwise. Red rows are flagged.

Double-click a row to open `https://<host>` in the browser.

## Practical tips

- Keep `Cycles` low (2–3) on large domains; brute force grows geometrically.
- A small, targeted wordlist beats a huge one for recursion.
- If a run is slow, disable screenshots — they dominate runtime.
- Review the takeover output manually before reporting; the check is heuristic.

## Authorization

Use only on infrastructure you own or have explicit written permission to test.
See the notice in the [README](../README.md).
