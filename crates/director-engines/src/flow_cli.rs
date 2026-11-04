use std::collections::HashMap;
use std::path::{Path, PathBuf};

use chrono::{Local, TimeZone};
use serde::{Deserialize, Serialize};
use tokio::process::Command;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreditReport {
    pub success: bool,
    pub authenticated: bool,
    pub auth_details: String,
    pub balance: i64,
    pub last_spent: Option<i64>,
    pub refresh_epoch: Option<i64>,
    pub refresh_countdown: String,
    pub minutes_quality: f64,
    pub clips_quality: i64,
    pub minutes_omni: f64,
    pub clips_omni: i64,
    pub minutes_fast: f64,
    pub clips_fast: i64,
    pub minutes_lite: f64,
    pub clips_lite: i64,
    pub formatted_report: String,
}

#[derive(Debug, Deserialize)]
struct CreditsCacheJson {
    balance: Option<i64>,
    previous_balance: Option<i64>,
    last_spent: Option<i64>,
    refresh_epoch: Option<i64>,
}

#[derive(Clone)]
pub struct FlowEngine {
    pub gflow_bin: String,
    pub base_dir: PathBuf,
}

impl FlowEngine {
    pub fn new(base_dir: impl Into<PathBuf>) -> Self {
        Self {
            gflow_bin: "gflow".to_string(),
            base_dir: base_dir.into(),
        }
    }

    fn get_env(&self) -> HashMap<String, String> {
        let mut env: HashMap<String, String> = std::env::vars().collect();
        if !env.contains_key("CHROME_BINARY") {
            if let Some(browser) = crate::platform::resolve_browser_bin() {
                env.insert(
                    "CHROME_BINARY".to_string(),
                    browser.to_string_lossy().to_string(),
                );
            }
        }
        env
    }

    pub async fn get_credits_and_status(&self) -> CreditReport {
        let cache_file = crate::platform::resolve_gflow_credits_cache();

        let mut bal = 0i64;
        let mut last_spent = None;
        let mut refresh_epoch = None;
        let mut has_cache = false;

        if cache_file.exists() {
            if let Ok(raw) = std::fs::read_to_string(&cache_file) {
                if let Ok(data) = serde_json::from_str::<CreditsCacheJson>(&raw) {
                    bal = data.balance.unwrap_or(0);
                    last_spent = data.last_spent.or_else(|| {
                        data.previous_balance
                            .filter(|&prev| prev >= bal)
                            .map(|prev| prev - bal)
                    });
                    refresh_epoch = data.refresh_epoch;
                    has_cache = true;
                }
            }
        }

        let now_ts = chrono::Utc::now().timestamp();
        let countdown_str = if let Some(ref_ep) = refresh_epoch {
            let dt_str = Local
                .timestamp_opt(ref_ep, 0)
                .single()
                .map(|dt| dt.format("%Y-%m-%d %H:%M:%S").to_string())
                .unwrap_or_else(|| "未知".to_string());
            let rem_sec = (ref_ep - now_ts).max(0);
            let days = rem_sec / 86400;
            let hours = (rem_sec % 86400) / 3600;
            let mins = (rem_sec % 3600) / 60;
            format!("{}天 {}小时 {}分钟 (刷新时间: {})", days, hours, mins, dt_str)
        } else {
            "未知".to_string()
        };

        let clips_quality = bal / 100;
        let min_quality = (((bal as f64 / 100.0) * 8.0 / 60.0) * 10.0).round() / 10.0;
        let clips_omni = bal / 12;
        let min_omni = (((bal as f64 / 12.0) * 8.0 / 60.0) * 10.0).round() / 10.0;
        let clips_fast = bal / 10;
        let min_fast = (((bal as f64 / 10.0) * 8.0 / 60.0) * 10.0).round() / 10.0;
        let clips_lite = bal / 5;
        let min_lite = (((bal as f64 / 5.0) * 8.0 / 60.0) * 10.0).round() / 10.0;

        let formatted_report = format!(
            "当前剩余: {} 点{} | 距离下次刷新: {} | 可制作时长: Quality {}分钟 ({}镜) / Omni {}分钟 ({}镜) / Fast {}分钟 ({}镜) / Lite {}分钟 ({}镜)",
            bal,
            last_spent
                .map(|s| format!(" (最近消耗: {} 点)", s))
                .unwrap_or_default(),
            countdown_str,
            min_quality,
            clips_quality,
            min_omni,
            clips_omni,
            min_fast,
            clips_fast,
            min_lite,
            clips_lite
        );

        CreditReport {
            success: has_cache,
            authenticated: has_cache,
            auth_details: if has_cache {
                "Google AI Ultra 会话已就绪 (flow.google.com)".to_string()
            } else {
                "未读取到本地积分缓存，可执行 gflow auth login".to_string()
            },
            balance: bal,
            last_spent,
            refresh_epoch,
            refresh_countdown: countdown_str,
            minutes_quality: min_quality,
            clips_quality,
            minutes_omni: min_omni,
            clips_omni,
            minutes_fast: min_fast,
            clips_fast,
            minutes_lite: min_lite,
            clips_lite,
            formatted_report,
        }
    }

    pub async fn run_movie_project(
        &self,
        manifest_path: &Path,
        out_dir: Option<&Path>,
        dry_run: bool,
        stitch: bool,
    ) -> anyhow::Result<(bool, String, String)> {
        let mut cmd = Command::new(&self.gflow_bin);
        cmd.envs(self.get_env());
        cmd.arg("movie").arg("run").arg(manifest_path);
        if dry_run {
            cmd.arg("--dry-run");
        }
        if stitch {
            cmd.arg("--stitch");
        }
        if let Some(out) = out_dir {
            cmd.arg("--out-dir").arg(out);
        }

        let output = cmd.output().await?;
        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        Ok((output.status.success(), stdout, stderr))
    }

    pub async fn generate_single_scene_clip(
        &self,
        initial_frame: Option<&Path>,
        prompt: &str,
        output_file: &Path,
        aspect: &str,
        model: &str,
    ) -> anyhow::Result<(bool, String, String)> {
        if let Some(parent) = output_file.parent() {
            std::fs::create_dir_all(parent)?;
        }

        let mut cmd = Command::new(&self.gflow_bin);
        cmd.envs(self.get_env());
        if let Some(frame) = initial_frame.filter(|p| p.exists()) {
            cmd.arg("video")
                .arg("i2v")
                .arg("--initial-frame")
                .arg(frame)
                .arg(prompt)
                .arg("--aspect")
                .arg(aspect)
                .arg("--model")
                .arg(model)
                .arg("-o")
                .arg(output_file);
        } else {
            cmd.arg("video")
                .arg("t2v")
                .arg(prompt)
                .arg("--aspect")
                .arg(aspect)
                .arg("--model")
                .arg(model)
                .arg("-o")
                .arg(output_file);
        }

        let output = cmd.output().await?;
        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        Ok((output.status.success(), stdout, stderr))
    }

    /// Generates an I2V clip with both `--initial-frame` and optional `--end-frame` interpolation
    /// (supported in gflow 0.92.1+ across Veo 3.1 and omni-flash up to 10s).
    pub async fn generate_dual_frame_i2v(
        &self,
        initial_frame: &Path,
        end_frame: Option<&Path>,
        prompt: &str,
        output_file: &Path,
        aspect: &str,
        model: &str,
        duration_sec: Option<u32>,
    ) -> anyhow::Result<(bool, String, String)> {
        if let Some(parent) = output_file.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let mut cmd = Command::new(&self.gflow_bin);
        cmd.envs(self.get_env());
        cmd.arg("video")
            .arg("i2v")
            .arg("--initial-frame")
            .arg(initial_frame);
        if let Some(ef) = end_frame.filter(|p| p.exists()) {
            cmd.arg("--end-frame").arg(ef);
        }
        if let Some(dur) = duration_sec {
            let valid_dur = if model == "omni-flash" && dur >= 10 {
                10
            } else if dur >= 8 {
                8
            } else if dur >= 6 {
                6
            } else {
                4
            };
            cmd.arg("--duration").arg(valid_dur.to_string());
        }
        cmd.arg(prompt)
            .arg("--aspect")
            .arg(aspect)
            .arg("--model")
            .arg(model)
            .arg("-o")
            .arg(output_file);

        let output = cmd.output().await?;
        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        Ok((output.status.success(), stdout, stderr))
    }

    /// Generates a Reference-to-Video (`gflow video r2v`) clip conditioned on up to 7 ingredient images
    /// (`omni-flash` cap = 7, `veo-fast` / `veo-lite` cap = 3).
    pub async fn generate_multi_ref_r2v(
        &self,
        ref_images: &[PathBuf],
        prompt: &str,
        output_file: &Path,
        aspect: &str,
        model: &str,
    ) -> anyhow::Result<(bool, String, String)> {
        if let Some(parent) = output_file.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let max_refs = if model == "omni-flash" { 7 } else { 3 };
        let mut cmd = Command::new(&self.gflow_bin);
        cmd.envs(self.get_env());
        cmd.arg("video").arg("r2v").arg(prompt);
        for r in ref_images.iter().filter(|p| p.exists()).take(max_refs) {
            cmd.arg("--ref").arg(r);
        }
        cmd.arg("--aspect")
            .arg(aspect)
            .arg("--model")
            .arg(model)
            .arg("-o")
            .arg(output_file);

        let output = cmd.output().await?;
        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        Ok((output.status.success(), stdout, stderr))
    }

    /// Generates or edits keyframe/character images using Google Flow's latest image models
    /// (`nano-pro` / `GEM_PIX_2`, `nano2.1` / `NARWHAL` with 10-ref cap, or `imagen4` / `IMAGEN_3_5`).
    pub async fn generate_flow_image(
        &self,
        prompt: &str,
        ref_images: &[PathBuf],
        output_file: &Path,
        aspect: &str,
        model: &str,
    ) -> anyhow::Result<(bool, String, String)> {
        if let Some(parent) = output_file.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let mut cmd = Command::new(&self.gflow_bin);
        cmd.envs(self.get_env());
        if ref_images.is_empty() {
            cmd.arg("image")
                .arg("t2i")
                .arg(prompt)
                .arg("--aspect")
                .arg(aspect)
                .arg("--model")
                .arg(model)
                .arg("-o")
                .arg(output_file);
        } else {
            cmd.arg("image").arg("i2i").arg(prompt);
            for r in ref_images.iter().filter(|p| p.exists()).take(10) {
                cmd.arg("--ref").arg(r);
            }
            cmd.arg("--aspect")
                .arg(aspect)
                .arg("--model")
                .arg(model)
                .arg("-o")
                .arg(output_file);
        }
        let output = cmd.output().await?;
        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        Ok((output.status.success(), stdout, stderr))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_flow_credits_with_seeded_cache() {
        let ws = std::env::current_dir().unwrap();
        let engine = FlowEngine::new(&ws);
        let report = engine.get_credits_and_status().await;
        assert!(report.success, "Should find credit cache");
        assert_eq!(report.balance, 9895, "Should match 9895 credits from cubex audit");
        assert!(report.clips_quality >= 98);
        assert!(report.clips_fast >= 980);
    }
}
