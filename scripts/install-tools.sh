#!/usr/bin/env bash
# Install the ProjectDiscovery tools used by Recon (requires Go 1.21+).
set -euo pipefail

if ! command -v go >/dev/null 2>&1; then
    echo "[!] Go is not installed or not on PATH. Install Go 1.21+ first." >&2
    exit 1
fi

echo "[*] Installing ProjectDiscovery tools..."
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest

GOBIN="$(go env GOPATH)/bin"
echo
echo "[+] Binaries are in: $GOBIN"
for tool in subfinder httpx dnsx; do
    if [ -x "$GOBIN/$tool" ]; then
        echo "  [ok] $GOBIN/$tool"
    else
        echo "  [MISSING] $GOBIN/$tool"
    fi
done

case ":$PATH:" in
    *":$GOBIN:"*) ;;
    *) echo; echo "[i] Add it to PATH: export PATH=\"$GOBIN:\$PATH\"" ;;
esac
