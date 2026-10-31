# Contributing

Thanks for improving Argus.

## Ground rules

- Only test against domains you own or are authorized to test. Contributions
  that add evasion, mass-targeting or credential-harvesting features will be
  rejected.
- Keep the runtime dependency-free (standard library only). External binaries
  (`subfinder`, `httpx`, `dnsx`) are expected to exist on the system.
- UI code must not perform network or subprocess work on the Tk main thread.

## Workflow

1. Fork and create a topic branch: `git checkout -b feature/my-change`.
2. Make the change, keeping it focused.
3. Add or update tests under `tests/`.
4. Run the checks:

   ```bash
   python -m pytest
   ruff check .
   ```

5. Open a pull request describing the change and how you tested it. UI changes
   should include a screenshot or a short description of manual testing.

## Code style

- Python 3.10+, type hints on public functions.
- Line length 100; lint rules live in `pyproject.toml`.
- Prefer small modules with one responsibility (see `docs/architecture.md`).

## Reporting bugs

Use the issue templates in `.github/ISSUE_TEMPLATE/`. Include the OS, Python
version, the target type (owned/lab/bug-bounty), and the relevant log lines.
Redact any sensitive hostnames before posting.

## Security issues

Do not open a public issue. Follow [SECURITY.md](SECURITY.md).
