"""Project-wide constants and paths.

Paths are anchored to the repository root so that ``runs/`` and
``resume.cfg`` live next to the launcher, regardless of the current
working directory.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = PROJECT_ROOT / "runs"
RESUME_FILE = PROJECT_ROOT / "resume.cfg"

SOFTWARE_NAME = "recon-gui"
VERSION = "1.1.0"

# Prefixes per dnsx invocation.
CHUNK = 400

# Seconds allowed for a takeover body fetch.
HTTP_TIMEOUT = 8

USER_AGENT = "Mozilla/5.0 (compatible; recon-gui)"

# Absolute tool locations tried first, then PATH.
TOOL_PATHS = {
    "subfinder": r"C:\Users\boser\go\bin\subfinder.exe",
    "httpx": r"C:\Users\boser\go\bin\httpx.exe",
    "dnsx": r"C:\Users\boser\go\bin\dnsx.exe",
}
