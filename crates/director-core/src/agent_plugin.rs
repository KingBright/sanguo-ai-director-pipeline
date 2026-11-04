use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::time::Instant;

use serde::{Deserialize, Serialize};
use tracing::{debug, info, warn};

pub const DEFAULT_ANTIGRAVITY_CONVERSATION_ID: &str = "e2e3111c-e08d-41d4-8bec-b19c04139f88";

/// Represents an Agent Plugin Manifest for invoking local or remote AI agents.
/// Fully serializable/deserializable from JSON and TOML files.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentPluginManifest {
    pub id: String,
    pub name: String,
    /// Plugin kind: "antigravity", "codex", "claude_code", "gemini_cli", "openai_http", "custom_cli"
    pub kind: String,
    #[serde(default)]
    pub command: Option<String>,
    #[serde(default)]
    pub args_template: Vec<String>,
    #[serde(default)]
    pub env: BTreeMap<String, String>,
    #[serde(default)]
    pub http_endpoint: Option<String>,
    #[serde(default)]
    pub capabilities: Vec<String>,
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default = "default_priority")]
    pub priority: i32,
    #[serde(default)]
    pub os_targets: Vec<String>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub model: Option<String>,
}

fn default_true() -> bool {
    true
}

fn default_priority() -> i32 {
    50
}

impl AgentPluginManifest {
    pub fn is_available_on_current_os(&self) -> bool {
        if self.os_targets.is_empty() {
            return true;
        }
        let current = current_os();
        self.os_targets.iter().any(|t| t == current || t == "all")
    }

    pub fn check_binary_exists(&self) -> bool {
        if let Some(cmd) = &self.command {
            if cmd.is_empty() {
                return false;
            }
            let p = Path::new(cmd);
            if p.is_absolute() {
                return p.is_file();
            }
            which_in_path(cmd).is_some()
        } else {
            // For HTTP plugins, binary check is not required
            self.http_endpoint.is_some()
        }
    }
}

/// Request to dispatch a creative directing or editing task to an AI agent.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentTaskRequest {
    /// "expand_micro_acting" | "decompose_storyboard" | "demand_dispatch" | "polish_scene"
    pub task_type: String,
    pub prompt: String,
    #[serde(default)]
    pub workspace_dir: Option<String>,
    #[serde(default)]
    pub preferred_plugin: Option<String>,
    #[serde(default)]
    pub conversation_id: Option<String>,
    #[serde(default)]
    pub extra_context: Option<serde_json::Value>,
}

/// Response returned by the agent invocation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentTaskResponse {
    pub plugin_id: String,
    /// "success" | "fallback" | "error"
    pub status: String,
    pub output: String,
    pub elapsed_ms: u64,
    pub os_platform: String,
}

/// Returns the current operating system identifier: "macos", "linux", "windows", or "unknown".
pub fn current_os() -> &'static str {
    if cfg!(target_os = "macos") {
        "macos"
    } else if cfg!(target_os = "linux") {
        "linux"
    } else if cfg!(target_os = "windows") {
        "windows"
    } else {
        "unknown"
    }
}

/// Checks if a binary command is executable or exists on PATH (plus standard user/system bin dirs).
pub fn which_in_path(bin_name: &str) -> Option<PathBuf> {
    let mut search_dirs: Vec<PathBuf> = Vec::new();
    if let Ok(paths) = std::env::var("PATH") {
        let separator = if cfg!(target_os = "windows") { ';' } else { ':' };
        for dir in paths.split(separator).filter(|d| !d.is_empty()) {
            search_dirs.push(PathBuf::from(dir));
        }
    }
    if let Ok(home) = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")) {
        let hp = PathBuf::from(home);
        search_dirs.push(hp.join(".local").join("bin"));
        search_dirs.push(hp.join(".cargo").join("bin"));
        search_dirs.push(hp.join(".dsh").join("bin"));
    }
    #[cfg(not(target_os = "windows"))]
    {
        search_dirs.push(PathBuf::from("/opt/homebrew/bin"));
        search_dirs.push(PathBuf::from("/usr/local/bin"));
    }
    for dir in search_dirs {
        let p = dir.join(bin_name);
        if p.is_file() {
            return Some(p);
        }
        #[cfg(target_os = "windows")]
        {
            for ext in ["exe", "cmd", "bat"] {
                let with_ext = dir.join(format!("{}.{}", bin_name, ext));
                if with_ext.is_file() {
                    return Some(with_ext);
                }
            }
        }
    }
    None
}

/// Cross-platform dynamic agent plugin registry.
/// Automatically discovers built-in adapters (Antigravity, Codex, Claude Code, Gemini CLI, Colab, OpenAI/Ollama)
/// and loads dynamic plugin manifests from `<workspace>/plugins/agents/*.toml` and `*.json`.
#[derive(Debug, Clone)]
pub struct AgentPluginRegistry {
    plugins: BTreeMap<String, AgentPluginManifest>,
}

impl Default for AgentPluginRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl AgentPluginRegistry {
    /// Creates a new registry and auto-discovers all built-in cross-platform adapters.
    pub fn new() -> Self {
        let mut reg = Self {
            plugins: BTreeMap::new(),
        };
        reg.discover_builtin_adapters();
        reg
    }

    /// Discovers built-in cross-platform adapters on macOS, Linux, and Windows.
    pub fn discover_builtin_adapters(&mut self) {
        let _os = current_os();
        let home = std::env::var("HOME")
            .or_else(|_| std::env::var("USERPROFILE"))
            .unwrap_or_default();
        let home_path = PathBuf::from(&home);

        // 1. Antigravity Adapter
        let mut antigravity_bin = None;
        if let Ok(bin_env) = std::env::var("ANTIGRAVITY_BIN") {
            let p = PathBuf::from(bin_env);
            if p.exists() {
                antigravity_bin = Some(p);
            }
        }
        if antigravity_bin.is_none() {
            let candidates = if cfg!(target_os = "windows") {
                vec![
                    home_path.join(".gemini").join("antigravity").join("bin").join("agentapi.bat"),
                    home_path.join(".gemini").join("antigravity-ide").join("bin").join("agentapi.bat"),
                    home_path.join(".gemini").join("antigravity").join("bin").join("agentapi.exe"),
                    PathBuf::from("C:\\Users\\Liang\\.gemini\\antigravity\\bin\\agentapi.bat"),
                ]
            } else {
                vec![
                    home_path.join(".gemini").join("antigravity").join("bin").join("agentapi"),
                    home_path.join(".gemini").join("antigravity-ide").join("bin").join("agentapi"),
                    home_path.join(".dsh").join("bin").join("dsh"),
                    home_path.join(".dsh").join("bin").join("agentapi"),
                    PathBuf::from("/Applications/DeepSeek Harness.app/Contents/Resources/app.asar/dsh/bin/dsh"),
                    PathBuf::from("/Applications/DeepSeek Harness.app/Contents/Resources/app.asar/dsh"),
                ]
            };
            for cand in candidates {
                if cand.is_file() {
                    antigravity_bin = Some(cand);
                    break;
                }
            }
            if antigravity_bin.is_none() {
                if let Some(p) = which_in_path("agentapi") {
                    antigravity_bin = Some(p);
                } else if let Some(p) = which_in_path("dsh") {
                    antigravity_bin = Some(p);
                }
            }
        }

        let antigravity_manifest = AgentPluginManifest {
            id: "antigravity".to_string(),
            name: "Google Antigravity Agent (AgentAPI / DSH)".to_string(),
            kind: "antigravity".to_string(),
            command: antigravity_bin.map(|p| p.to_string_lossy().to_string()),
            args_template: vec![
                "send-message".to_string(),
                "--title".to_string(),
                "AI Director Dispatch".to_string(),
                "{conversation_id}".to_string(),
                "{prompt}".to_string(),
            ],
            env: BTreeMap::new(),
            http_endpoint: None,
            capabilities: vec![
                "expand_micro_acting".to_string(),
                "decompose_storyboard".to_string(),
                "demand_dispatch".to_string(),
                "polish_scene".to_string(),
            ],
            enabled: true,
            priority: 100,
            os_targets: vec!["macos".to_string(), "linux".to_string(), "windows".to_string()],
            description: Some("Direct integration with Google Antigravity & DeepSeek Harness AgentAPI bridge".to_string()),
            model: Some("gemini-4-argon".to_string()),
        };
        self.register_plugin(antigravity_manifest);

        // 2. OpenAI Codex CLI Adapter
        let mut codex_bin = which_in_path("codex");
        if codex_bin.is_none() {
            let candidates = if cfg!(target_os = "windows") {
                let appdata = std::env::var("APPDATA").unwrap_or_default();
                vec![
                    PathBuf::from(&appdata).join("npm").join("codex.cmd"),
                    PathBuf::from(&appdata).join("npm").join("codex"),
                ]
            } else {
                vec![
                    PathBuf::from("/opt/homebrew/bin/codex"),
                    PathBuf::from("/usr/local/bin/codex"),
                    home_path.join(".local").join("bin").join("codex"),
                ]
            };
            for cand in candidates {
                if cand.exists() {
                    codex_bin = Some(cand);
                    break;
                }
            }
        }

        let codex_manifest = AgentPluginManifest {
            id: "codex".to_string(),
            name: "OpenAI Codex CLI Agent".to_string(),
            kind: "codex".to_string(),
            command: codex_bin.map(|p| p.to_string_lossy().to_string()),
            args_template: vec![
                "exec".to_string(),
                "--skip-git-repo-check".to_string(),
                "{prompt}".to_string(),
            ],
            env: BTreeMap::new(),
            http_endpoint: None,
            capabilities: vec![
                "expand_micro_acting".to_string(),
                "decompose_storyboard".to_string(),
                "demand_dispatch".to_string(),
                "polish_scene".to_string(),
            ],
            enabled: true,
            priority: 90,
            os_targets: vec!["macos".to_string(), "linux".to_string(), "windows".to_string()],
            description: Some("OpenAI Codex autonomous coding & creative scripting CLI adapter".to_string()),
            model: Some("gpt-5-codex".to_string()),
        };
        self.register_plugin(codex_manifest);

        // 3. Claude Code CLI Adapter
        let mut claude_bin = which_in_path("claude");
        if claude_bin.is_none() {
            let candidates = if cfg!(target_os = "windows") {
                let appdata = std::env::var("APPDATA").unwrap_or_default();
                vec![
                    PathBuf::from(&appdata).join("npm").join("claude.cmd"),
                    PathBuf::from(&appdata).join("npm").join("claude"),
                ]
            } else {
                vec![
                    PathBuf::from("/opt/homebrew/bin/claude"),
                    PathBuf::from("/usr/local/bin/claude"),
                    home_path.join(".local").join("bin").join("claude"),
                ]
            };
            for cand in candidates {
                if cand.exists() {
                    claude_bin = Some(cand);
                    break;
                }
            }
        }

        let claude_manifest = AgentPluginManifest {
            id: "claude-code".to_string(),
            name: "Anthropic Claude Code CLI Agent".to_string(),
            kind: "claude_code".to_string(),
            command: claude_bin.map(|p| p.to_string_lossy().to_string()),
            args_template: vec!["-p".to_string(), "{prompt}".to_string()],
            env: BTreeMap::new(),
            http_endpoint: None,
            capabilities: vec![
                "expand_micro_acting".to_string(),
                "decompose_storyboard".to_string(),
                "demand_dispatch".to_string(),
                "polish_scene".to_string(),
            ],
            enabled: true,
            priority: 85,
            os_targets: vec!["macos".to_string(), "linux".to_string(), "windows".to_string()],
            description: Some("Anthropic Claude Code interactive & non-interactive agent runner".to_string()),
            model: Some("claude-3-7-sonnet".to_string()),
        };
        self.register_plugin(claude_manifest);

        // 4. Gemini CLI Adapter
        let mut gemini_bin = which_in_path("gemini");
        if gemini_bin.is_none() {
            let candidates = vec![
                PathBuf::from("/opt/homebrew/bin/gemini"),
                PathBuf::from("/usr/local/bin/gemini"),
                home_path.join(".local").join("bin").join("gemini"),
            ];
            for cand in candidates {
                if cand.exists() {
                    gemini_bin = Some(cand);
                    break;
                }
            }
        }

        let gemini_manifest = AgentPluginManifest {
            id: "gemini-cli".to_string(),
            name: "Google Gemini CLI Agent".to_string(),
            kind: "gemini_cli".to_string(),
            command: gemini_bin.map(|p| p.to_string_lossy().to_string()),
            args_template: vec!["-p".to_string(), "{prompt}".to_string()],
            env: BTreeMap::new(),
            http_endpoint: None,
            capabilities: vec![
                "expand_micro_acting".to_string(),
                "decompose_storyboard".to_string(),
                "polish_scene".to_string(),
            ],
            enabled: true,
            priority: 80,
            os_targets: vec!["macos".to_string(), "linux".to_string(), "windows".to_string()],
            description: Some("Official Google Gemini CLI developer runner".to_string()),
            model: Some("gemini-2.5-pro".to_string()),
        };
        self.register_plugin(gemini_manifest);

        // 5. Colab Operator / Workstation Adapter
        let mut colab_bin = which_in_path("colab");
        if colab_bin.is_none() {
            let candidates = vec![
                home_path.join(".local").join("bin").join("colab"),
                home_path.join(".local").join("bin").join("colab-mcp"),
            ];
            for cand in candidates {
                if cand.exists() {
                    colab_bin = Some(cand);
                    break;
                }
            }
        }

        let colab_manifest = AgentPluginManifest {
            id: "colab-operator".to_string(),
            name: "Google Colab Ultra Cloud GPU Operator".to_string(),
            kind: "custom_cli".to_string(),
            command: colab_bin.map(|p| p.to_string_lossy().to_string()),
            args_template: vec!["run".to_string(), "{prompt}".to_string()],
            env: BTreeMap::new(),
            http_endpoint: None,
            capabilities: vec![
                "cloud_gpu_dispatch".to_string(),
                "demand_dispatch".to_string(),
                "tts_generation".to_string(),
                "video_generation".to_string(),
            ],
            enabled: true,
            priority: 70,
            os_targets: vec!["macos".to_string(), "linux".to_string(), "windows".to_string()],
            description: Some("Dispatches high-compute AI video and voice tasks to remote Colab GPU instances".to_string()),
            model: Some("colab-a100-l4".to_string()),
        };
        self.register_plugin(colab_manifest);

        // 6. OpenAI / Ollama HTTP Endpoint Adapter
        let http_url = std::env::var("DIRECTOR_LLM_URL")
            .or_else(|_| std::env::var("OPENAI_BASE_URL"))
            .ok()
            .filter(|u| !u.trim().is_empty());

        let openai_manifest = AgentPluginManifest {
            id: "openai-http".to_string(),
            name: "Universal OpenAI / Ollama HTTP LLM".to_string(),
            kind: "openai_http".to_string(),
            command: None,
            args_template: vec![],
            env: BTreeMap::new(),
            http_endpoint: http_url.or_else(|| Some("http://127.0.0.1:11434/v1".to_string())),
            capabilities: vec![
                "expand_micro_acting".to_string(),
                "decompose_storyboard".to_string(),
                "polish_scene".to_string(),
            ],
            enabled: true,
            priority: 60,
            os_targets: vec!["macos".to_string(), "linux".to_string(), "windows".to_string()],
            description: Some("Compatible OpenAI/v1/chat/completions endpoint for local Ollama, vLLM, or commercial APIs".to_string()),
            model: std::env::var("DIRECTOR_LLM_MODEL").ok().or_else(|| Some("qwen2.5:32b".to_string())),
        };
        self.register_plugin(openai_manifest);
    }

    /// Registers or updates a plugin manifest in the registry, preserving auto-discovered binary paths
    /// when a declarative TOML/JSON manifest leaves `command` empty or uses a bare binary name.
    pub fn register_plugin(&mut self, mut manifest: AgentPluginManifest) {
        let cmd_empty = manifest
            .command
            .as_deref()
            .map(|s| s.trim().is_empty())
            .unwrap_or(true);
        if cmd_empty {
            if let Some(existing) = self.plugins.get(&manifest.id) {
                if existing
                    .command
                    .as_deref()
                    .map(|s| !s.trim().is_empty())
                    .unwrap_or(false)
                {
                    manifest.command = existing.command.clone();
                }
            }
        } else if let Some(cmd) = manifest.command.clone() {
            let p = Path::new(&cmd);
            if !p.is_absolute() {
                if let Some(resolved) = which_in_path(&cmd) {
                    manifest.command = Some(resolved.to_string_lossy().to_string());
                } else if let Some(existing) = self.plugins.get(&manifest.id) {
                    if existing.check_binary_exists() {
                        manifest.command = existing.command.clone();
                    }
                }
            }
        }
        self.plugins.insert(manifest.id.clone(), manifest);
    }

    /// Loads all plugin manifests from a workspace or directory (searches `*.toml` and `*.json`).
    pub fn load_from_dir(&mut self, dir: &Path) -> usize {
        let mut count = 0;
        if !dir.exists() || !dir.is_dir() {
            return 0;
        }

        if let Ok(entries) = std::fs::read_dir(dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_file() {
                    let ext = path.extension().and_then(|s| s.to_str()).unwrap_or("");
                    if ext == "toml" {
                        if let Ok(content) = std::fs::read_to_string(&path) {
                            if let Ok(manifest) = toml::from_str::<AgentPluginManifest>(&content) {
                                info!("Loaded dynamic agent plugin from TOML: {}", manifest.id);
                                self.register_plugin(manifest);
                                count += 1;
                            } else {
                                warn!("Failed to parse agent plugin TOML: {}", path.display());
                            }
                        }
                    } else if ext == "json" {
                        if let Ok(content) = std::fs::read_to_string(&path) {
                            if let Ok(manifest) = serde_json::from_str::<AgentPluginManifest>(&content) {
                                info!("Loaded dynamic agent plugin from JSON: {}", manifest.id);
                                self.register_plugin(manifest);
                                count += 1;
                            } else {
                                warn!("Failed to parse agent plugin JSON: {}", path.display());
                            }
                        }
                    }
                }
            }
        }
        count
    }

    /// Retrieves a plugin manifest by id.
    pub fn get_plugin(&self, id: &str) -> Option<&AgentPluginManifest> {
        self.plugins.get(id)
    }

    /// Returns a list of all registered plugin manifests, sorted by priority descending.
    pub fn list_plugins(&self) -> Vec<AgentPluginManifest> {
        let mut list: Vec<AgentPluginManifest> = self.plugins.values().cloned().collect();
        list.sort_by(|a, b| b.priority.cmp(&a.priority));
        list
    }

    /// Selects the best suitable plugin for a given task request based on preferences, capabilities, and availability.
    pub fn select_plugin_for_task(&self, req: &AgentTaskRequest) -> Option<AgentPluginManifest> {
        // 1. If preferred plugin is specified and available, use it
        if let Some(pref) = &req.preferred_plugin {
            if let Some(p) = self.plugins.get(pref) {
                if p.enabled && p.is_available_on_current_os() && p.check_binary_exists() {
                    return Some(p.clone());
                }
            }
        }

        // 2. Otherwise find highest priority enabled and available plugin matching task capabilities
        let mut candidates: Vec<&AgentPluginManifest> = self
            .plugins
            .values()
            .filter(|p| {
                p.enabled
                    && p.is_available_on_current_os()
                    && p.check_binary_exists()
                    && (p.capabilities.is_empty()
                        || p.capabilities.iter().any(|c| c == &req.task_type || c == "all"))
            })
            .collect();

        candidates.sort_by(|a, b| b.priority.cmp(&a.priority));
        candidates.first().map(|p| (*p).clone())
    }

    /// Dispatches an agent task to the chosen plugin asynchronously.
    /// Handles cross-platform CLI execution, prompt template interpolation, and HTTP calls.
    pub async fn dispatch_task(&self, req: &AgentTaskRequest) -> anyhow::Result<AgentTaskResponse> {
        let start = Instant::now();
        let os_str = current_os().to_string();

        let plugin = match self.select_plugin_for_task(req) {
            Some(p) => p,
            None => {
                anyhow::bail!(
                    "No available agent plugin found on OS '{}' for task type '{}'. (Installed plugins: {})",
                    os_str,
                    req.task_type,
                    self.plugins
                        .values()
                        .map(|p| format!("{}(avail={})", p.id, p.check_binary_exists()))
                        .collect::<Vec<_>>()
                        .join(", ")
                );
            }
        };

        debug!("Dispatching task '{}' to plugin '{}'", req.task_type, plugin.id);

        if plugin.kind == "openai_http" {
            let endpoint = plugin
                .http_endpoint
                .as_deref()
                .unwrap_or("http://localhost:11434/v1");
            let url = if endpoint.ends_with("/chat/completions") {
                endpoint.to_string()
            } else {
                format!("{}/chat/completions", endpoint.trim_end_matches('/'))
            };

            let client = reqwest::Client::builder()
                .connect_timeout(std::time::Duration::from_secs(2))
                .timeout(std::time::Duration::from_secs(30))
                .build()?;

            let model_name = plugin.model.as_deref().unwrap_or("qwen2.5:32b");
            let body = serde_json::json!({
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional AI Director specialized in 4-beat micro-acting and cinematic visual storytelling."
                    },
                    {
                        "role": "user",
                        "content": req.prompt
                    }
                ],
                "temperature": 0.7
            });

            let resp = client.post(&url).json(&body).send().await?;
            if !resp.status().is_success() {
                let err_text = resp.text().await.unwrap_or_default();
                anyhow::bail!("OpenAI HTTP endpoint returned error: {}", err_text);
            }

            let resp_json: serde_json::Value = resp.json().await?;
            let output = resp_json
                .get("choices")
                .and_then(|c| c.as_array())
                .and_then(|a| a.first())
                .and_then(|c| c.get("message"))
                .and_then(|m| m.get("content"))
                .and_then(|s| s.as_str())
                .unwrap_or("")
                .to_string();

            let elapsed_ms = start.elapsed().as_millis() as u64;
            return Ok(AgentTaskResponse {
                plugin_id: plugin.id,
                status: "success".to_string(),
                output,
                elapsed_ms,
                os_platform: os_str,
            });
        }

        // CLI execution
        let bin_cmd = plugin
            .command
            .as_deref()
            .ok_or_else(|| anyhow::anyhow!("Plugin '{}' has no executable command specified", plugin.id))?;

        let conv_id = req
            .conversation_id
            .as_deref()
            .unwrap_or(DEFAULT_ANTIGRAVITY_CONVERSATION_ID);
        let work_dir = req.workspace_dir.as_deref().unwrap_or(".");

        let mut processed_args = Vec::new();
        for tmpl in &plugin.args_template {
            let replaced = tmpl
                .replace("{prompt}", &req.prompt)
                .replace("{conversation_id}", conv_id)
                .replace("{workspace_dir}", work_dir)
                .replace("{task_type}", &req.task_type);
            processed_args.push(replaced);
        }

        // If no template argument contains {prompt}, append it
        if !plugin.args_template.iter().any(|a| a.contains("{prompt}")) {
            processed_args.push(req.prompt.clone());
        }

        let mut cmd = if cfg!(target_os = "windows") && bin_cmd.ends_with(".bat") {
            let mut c = tokio::process::Command::new("cmd");
            c.arg("/C").arg(bin_cmd);
            c.args(&processed_args);
            c
        } else {
            let mut c = tokio::process::Command::new(bin_cmd);
            c.args(&processed_args);
            c
        };

        if let Some(wd) = &req.workspace_dir {
            let p = Path::new(wd);
            if p.exists() {
                cmd.current_dir(p);
            }
        }

        for (k, v) in &plugin.env {
            cmd.env(k, v);
        }

        cmd.stdin(std::process::Stdio::null());
        debug!("Executing CLI agent: {:?} with args {:?}", bin_cmd, processed_args);

        let out = tokio::time::timeout(std::time::Duration::from_secs(25), cmd.output())
            .await
            .map_err(|_| anyhow::anyhow!("Agent CLI execution timed out after 25 seconds"))??;

        let stdout = String::from_utf8_lossy(&out.stdout).to_string();
        let stderr = String::from_utf8_lossy(&out.stderr).to_string();
        let elapsed_ms = start.elapsed().as_millis() as u64;

        if !out.status.success() {
            let combined = format!("STDOUT:\n{}\nSTDERR:\n{}", stdout, stderr);
            warn!("Agent CLI invocation exited with error: {}", combined);
            Ok(AgentTaskResponse {
                plugin_id: plugin.id,
                status: "error".to_string(),
                output: combined,
                elapsed_ms,
                os_platform: os_str,
            })
        } else {
            let out_text = if stdout.trim().is_empty() {
                stderr
            } else {
                stdout
            };
            Ok(AgentTaskResponse {
                plugin_id: plugin.id,
                status: "success".to_string(),
                output: out_text,
                elapsed_ms,
                os_platform: os_str,
            })
        }
    }
}
