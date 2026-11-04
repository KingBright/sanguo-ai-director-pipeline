#![recursion_limit = "512"]

use std::path::PathBuf;
use director_core::WorkspacePaths;

#[path = "../mcp.rs"]
mod mcp;

fn resolve_workspace_root() -> PathBuf {
    if let Ok(dir) = std::env::var("DIRECTOR_WORKSPACE") {
        return PathBuf::from(dir);
    }
    let cwd = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    if cwd.join("episodes").exists() || cwd.join("projects").exists() {
        return cwd;
    }
    for ancestor in cwd.ancestors() {
        if ancestor.join("episodes").exists() || ancestor.join("projects").exists() {
            return ancestor.to_path_buf();
        }
    }
    cwd
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    let base_dir = resolve_workspace_root();
    if let Some(pos) = args.iter().position(|a| a == "cli" || a == "--cli") {
        let tool_name = args
            .get(pos + 1)
            .cloned()
            .unwrap_or_else(|| "studio_list_projects".to_string());
        let json_arg = args.get(pos + 2).cloned().unwrap_or_else(|| "{}".to_string());
        let parsed_args: serde_json::Value =
            serde_json::from_str(&json_arg).unwrap_or_else(|_| serde_json::json!({}));
        let active_proj = WorkspacePaths::resolve_active_project_id(&base_dir);
        let paths = WorkspacePaths::for_project(&base_dir, &active_proj);
        let req = serde_json::json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": parsed_args,
            }
        });
        if let Some(resp) = mcp::handle_mcp_jsonrpc(&paths, req).await {
            if let Some(text) = resp
                .pointer("/result/content/0/text")
                .and_then(|v| v.as_str())
            {
                println!("{}", text);
            } else {
                println!("{}", serde_json::to_string_pretty(&resp)?);
            }
        }
        return Ok(());
    }

    mcp::run_mcp_stdio(base_dir).await
}
