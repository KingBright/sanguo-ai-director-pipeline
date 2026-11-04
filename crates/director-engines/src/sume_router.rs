use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use tokio::process::Command;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SumeModelInfo {
    pub id: String,
    pub label: String,
    pub vendor: String,
    pub category: String,
    pub from_usd_per_sec_or_img: f64,
    pub highlights: String,
}

#[derive(Clone)]
pub struct SumeEngine {
    pub base_dir: PathBuf,
    pub python_bin: PathBuf,
}

impl SumeEngine {
    pub fn new(base_dir: impl Into<PathBuf>) -> Self {
        let base_dir = base_dir.into();
        let python_bin = crate::platform::resolve_python_bin(Some(&base_dir));
        Self {
            base_dir,
            python_bin,
        }
    }

    pub fn is_sume_model(model: &str) -> bool {
        if model.starts_with("sume:") {
            return true;
        }
        matches!(
            model,
            "heygen-video-1"
                | "seedance-2.5"
                | "seedance-2"
                | "seedance-2-fast"
                | "seedance-2-mini"
                | "minimax-h3-max"
                | "hailuo-h3-regen"
                | "kling-4"
                | "kling-4-omni"
                | "kling-3-omni"
                | "wan-3.0"
                | "wan-3.0-prime"
                | "vidu-q4"
                | "vidu-q4-reference"
                | "omnihuman-2"
                | "omnihuman-1.5"
                | "latentsync"
                | "kling-lipsync"
                | "sync-lipsync-3"
                | "sync-lipsync-2-pro"
        )
    }

    pub fn curated_models() -> Vec<SumeModelInfo> {
        vec![
            SumeModelInfo {
                id: "heygen-video-1".to_string(),
                label: "HeyGen Video 1 (Sume × HeyGen 免费礼券支持)".to_string(),
                vendor: "HeyGen".to_string(),
                category: "video".to_string(),
                from_usd_per_sec_or_img: 0.0100,
                highlights: "支持首帧/多参考图 + 原生语音精准口型同步 (480p-2K, 5-30s); 免费礼券每张可抵扣1条视频".to_string(),
            },
            SumeModelInfo {
                id: "seedance-2.5".to_string(),
                label: "Seedance 2.5 (字节跳动最新旗舰)".to_string(),
                vendor: "ByteDance".to_string(),
                category: "video".to_string(),
                from_usd_per_sec_or_img: 0.1028,
                highlights: "4-30s 超长镜头、首尾帧、多参考图/参考视频、原生音画直出，比 fal.ai 便宜 51%".to_string(),
            },
            SumeModelInfo {
                id: "seedance-2-fast".to_string(),
                label: "Seedance 2.0 Fast / Mini".to_string(),
                vendor: "ByteDance".to_string(),
                category: "video".to_string(),
                from_usd_per_sec_or_img: 0.0400,
                highlights: "高性价比中文口型与武打/运镜生成 ($0.04/s - $0.057/s)".to_string(),
            },
            SumeModelInfo {
                id: "minimax-h3-max".to_string(),
                label: "MiniMax H3 Max / H3 (海螺云端直出)".to_string(),
                vendor: "MiniMax".to_string(),
                category: "video".to_string(),
                from_usd_per_sec_or_img: 0.0500,
                highlights: "老张教程同款 MiniMax H3 云端满血版，原生立体声 + 中文/日语台词直出 (480p-4K)".to_string(),
            },
            SumeModelInfo {
                id: "kling-4-omni".to_string(),
                label: "Kling 4.0 Omni (快手可灵 4.0 全能)".to_string(),
                vendor: "Kuaishou".to_string(),
                category: "video".to_string(),
                from_usd_per_sec_or_img: 0.1570,
                highlights: "支持最多 10 张参考图 + 首尾帧 + 最长 30s + 原生音效".to_string(),
            },
            SumeModelInfo {
                id: "wan-3.0".to_string(),
                label: "Wan 3.0 / 3.0 Prime (阿里通义万相 3.0)".to_string(),
                vendor: "Alibaba".to_string(),
                category: "video".to_string(),
                from_usd_per_sec_or_img: 0.0500,
                highlights: "支持最长 30s、首尾帧、参考图与原生音频驱动 ($0.05/s 起)".to_string(),
            },
            SumeModelInfo {
                id: "vidu-q4-reference".to_string(),
                label: "Vidu v4 Reference (多角色多声纹)".to_string(),
                vendor: "Vidu".to_string(),
                category: "video".to_string(),
                from_usd_per_sec_or_img: 0.0315,
                highlights: "单镜头支持最多 12 张参考图 + 3 个独立角色声纹绑定 (540p-4K)".to_string(),
            },
            SumeModelInfo {
                id: "omnihuman-2".to_string(),
                label: "OmniHuman 2 / 1.5 (字节音频驱动数字人表演)".to_string(),
                vendor: "ByteDance".to_string(),
                category: "lipsync".to_string(),
                from_usd_per_sec_or_img: 0.1050,
                highlights: "用 100% 准确中文配音直接驱动单张剧照全身与面部微表情演绎".to_string(),
            },
            SumeModelInfo {
                id: "latentsync".to_string(),
                label: "LatentSync / Kling Lipsync (二次口型重对齐修复)".to_string(),
                vendor: "ByteDance / Kling".to_string(),
                category: "lipsync".to_string(),
                from_usd_per_sec_or_img: 0.0050,
                highlights: "仅 $0.005/秒（6秒仅需3美分），可将已生成视频的嘴型与修正后的标准普通话配音 1:1 重新对齐".to_string(),
            },
        ]
    }

    pub async fn generate_single_scene_clip(
        &self,
        initial_frame: Option<&Path>,
        end_frame: Option<&Path>,
        prompt: &str,
        output_file: &Path,
        aspect: &str,
        model: &str,
        duration_sec: u32,
        dry_run: bool,
    ) -> anyhow::Result<(bool, String, String)> {
        if let Some(parent) = output_file.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let worker_script = self.base_dir.join("scripts").join("sume_worker.py");
        let clean_model = model.strip_prefix("sume:").unwrap_or(model);

        let mut cmd = Command::new(&self.python_bin);
        cmd.current_dir(&self.base_dir);
        cmd.arg("-X")
            .arg("utf8")
            .arg(&worker_script)
            .arg("generate-video")
            .arg("--model")
            .arg(clean_model)
            .arg("--prompt")
            .arg(prompt)
            .arg("--duration")
            .arg(duration_sec.max(5).to_string())
            .arg("--aspect")
            .arg(aspect)
            .arg("-o")
            .arg(output_file);

        if let Some(init) = initial_frame.filter(|p| p.exists()) {
            cmd.arg("--image-url").arg(init);
        }
        if let Some(ef) = end_frame.filter(|p| p.exists()) {
            cmd.arg("--end-image-url").arg(ef);
        }
        if dry_run {
            cmd.arg("--dry-run");
        }

        let out = cmd.output().await?;
        let stdout = String::from_utf8_lossy(&out.stdout).to_string();
        let stderr = String::from_utf8_lossy(&out.stderr).to_string();
        Ok((out.status.success(), stdout, stderr))
    }
}
