@echo off
chcp 65001 >nul
echo =====================================================================
echo   三国·逆天改命 - 家庭 AI 影视导演工作台 (Rust 全栈后台)
echo =====================================================================
if exist "target\release\director-server.exe" (
    "target\release\director-server.exe"
) else if exist "target\debug\director-server.exe" (
    "target\debug\director-server.exe"
) else (
    cargo run -p director-server
)
pause
