# SPDX-License-Identifier: MIT
# One-click upgrade to Microsoft WSL 3.0.3 (and configure optimal .wslconfig for AMD Ryzen AI Max+ 395)

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "==> Requesting Administrator privileges to register WSL 3.0.3 system service..." -ForegroundColor Cyan
    Start-Process powershell.exe -Verb RunAs -Wait -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    wsl --version
    exit $LASTEXITCODE
}

$bundle = "C:\Users\Liang\AppData\Local\Temp\Microsoft.WSL_3.0.3.0_x64_ARM64.msixbundle"
if (-not (Test-Path $bundle)) {
    throw "Installer not found at $bundle"
}

Write-Host "==> Shutting down any running WSL instances..." -ForegroundColor Cyan
wsl --shutdown

Write-Host "==> Installing Microsoft WSL 3.0.3.0 (678.91 MB)..." -ForegroundColor Cyan
Add-AppxPackage -Path $bundle -ForceApplicationShutdown

Write-Host "==> Upgrade completed! Current WSL version:" -ForegroundColor Green
wsl --version
Read-Host "Press Enter to close this window"
