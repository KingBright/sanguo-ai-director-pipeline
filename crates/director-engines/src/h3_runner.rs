use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use tokio::process::Command;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocalGpuStatus {
    pub device_name: String,
    pub vram_gb: u32,
    pub gpu_detected: bool,
    pub model_ready: bool,
    pub python_bin: String,
    pub model_dir: String,
}

#[derive(Clone)]
pub struct H3Engine {
    pub base_dir: PathBuf,
    pub python_bin: PathBuf,
    pub model_dir: PathBuf,
}

impl H3Engine {
    pub fn new(base_dir: impl Into<PathBuf>) -> Self {
        let base_dir = base_dir.into();
        Self {
            base_dir,
            python_bin: PathBuf::from("C:/Users/Liang/minimax/.venv/Scripts/python.exe"),
            model_dir: PathBuf::from("C:/Users/Liang/minimax/MiniMax-H3"),
        }
    }

    pub fn check_system(&self) -> LocalGpuStatus {
        let model_ready = self.model_dir.exists() && self.python_bin.exists();
        LocalGpuStatus {
            device_name: "AMD Radeon 8060S (Strix Halo gfx1151 UMA)".to_string(),
            vram_gb: 96,
            gpu_detected: self.python_bin.exists(),
            model_ready,
            python_bin: self.python_bin.to_string_lossy().to_string(),
            model_dir: self.model_dir.to_string_lossy().to_string(),
        }
    }

    pub async fn run_episode_or_preview(
        &self,
        ep_num: u32,
        dry_run: bool,
    ) -> anyhow::Result<(bool, String, String)> {
        let mut ep_ids = Vec::new();
        if let Ok(entries) = std::fs::read_dir(self.base_dir.join("episodes")) {
            let mut dirs: Vec<_> = entries.flatten().filter(|e| e.path().is_dir()).collect();
            dirs.sort_by_key(|e| e.file_name());
            for d in dirs {
                let name = d.file_name().to_string_lossy().to_string();
                if !name.starts_with('.') {
                    ep_ids.push(name);
                }
            }
        }
        let idx = (ep_num.saturating_sub(1) as usize).min(ep_ids.len().saturating_sub(1));
        let ep_id = ep_ids
            .get(idx)
            .cloned()
            .unwrap_or_else(|| format!("ep{:02}", ep_num.max(1)));
        self.run_local_h3_render(&self.base_dir, &ep_id, None, dry_run)
            .await
    }

    pub async fn run_local_h3_render(
        &self,
        project_base_dir: &std::path::Path,
        episode_id: &str,
        scene_id: Option<&str>,
        dry_run: bool,
    ) -> anyhow::Result<(bool, String, String)> {
        if !self.python_bin.exists() {
            anyhow::bail!(
                "MiniMax H3 python runtime not found at {}",
                self.python_bin.display()
            );
        }
        let worker_script = self.base_dir.join("scripts").join("local_rocm_worker.py");
        let mut cmd = Command::new(&self.python_bin);
        cmd.current_dir(&self.base_dir);
        cmd.arg("-X")
            .arg("utf8")
            .arg(&worker_script)
            .arg("render-h3")
            .arg("--base-dir")
            .arg(project_base_dir)
            .arg("--episode-id")
            .arg(episode_id);
        if let Some(sid) = scene_id {
            if !sid.trim().is_empty() {
                cmd.arg("--scene-id").arg(sid);
            }
        }
        if dry_run {
            cmd.arg("--dry-run");
        }
        let out = cmd.output().await?;
        let stdout = String::from_utf8_lossy(&out.stdout).to_string();
        let stderr = String::from_utf8_lossy(&out.stderr).to_string();
        Ok((out.status.success(), stdout, stderr))
    }

    pub async fn synthesize_voiceovers(
        &self,
        project_base_dir: &std::path::Path,
        episode_id: &str,
        scene_id: Option<&str>,
        instruct: Option<&str>,
    ) -> anyhow::Result<(bool, String, String)> {
        let worker_script = self.base_dir.join("scripts").join("local_rocm_worker.py");
        let mut cmd = Command::new(&self.python_bin);
        cmd.current_dir(&self.base_dir);
        cmd.arg("-X")
            .arg("utf8")
            .arg(&worker_script)
            .arg("tts")
            .arg("--base-dir")
            .arg(project_base_dir)
            .arg("--root-dir")
            .arg(&self.base_dir)
            .arg("--episode-id")
            .arg(episode_id);
        if let Some(sid) = scene_id {
            if !sid.trim().is_empty() {
                cmd.arg("--scene-id").arg(sid);
            }
        }
        if let Some(ins) = instruct {
            if !ins.trim().is_empty() {
                cmd.arg("--instruct").arg(ins);
            }
        }
        let out = cmd.output().await?;
        let stdout = String::from_utf8_lossy(&out.stdout).to_string();
        let stderr = String::from_utf8_lossy(&out.stderr).to_string();
        Ok((out.status.success(), stdout, stderr))
    }

    pub async fn compose_bgm(
        &self,
        project_base_dir: &std::path::Path,
        episode_id: &str,
        prompt: &str,
        duration_sec: f64,
        seed: i64,
    ) -> anyhow::Result<(bool, String, String)> {
        let worker_script = self.base_dir.join("scripts").join("local_rocm_worker.py");
        let mut cmd = Command::new(&self.python_bin);
        cmd.current_dir(&self.base_dir);
        cmd.arg("-X")
            .arg("utf8")
            .arg(&worker_script)
            .arg("bgm")
            .arg("--base-dir")
            .arg(project_base_dir)
            .arg("--episode-id")
            .arg(episode_id)
            .arg("--prompt")
            .arg(prompt)
            .arg("--duration")
            .arg(format!("{:.1}", duration_sec))
            .arg("--seed")
            .arg(seed.to_string());
        let out = cmd.output().await?;
        let stdout = String::from_utf8_lossy(&out.stdout).to_string();
        let stderr = String::from_utf8_lossy(&out.stderr).to_string();
        Ok((out.status.success(), stdout, stderr))
    }

    pub async fn master_episode_local(
        &self,
        project_base_dir: &std::path::Path,
        episode_id: &str,
    ) -> anyhow::Result<(bool, String, String)> {
        let worker_script = self.base_dir.join("scripts").join("local_rocm_worker.py");
        let mut cmd = Command::new(&self.python_bin);
        cmd.current_dir(&self.base_dir);
        cmd.arg("-X")
            .arg("utf8")
            .arg(&worker_script)
            .arg("master")
            .arg("--base-dir")
            .arg(project_base_dir)
            .arg("--episode-id")
            .arg(episode_id);
        let out = cmd.output().await?;
        let stdout = String::from_utf8_lossy(&out.stdout).to_string();
        let stderr = String::from_utf8_lossy(&out.stderr).to_string();
        Ok((out.status.success(), stdout, stderr))
    }

    pub async fn run_test_shot(&self) -> anyhow::Result<(bool, String, String)> {
        let mut cmd = Command::new(&self.python_bin);
        cmd.current_dir(&self.base_dir);
        cmd.arg("run_h3.py").arg("--test-shot");
        let out = cmd.output().await?;
        let stdout = String::from_utf8_lossy(&out.stdout).to_string();
        let stderr = String::from_utf8_lossy(&out.stderr).to_string();
        Ok((out.status.success(), stdout, stderr))
    }
}
