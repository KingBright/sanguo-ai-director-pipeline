# Director Studio 独立常驻守护脚本 (脱离 Antigravity Agent 进程树)
$WorkDir = "c:\Users\Liang\Downloads\sanguo"
$ExePath = "c:\Users\Liang\Downloads\sanguo\target\release\director-server.exe"
$LogFile = "c:\Users\Liang\Downloads\sanguo\output\director-server-standalone.log"

Set-Location $WorkDir
$env:DIRECTOR_PORT = "18443"
$env:DIRECTOR_PASSWORD = "duanshipin123"
$env:DIRECTOR_ADMIN_PIN = "2280"

while ($true) {
    $proc = Get-Process -Name "director-server" -ErrorAction SilentlyContinue
    if (-not $proc) {
        $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content -Path $LogFile -Value "[$ts] Starting standalone director-server.exe..."
        Start-Process -FilePath $ExePath -WorkingDirectory $WorkDir -WindowStyle Hidden
    }
    Start-Sleep -Seconds 5
}
