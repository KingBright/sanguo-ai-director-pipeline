#!/usr/bin/env bash
# ==============================================================================
# Cross-Platform Director Service Manager (macOS & Linux)
# Port: 18443 | Service: director-server
# Supports: --daemon, --status, --stop, --restart, --gen-launchd, --gen-systemd
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PORT="${DIRECTOR_PORT:-18443}"
PID_FILE="${WORKSPACE_ROOT}/.director_server.pid"
LOG_FILE="${WORKSPACE_ROOT}/.director_server.log"

OS_TYPE="$(uname -s)"

find_binary() {
    # Check custom binary env var
    if [[ -n "${DIRECTOR_BIN:-}" && -x "${DIRECTOR_BIN}" ]]; then
        echo "${DIRECTOR_BIN}"
        return 0
    fi

    # Check release target
    if [[ -x "${WORKSPACE_ROOT}/target/release/director-server" ]]; then
        echo "${WORKSPACE_ROOT}/target/release/director-server"
        return 0
    fi

    # Check rust-target release directory if configured
    if [[ -x "${HOME}/rust-target/release/director-server" ]]; then
        echo "${HOME}/rust-target/release/director-server"
        return 0
    fi

    # Check debug target
    if [[ -x "${WORKSPACE_ROOT}/target/debug/director-server" ]]; then
        echo "${WORKSPACE_ROOT}/target/debug/director-server"
        return 0
    fi

    if [[ -x "${HOME}/rust-target/debug/director-server" ]]; then
        echo "${HOME}/rust-target/debug/director-server"
        return 0
    fi

    # Auto build release
    echo "⚠️ 未检测到预编译的 director-server，正在自动执行 cargo build --release..." >&2
    (cd "${WORKSPACE_ROOT}" && cargo build --release --bin director-server) >&2

    if [[ -x "${WORKSPACE_ROOT}/target/release/director-server" ]]; then
        echo "${WORKSPACE_ROOT}/target/release/director-server"
        return 0
    fi
    if [[ -x "${HOME}/rust-target/release/director-server" ]]; then
        echo "${HOME}/rust-target/release/director-server"
        return 0
    fi

    echo "❌ 无法找到或编译 director-server 可执行文件！" >&2
    exit 1
}

get_running_pid() {
    if [[ -f "${PID_FILE}" ]]; then
        local pid
        pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
        if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
            echo "${pid}"
            return 0
        fi
    fi
    # Check port via lsof
    if command -v lsof >/dev/null 2>&1; then
        local port_pid
        port_pid="$(lsof -ti tcp:"${PORT}" -sTCP:LISTEN 2>/dev/null | head -n1 || true)"
        if [[ -n "${port_pid}" ]]; then
            echo "${port_pid}"
            return 0
        fi
    fi
    return 1
}

cmd_status() {
    if pid="$(get_running_pid)"; then
        echo "🟢 [RUNNING] Director Studio 服务正在运行 (PID: ${pid}, Port: ${PORT})"
        echo "   Web 访问地址: http://127.0.0.1:${PORT}"
        echo "   日志文件: ${LOG_FILE}"
        return 0
    else
        echo "⚪ [STOPPED] Director Studio 服务未在运行 (Port: ${PORT} 空闲)"
        return 1
    fi
}

cmd_stop() {
    if pid="$(get_running_pid)"; then
        echo "🛑 正在停止 Director Studio 服务 (PID: ${pid})..."
        kill -TERM "${pid}" 2>/dev/null || true
        for _ in {1..20}; do
            if ! kill -0 "${pid}" 2>/dev/null; then
                rm -f "${PID_FILE}"
                echo "✅ Director Studio 服务已成功停止。"
                return 0
            fi
            sleep 0.25
        done
        echo "⚠️ 进程未响应 SIGTERM，强制执行 SIGKILL..."
        kill -9 "${pid}" 2>/dev/null || true
        rm -f "${PID_FILE}"
        echo "✅ 服务已强制终止。"
    else
        echo "ℹ️ Director Studio 服务当前未在运行。"
        rm -f "${PID_FILE}"
    fi
}

cmd_start() {
    local daemon_mode="${1:-0}"
    if pid="$(get_running_pid)"; then
        echo "⚠️ 服务已在运行中 (PID: ${pid}, Port: ${PORT})，无需重复启动。"
        echo "   如需重启，请运行: $0 --restart"
        return 0
    fi

    local bin_path
    bin_path="$(find_binary)"
    export DIRECTOR_PORT="${PORT}"
    export DIRECTOR_WORKSPACE="${WORKSPACE_ROOT}"

    if [[ "${daemon_mode}" -eq 1 ]]; then
        echo "🚀 正在以后台守护进程模式启动 Director Studio 服务..."
        echo "   可执行文件: ${bin_path}"
        echo "   工作区根目录: ${WORKSPACE_ROOT}"
        echo "   端口: ${PORT}"
        nohup "${bin_path}" > "${LOG_FILE}" 2>&1 &
        local new_pid=$!
        echo "${new_pid}" > "${PID_FILE}"
        sleep 1.0

        if kill -0 "${new_pid}" 2>/dev/null; then
            echo "✅ 服务后台启动成功 (PID: ${new_pid})！"
            echo "   Web 控制台: http://127.0.0.1:${PORT}"
            echo "   实时日志跟踪: tail -f \"${LOG_FILE}\""
        else
            echo "❌ 服务启动失败，最近日志输出："
            tail -n 25 "${LOG_FILE}" || true
            exit 1
        fi
    else
        echo "🎬 正在前台启动 Director Studio 服务 (Ctrl+C 终止)..."
        echo "   Web 控制台: http://127.0.0.1:${PORT}"
        exec "${bin_path}"
    fi
}

cmd_gen_launchd() {
    local plist_dir="${HOME}/Library/LaunchAgents"
    local plist_file="${plist_dir}/fun.hackerlife.director.plist"
    local bin_path
    bin_path="$(find_binary)"

    mkdir -p "${plist_dir}"
    cat > "${plist_file}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>fun.hackerlife.director</string>
    <key>ProgramArguments</key>
    <array>
        <string>${bin_path}</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>DIRECTOR_PORT</key>
        <string>${PORT}</string>
        <key>DIRECTOR_WORKSPACE</key>
        <string>${WORKSPACE_ROOT}</string>
    </dict>
    <key>WorkingDirectory</key>
    <string>${WORKSPACE_ROOT}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${WORKSPACE_ROOT}/.director_server.launchd.log</string>
    <key>StandardErrorPath</key>
    <string>${WORKSPACE_ROOT}/.director_server.launchd.log</string>
</dict>
</plist>
EOF

    echo "✅ 已成功生成 macOS launchd 守护配置文件: ${plist_file}"
    echo "   载入自启服务: launchctl load -w \"${plist_file}\""
    echo "   卸载自启服务: launchctl unload -w \"${plist_file}\""
}

cmd_gen_systemd() {
    local service_dir="${HOME}/.config/systemd/user"
    local service_file="${service_dir}/director-server.service"
    local bin_path
    bin_path="$(find_binary)"

    mkdir -p "${service_dir}"
    cat > "${service_file}" <<EOF
[Unit]
Description=Sanguo AI Director Server & MCP Hub
After=network.target

[Service]
Type=simple
WorkingDirectory=${WORKSPACE_ROOT}
Environment=DIRECTOR_PORT=${PORT}
Environment=DIRECTOR_WORKSPACE=${WORKSPACE_ROOT}
ExecStart=${bin_path}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

    echo "✅ 已成功生成 Linux systemd 用户级服务文件: ${service_file}"
    echo "   启动与开机自启命令:"
    echo "   systemctl --user daemon-reload"
    echo "   systemctl --user enable --now director-server.service"
    echo "   systemctl --user status director-server.service"
}

# ------------------------------------------------------------------------------
# Argument Routing
# ------------------------------------------------------------------------------
case "${1:-}" in
    --daemon|-d)
        cmd_start 1
        ;;
    --status|-s)
        cmd_status
        ;;
    --stop)
        cmd_stop
        ;;
    --restart)
        cmd_stop
        sleep 0.5
        cmd_start 1
        ;;
    --gen-launchd)
        cmd_gen_launchd
        ;;
    --gen-systemd)
        cmd_gen_systemd
        ;;
    --help|-h)
        cat <<EOF
Director Studio Cross-Platform Service Manager (macOS & Linux)
用法: $0 [选项]

选项:
  --daemon, -d       在后台守护进程模式运行服务 (记录 PID 并输出到 .director_server.log)
  --status, -s       检查当前服务运行状态与端口监听
  --stop             停止当前正在运行的后台服务
  --restart          重启后台服务
  --gen-launchd      生成 macOS launchd 用户级开机自启配置文件 (~/Library/LaunchAgents/)
  --gen-systemd      生成 Linux systemd 用户级服务配置文件 (~/.config/systemd/user/)
  --help, -h         显示帮助信息

环境变量:
  DIRECTOR_PORT      服务监听端口 (默认: 18443)
  DIRECTOR_WORKSPACE 项目工作区根目录 (默认: 脚本父目录)
  DIRECTOR_BIN       自定义可执行文件路径
EOF
        ;;
    *)
        cmd_start 0
        ;;
esac
