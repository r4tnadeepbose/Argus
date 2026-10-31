#Requires -Version 5.1
<#
.SYNOPSIS
    Install the ProjectDiscovery tools used by Recon.
.DESCRIPTION
    Requires Go 1.21+. Installs subfinder, httpx and dnsx into %USERPROFILE%\go\bin,
    then reports the resolved paths.
#>
$ErrorActionPreference = "Stop"

if (-not (Get-Command go -ErrorAction SilentlyContinue)) {
    Write-Error "Go is not installed or not on PATH. Install Go 1.21+ first."
}

Write-Host "Installing ProjectDiscovery tools..." -ForegroundColor Cyan
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest

$bin = Join-Path $env:USERPROFILE "go\bin"
Write-Host "`nBinaries are in: $bin" -ForegroundColor Green
foreach ($tool in @("subfinder", "httpx", "dnsx")) {
    $exe = Join-Path $bin "$tool.exe"
    if (Test-Path $exe) {
        Write-Host "  [ok] $exe"
    } else {
        Write-Host "  [MISSING] $tool.exe" -ForegroundColor Yellow
    }
}

if (($env:Path -split ';') -notcontains $bin) {
    Write-Host "`nAdd it to PATH for this session:" -ForegroundColor Yellow
    Write-Host "  `$env:Path = `"$bin;`$env:Path`""
}
