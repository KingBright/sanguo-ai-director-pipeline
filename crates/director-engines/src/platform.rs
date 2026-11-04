use std::path::{Path, PathBuf};
use director_core::agent_plugin::which_in_path;

/// Resolves the Python 3 binary path dynamically across macOS, Linux, and Windows.
/// Priority order:
/// 1. `DIRECTOR_PYTHON_BIN` environment variable
/// 2. Workspace local virtualenv (`<workspace>/.venv/bin/python3` or `Scripts/python.exe`)
/// 3. User standard virtualenvs (`~/minimax/.venv`, `~/.venv`)
/// 4. System / Homebrew paths (`/opt/homebrew/bin/python3`, `/usr/local/bin/python3`, `/usr/bin/python3`)
/// 5. PATH search (`python3`, `python`)
pub fn resolve_python_bin(workspace_root: Option<&Path>) -> PathBuf {
    if let Ok(env_py) = std::env::var("DIRECTOR_PYTHON_BIN") {
        let p = PathBuf::from(env_py);
        if p.exists() {
            return p;
        }
    }

    if let Some(root) = workspace_root {
        let venv_unix = root.join(".venv").join("bin").join("python3");
        if venv_unix.exists() {
            return venv_unix;
        }
        let venv_unix_py = root.join(".venv").join("bin").join("python");
        if venv_unix_py.exists() {
            return venv_unix_py;
        }
        let venv_win = root.join(".venv").join("Scripts").join("python.exe");
        if venv_win.exists() {
            return venv_win;
        }
    }

    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .unwrap_or_default();
    let home_path = PathBuf::from(&home);

    let candidates = if cfg!(target_os = "windows") {
        vec![
            home_path.join("minimax").join(".venv").join("Scripts").join("python.exe"),
            home_path.join(".venv").join("Scripts").join("python.exe"),
            PathBuf::from("C:\\Users\\Liang\\minimax\\.venv\\Scripts\\python.exe"),
        ]
    } else {
        vec![
            home_path.join("minimax").join(".venv").join("bin").join("python3"),
            home_path.join("minimax").join(".venv").join("bin").join("python"),
            home_path.join(".venv").join("bin").join("python3"),
            home_path.join(".venv").join("bin").join("python"),
            PathBuf::from("/opt/homebrew/bin/python3"),
            PathBuf::from("/usr/local/bin/python3"),
            PathBuf::from("/usr/bin/python3"),
        ]
    };

    for cand in candidates {
        if cand.exists() {
            return cand;
        }
    }

    if let Some(p) = which_in_path("python3") {
        return p;
    }
    if let Some(p) = which_in_path("python") {
        return p;
    }

    PathBuf::from("python3")
}

/// Resolves the browser binary (Chrome, Edge, Chromium, Brave) across macOS, Linux, and Windows.
pub fn resolve_browser_bin() -> Option<PathBuf> {
    if let Ok(bin) = std::env::var("CHROME_BINARY") {
        let p = PathBuf::from(bin);
        if p.exists() {
            return Some(p);
        }
    }

    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .unwrap_or_default();
    let home_path = PathBuf::from(&home);

    #[cfg(target_os = "macos")]
    {
        let mac_candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ];
        for cand in mac_candidates {
            let p = PathBuf::from(cand);
            if p.exists() {
                return Some(p);
            }
        }
        let user_mac = home_path.join("Applications").join("Google Chrome.app").join("Contents/MacOS/Google Chrome");
        if user_mac.exists() {
            return Some(user_mac);
        }
    }

    #[cfg(target_os = "linux")]
    {
        for name in &["google-chrome", "chromium", "chromium-browser", "microsoft-edge", "brave-browser"] {
            if let Some(p) = which_in_path(name) {
                return Some(p);
            }
        }
        for cand in &["/usr/bin/google-chrome", "/usr/bin/chromium-browser", "/usr/bin/chromium", "/snap/bin/chromium"] {
            let p = PathBuf::from(cand);
            if p.exists() {
                return Some(p);
            }
        }
    }

    #[cfg(target_os = "windows")]
    {
        let local_app = std::env::var("LOCALAPPDATA").unwrap_or_default();
        let local_app_path = PathBuf::from(&local_app);
        let pw_candidates = [
            local_app_path.join("ms-playwright").join("chromium-1228").join("chrome-win64").join("chrome.exe"),
            local_app_path.join("ms-playwright").join("chromium-1155").join("chrome-win64").join("chrome.exe"),
        ];
        for cand in pw_candidates {
            if cand.exists() {
                return Some(cand);
            }
        }
        let win_candidates = [
            PathBuf::from("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"),
            PathBuf::from("C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"),
            PathBuf::from("C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"),
            PathBuf::from("C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"),
        ];
        for cand in win_candidates {
            if cand.exists() {
                return Some(cand);
            }
        }
    }

    // Generic fallback across any OS
    if let Some(p) = which_in_path("google-chrome") {
        return Some(p);
    }
    if let Some(p) = which_in_path("chrome") {
        return Some(p);
    }
    if let Some(p) = which_in_path("chromium") {
        return Some(p);
    }

    None
}

/// Resolves Google Colab CLI or MCP binary path across platforms.
pub fn resolve_colab_bin() -> Option<PathBuf> {
    if let Ok(colab_env) = std::env::var("COLAB_BIN") {
        let p = PathBuf::from(colab_env);
        if p.exists() {
            return Some(p);
        }
    }

    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .unwrap_or_default();
    let home_path = PathBuf::from(&home);

    let candidates = [
        home_path.join(".local").join("bin").join("colab"),
        home_path.join(".local").join("bin").join("colab-mcp"),
        PathBuf::from("/usr/local/bin/colab"),
        PathBuf::from("/opt/homebrew/bin/colab"),
    ];

    for cand in candidates {
        if cand.exists() {
            return Some(cand);
        }
    }

    if let Some(p) = which_in_path("colab") {
        return Some(p);
    }
    if let Some(p) = which_in_path("colab-mcp") {
        return Some(p);
    }

    None
}

/// Resolves Google Flow / gflow-cli credits cache path across platforms.
pub fn resolve_gflow_credits_cache() -> PathBuf {
    if let Ok(path) = std::env::var("GFLOW_CREDITS_CACHE") {
        let p = PathBuf::from(path);
        if p.exists() {
            return p;
        }
    }

    // Check workspace local fallbacks first if present
    if let Ok(cwd) = std::env::current_dir() {
        let mut dirs = vec![cwd.clone()];
        if let Some(p1) = cwd.parent() {
            dirs.push(p1.to_path_buf());
            if let Some(p2) = p1.parent() {
                dirs.push(p2.to_path_buf());
            }
        }
        for d in dirs {
            let ws_cache = d.join(".gflow_credits_cache.json");
            if ws_cache.exists() {
                return ws_cache;
            }
            let ws_direct = d.join("credits_cache.json");
            if ws_direct.exists() {
                return ws_direct;
            }
        }
    }
    let dot_fallback = PathBuf::from(".gflow_credits_cache.json");
    if dot_fallback.exists() {
        return dot_fallback;
    }

    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .unwrap_or_default();
    let home_path = PathBuf::from(&home);

    let candidates = if cfg!(target_os = "windows") {
        let local_app = std::env::var("LOCALAPPDATA").unwrap_or_default();
        vec![
            PathBuf::from(&local_app).join("ffroliva").join("gflow-cli").join("credits_cache.json"),
            home_path.join("AppData").join("Local").join("ffroliva").join("gflow-cli").join("credits_cache.json"),
        ]
    } else if cfg!(target_os = "macos") {
        vec![
            home_path.join("Library").join("Application Support").join("ffroliva").join("gflow-cli").join("credits_cache.json"),
            home_path.join(".config").join("gflow-cli").join("credits_cache.json"),
            home_path.join(".cache").join("gflow-cli").join("credits_cache.json"),
        ]
    } else {
        vec![
            home_path.join(".config").join("gflow-cli").join("credits_cache.json"),
            home_path.join(".cache").join("gflow-cli").join("credits_cache.json"),
        ]
    };

    for cand in &candidates {
        if cand.exists() {
            return cand.clone();
        }
    }

    candidates.into_iter().next().unwrap_or_else(|| PathBuf::from("credits_cache.json"))
}
