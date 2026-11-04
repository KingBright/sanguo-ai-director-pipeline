use std::path::{Path, PathBuf};
use tokio::process::Command;
use tracing::{debug, info, warn};

use crate::platform::{resolve_colab_bin, resolve_python_bin};

/// Colab Ultra Workstation & Cross-Platform Audio-Video Runner.
/// Orchestrates cloud and local GPU dispatch, neural audio synthesis, and video quality critique.
#[derive(Debug, Clone)]
pub struct ColabBridgeRunner {
    pub workspace_root: PathBuf,
    pub python_bin: PathBuf,
    pub colab_bin: Option<PathBuf>,
}

impl ColabBridgeRunner {
    pub fn new(workspace_root: impl Into<PathBuf>) -> Self {
        let root = workspace_root.into();
        let py = resolve_python_bin(Some(&root));
        let colab = resolve_colab_bin();
        Self {
            workspace_root: root,
            python_bin: py,
            colab_bin: colab,
        }
    }

    /// Invokes the `colab_av_bridge.py` script across platforms.
    pub async fn run_av_bridge(&self, extra_args: &[&str]) -> anyhow::Result<String> {
        let script_candidates = [
            self.workspace_root
                .join(".agents")
                .join("skills")
                .join("colab-ultra-workstation")
                .join("scripts")
                .join("colab_av_bridge.py"),
            self.workspace_root.join("scripts").join("colab_av_bridge.py"),
        ];

        let script = script_candidates
            .iter()
            .find(|p| p.exists())
            .ok_or_else(|| anyhow::anyhow!("colab_av_bridge.py not found in workspace"))?;

        info!("Invoking Colab AV Bridge script: {}", script.display());

        let mut cmd = Command::new(&self.python_bin);
        cmd.current_dir(&self.workspace_root)
            .arg("-X")
            .arg("utf8")
            .arg(script)
            .args(extra_args);

        let out = cmd.output().await?;
        let stdout = String::from_utf8_lossy(&out.stdout).to_string();
        let stderr = String::from_utf8_lossy(&out.stderr).to_string();

        if !out.status.success() {
            anyhow::bail!("colab_av_bridge failed ({}): {}\n{}", out.status, stdout, stderr);
        }

        Ok(stdout)
    }

    /// Invokes the `colab_av_bridge.py` script with parallel worker and session pool support.
    pub async fn run_av_bridge_parallel(
        &self,
        parallel_workers: usize,
        session_pool: Option<&[&str]>,
        extra_args: &[&str],
    ) -> anyhow::Result<String> {
        let workers_str = parallel_workers.to_string();
        let mut args: Vec<&str> = vec!["--parallel-workers", &workers_str];
        let pool_str;
        if let Some(pool) = session_pool {
            if !pool.is_empty() {
                pool_str = pool.join(",");
                args.push("--session-pool");
                args.push(&pool_str);
            }
        }
        args.extend_from_slice(extra_args);
        self.run_av_bridge(&args).await
    }

    /// Invokes the `colab_tts_client.py` script to synthesize speech with natural emotion.
    pub async fn run_tts_client(
        &self,
        text: &str,
        voice: &str,
        output_path: &Path,
    ) -> anyhow::Result<PathBuf> {
        let script_candidates = [
            self.workspace_root
                .join(".agents")
                .join("skills")
                .join("colab-ultra-workstation")
                .join("scripts")
                .join("colab_tts_client.py"),
            self.workspace_root.join("scripts").join("colab_tts_client.py"),
        ];

        let script = script_candidates
            .iter()
            .find(|p| p.exists())
            .ok_or_else(|| anyhow::anyhow!("colab_tts_client.py not found in workspace"))?;

        let mut cmd = Command::new(&self.python_bin);
        cmd.current_dir(&self.workspace_root)
            .arg("-X")
            .arg("utf8")
            .arg(script)
            .arg("--text")
            .arg(text)
            .arg("--voice")
            .arg(voice)
            .arg("--output")
            .arg(output_path);

        let out = cmd.output().await?;
        if !out.status.success() {
            let stderr = String::from_utf8_lossy(&out.stderr);
            anyhow::bail!("colab_tts_client failed: {}", stderr);
        }

        Ok(output_path.to_path_buf())
    }

    /// Invokes `scripts/video_quality_critic.py --video <path> --json` to perform
    /// quantitative 4-beat micro-acting and audio-visual lip-sync evaluation with minimal tokens.
    pub async fn run_video_quality_critic(&self, video_path: &Path) -> anyhow::Result<serde_json::Value> {
        let script = self.workspace_root.join("scripts").join("video_quality_critic.py");
        if !script.exists() {
            anyhow::bail!("video_quality_critic.py not found at {}", script.display());
        }

        debug!(
            "Running video quality critic on {} using {}",
            video_path.display(),
            self.python_bin.display()
        );

        let mut cmd = Command::new(&self.python_bin);
        cmd.current_dir(&self.workspace_root)
            .arg("-X")
            .arg("utf8")
            .arg(&script)
            .arg("--video")
            .arg(video_path)
            .arg("--json");

        let out = cmd.output().await?;
        let stdout = String::from_utf8_lossy(&out.stdout).to_string();
        let stderr = String::from_utf8_lossy(&out.stderr).to_string();

        if !out.status.success() {
            warn!("video_quality_critic stderr: {}", stderr);
            anyhow::bail!("video_quality_critic exited with code {}: {}", out.status, stderr);
        }

        let parsed: serde_json::Value = serde_json::from_str(stdout.trim())
            .map_err(|e| anyhow::anyhow!("Failed to parse video critic JSON: {} (Output: {})", e, stdout))?;

        Ok(parsed)
    }
}
