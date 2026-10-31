# Installation

## 1. Python

Recon needs **Python 3.10 or newer** with Tkinter.

- **Windows**: install from python.org and enable *Add Python to PATH*. Tkinter
  is included in the official installer.
- **Ubuntu / Debian**: `sudo apt install python3 python3-venv python3-tk`
- **Fedora**: `sudo dnf install python3 python3-tkinter`
- **Arch**: `sudo pacman -S python tk`

Verify:

```bash
python -c "import tkinter; print(tkinter.TkVersion)"
```

## 2. ProjectDiscovery tools

Install with Go (1.21+), or download release binaries.

```bash
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest
```

On Windows the binaries land in `%USERPROFILE%\go\bin`; on Linux/macOS in
`$(go env GOPATH)/bin`, which must be on `PATH`.

Verify:

```bash
subfinder -version
httpx -version
dnsx -version
```

### Screenshots (optional)

`httpx -ss` requires a Chrome/Chromium installation. If it is missing, disable
the **Screenshots** checkbox; everything else still works.

## 3. Configure tool locations

Recon first checks absolute paths in [`recon/constants.py`](../recon/constants.py)
(`TOOL_PATHS`), then `PATH`. Edit the paths if your binaries live elsewhere:

```python
TOOL_PATHS = {
    "subfinder": r"C:\Users\you\go\bin\subfinder.exe",
    "httpx":     r"C:\Users\you\go\bin\httpx.exe",
    "dnsx":      r"C:\Users\you\go\bin\dnsx.exe",
}
```

## 4. Run Recon

No Python packages are required:

```bash
python recon_gui.py
# or
python -m recon
```

Optionally install it as a console script:

```bash
python -m pip install -e .
recon-gui
```

## 5. Developer setup

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```
