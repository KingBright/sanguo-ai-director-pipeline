use std::path::{Path, PathBuf};

use regex::Regex;
use tokio::process::Command;

use crate::linter::DirectorLinter;

pub struct MasteringEngine {
    pub base_dir: PathBuf,
    pub ffmpeg_bin: String,
}

impl MasteringEngine {
    pub fn new(base_dir: impl Into<PathBuf>) -> Self {
        Self {
            base_dir: base_dir.into(),
            ffmpeg_bin: "ffmpeg".to_string(),
        }
    }

    pub async fn master_scene_clip(
        &self,
        linter: &DirectorLinter,
        raw_video_path: &Path,
        output_video_path: &Path,
        acoustic_space: &str,
        voiceover_path: Option<&Path>,
        ass_subtitle_path: Option<&Path>,
        target_duration: f64,
        vo_delay_ms: u32,
        use_native_audio: bool,
    ) -> anyhow::Result<()> {
        if !raw_video_path.exists() {
            anyhow::bail!("Raw video clip not found: {}", raw_video_path.display());
        }
        if !use_native_audio {
            if let Some(vo) = voiceover_path {
                if !vo.exists() {
                    anyhow::bail!("Voiceover audio file not found: {}", vo.display());
                }
            }
        }
        if let Some(ass) = ass_subtitle_path {
            if !ass.exists() {
                anyhow::bail!("ASS subtitle file not found: {}", ass.display());
            }
        }

        let bg_filter = linter.get_ffmpeg_bg_filter(acoustic_space);
        if let Some(parent) = output_video_path.parent() {
            std::fs::create_dir_all(parent)?;
        }

        // Probe input duration
        let probe = Command::new(&self.ffmpeg_bin)
            .arg("-i")
            .arg(raw_video_path)
            .output()
            .await?;
        let stderr = String::from_utf8_lossy(&probe.stderr);
        let mut raw_dur = target_duration;
        if let Ok(re) = Regex::new(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)") {
            if let Some(caps) = re.captures(&stderr) {
                let h: f64 = caps[1].parse().unwrap_or(0.0);
                let m: f64 = caps[2].parse().unwrap_or(0.0);
                let s: f64 = caps[3].parse().unwrap_or(0.0);
                raw_dur = h * 3600.0 + m * 60.0 + s;
            }
        }

        let effective_dur = if use_native_audio {
            raw_dur
        } else {
            target_duration
        };

        let mut v_filters = Vec::new();
        if !use_native_audio && raw_dur > 0.5 && (raw_dur - target_duration).abs() > 0.25 {
            let stretch = ((target_duration / raw_dur) * 10000.0).round() / 10000.0;
            v_filters.push(format!("setpts={}*PTS", stretch));
            v_filters.push("minterpolate=fps=24:mi_mode=blend".to_string());
        } else {
            v_filters.push("fps=24".to_string());
        }
        v_filters.push("scale=1280:720:flags=lanczos".to_string());

        if let Some(ass) = ass_subtitle_path {
            let safe_ass = ass.to_string_lossy().replace('\\', "/").replace(':', "\\:");
            v_filters.push(format!("ass='{}'", safe_ass));
        }
        let v_chain = v_filters.join(",");

        let rain_bed = self
            .base_dir
            .join("output/raw_clips/ep01_crossing/ep01_01_rain_exterior_v3_cloud.mp4");
        let use_rain_bed =
            rain_bed.exists() && matches!(acoustic_space, "exterior_storm" | "interior_closed");

        let mut cmd = Command::new(&self.ffmpeg_bin);
        cmd.arg("-y").arg("-i").arg(raw_video_path);

        if use_native_audio {
            let filter_complex = format!(
                "[0:v]{}[v];[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=1.35[a]",
                v_chain
            );
            cmd.arg("-filter_complex")
                .arg(filter_complex)
                .arg("-map")
                .arg("[v]")
                .arg("-map")
                .arg("[a]")
                .arg("-t")
                .arg(format!("{:.2}", effective_dur));
        } else if use_rain_bed && voiceover_path.is_some() {
            let vo = voiceover_path.unwrap();
            let bed_filter = if acoustic_space == "exterior_storm" {
                "volume=0.80"
            } else {
                "lowpass=f=420,volume=0.35"
            };
            let filter_complex = format!(
                "[0:v]{v_chain}[v];[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad=whole_dur={target_duration},{bg_filter}[raw_a];[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad=whole_dur={target_duration},{bed_filter}[bed_a];[2:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,adelay={vo_delay_ms}|{vo_delay_ms},apad=whole_dur={target_duration},volume=1.85[vo];[raw_a][bed_a][vo]amix=inputs=3:duration=first:dropout_transition=2:normalize=0[a]"
            );
            cmd.arg("-i")
                .arg(&rain_bed)
                .arg("-i")
                .arg(vo)
                .arg("-filter_complex")
                .arg(filter_complex)
                .arg("-map")
                .arg("[v]")
                .arg("-map")
                .arg("[a]")
                .arg("-t")
                .arg(target_duration.to_string());
        } else if let Some(vo) = voiceover_path {
            let filter_complex = format!(
                "[0:v]{v_chain}[v];[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad=whole_dur={target_duration},{bg_filter}[bg];[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,adelay={vo_delay_ms}|{vo_delay_ms},apad=whole_dur={target_duration},volume=1.85[vo];[bg][vo]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[a]"
            );
            cmd.arg("-i")
                .arg(vo)
                .arg("-filter_complex")
                .arg(filter_complex)
                .arg("-map")
                .arg("[v]")
                .arg("-map")
                .arg("[a]")
                .arg("-t")
                .arg(target_duration.to_string());
        } else {
            let filter_complex = format!(
                "[0:v]{v_chain}[v];[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad=whole_dur={target_duration},{bg_filter}[a]"
            );
            cmd.arg("-filter_complex")
                .arg(filter_complex)
                .arg("-map")
                .arg("[v]")
                .arg("-map")
                .arg("[a]")
                .arg("-t")
                .arg(target_duration.to_string());
        }

        cmd.args([
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "192k",
        ])
        .arg(output_video_path);

        let res = cmd.output().await?;
        if !res.status.success() {
            let err_str = String::from_utf8_lossy(&res.stderr);
            anyhow::bail!("FFmpeg mastering failed: {}", err_str);
        }
        Ok(())
    }

    /// Exports a non-destructive multi-track JianYing Pro / CapCut (`draft_content.json`) project
    /// and separate stem files (`SRT` subtitle track, trimmed video manifest, voice/foley/BGM track slots)
    /// so raw generated clips can be trimmed cleanly without cutting BGM or subtitles.
    pub fn export_jianying_multitrack_draft(
        &self,
        episode_id: &str,
        title: &str,
        scenes: &[crate::models::SceneSpec],
    ) -> anyhow::Result<PathBuf> {
        let draft_dir = self
            .base_dir
            .join("output")
            .join("jianying_drafts")
            .join(episode_id);
        std::fs::create_dir_all(&draft_dir)?;

        let mut video_segments = Vec::new();
        let mut dialogue_segments = Vec::new();
        let mut foley_segments = Vec::new();
        let mut subtitle_segments = Vec::new();
        let mut srt_lines = Vec::new();

        let mut timeline_cursor_us: u64 = 0;

        for (idx, sc) in scenes.iter().enumerate() {
            let raw_dur_sec = if sc.duration == 0 { 8.0 } else { sc.duration as f64 };
            let trim_in = sc.trim_start_sec.unwrap_or(0.0).max(0.0);
            // Default 0.15s tail trim to remove Seedance/Veo end-of-clip audio pop
            let trim_out = sc.trim_end_sec.unwrap_or(0.15).max(0.0);
            let clean_dur_sec = (raw_dur_sec - trim_in - trim_out).max(1.0);
            let dur_us = (clean_dur_sec * 1_000_000.0) as u64;
            let trim_in_us = (trim_in * 1_000_000.0) as u64;

            let start_sec = timeline_cursor_us as f64 / 1_000_000.0;
            let end_sec = (timeline_cursor_us + dur_us) as f64 / 1_000_000.0;

            video_segments.push(serde_json::json!({
                "track": "V1_Clean_Video",
                "scene_id": sc.id,
                "source_clip": format!("output/raw_clips/{}/{}.mp4", episode_id, sc.id),
                "source_trim_start_us": trim_in_us,
                "source_duration_us": dur_us,
                "timeline_start_us": timeline_cursor_us,
                "timeline_duration_us": dur_us,
            }));

            if let Some(ref line) = sc.line {
                if !line.trim().is_empty() {
                    let speaker = sc.speaker.as_deref().unwrap_or("Narrator");
                    dialogue_segments.push(serde_json::json!({
                        "track": "A1_Dialogue_Stem_Qwen3TTS",
                        "scene_id": sc.id,
                        "speaker": speaker,
                        "line": line,
                        "source_wav": format!("output/voiceovers/{}/{}.wav", episode_id, sc.id),
                        "timeline_start_us": timeline_cursor_us,
                        "timeline_duration_us": dur_us,
                        "sidechain_duck_bgm_db": -12.0,
                    }));

                    subtitle_segments.push(serde_json::json!({
                        "track": "T1_Subtitle_WhisperX",
                        "scene_id": sc.id,
                        "speaker": speaker,
                        "text": line,
                        "timeline_start_us": timeline_cursor_us,
                        "timeline_duration_us": dur_us,
                    }));

                    srt_lines.push(format!(
                        "{}\n{} --> {}\n{}\n",
                        idx + 1,
                        format_srt_timestamp(start_sec),
                        format_srt_timestamp(end_sec),
                        line.trim()
                    ));
                }
            }

            foley_segments.push(serde_json::json!({
                "track": "A2_Foley_SFX_MMAudio",
                "scene_id": sc.id,
                "acoustic_space": sc.acoustic_space.as_deref().unwrap_or("interior_room"),
                "foley_cue": sc.foley_cue.as_deref().unwrap_or("Frame-synced cloth and environment foley"),
                "timeline_start_us": timeline_cursor_us,
                "timeline_duration_us": dur_us,
            }));

            timeline_cursor_us += dur_us;
        }

        let draft_json = serde_json::json!({
            "schema": "jianying_capcut_multitrack_v2",
            "episode_id": episode_id,
            "title": title,
            "total_duration_sec": (timeline_cursor_us as f64) / 1_000_000.0,
            "non_destructive_trim_policy": "All clips pre-trimmed (default -0.15s tail glitch guard); BGM and subtitles sit on independent tracks so trimming never breaks musical beats.",
            "open_source_audio_stack": {
                "tts_engine": "Qwen3-TTS-12Hz-1.7B (Base Zero-Shot Voice Cloning + VoiceDesign Emotional Persona Control, CPU Vocoder TDR-Safe)",
                "lip_sync_engine": "MiniMax H3 Audio-Driven Video (A2V Retake Conditioning) / ByteDance LatentSync",
                "foley_sfx_engine": "MiniMax H3 Native Stereo 32kHz Foley + L3 Acoustic Space Low-Pass Filter",
                "bgm_engine": "ACE-Step 1.5 Turbo (48kHz Stereo Film Scoring, CPU OobleckVAE TDR-Safe) + FFmpeg sidechaincompress (-12dB Auto-Ducking)",
            },
            "tracks": {
                "V1_video": video_segments,
                "A1_dialogue": dialogue_segments,
                "A2_foley_sfx": foley_segments,
                "A3_bgm_score": {
                    "track": "A3_BGM_ACEStep15_Ducked",
                    "source_wav": format!("output/bgm/{}_acestep_bgm.wav", episode_id),
                    "timeline_start_us": 0,
                    "timeline_duration_us": timeline_cursor_us,
                    "ducking_filter": "sidechaincompress=threshold=0.04:ratio=5:attack=30:release=350",
                },
                "T1_subtitles": subtitle_segments,
            }
        });

        let draft_file = draft_dir.join("draft_content.json");
        std::fs::write(&draft_file, serde_json::to_string_pretty(&draft_json)?)?;

        let srt_file = draft_dir.join(format!("{}.srt", episode_id));
        std::fs::write(&srt_file, srt_lines.join("\n"))?;

        Ok(draft_dir)
    }
}

fn format_srt_timestamp(sec: f64) -> String {
    let total_ms = (sec.max(0.0) * 1000.0).round() as u64;
    let ms = total_ms % 1000;
    let total_s = total_ms / 1000;
    let s = total_s % 60;
    let total_m = total_s / 60;
    let m = total_m % 60;
    let h = total_m / 60;
    format!("{:02}:{:02}:{:02},{:03}", h, m, s, ms)
}
