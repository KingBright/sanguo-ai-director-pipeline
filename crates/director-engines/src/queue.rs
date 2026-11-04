use std::sync::Arc;

use chrono::Local;
use serde::{Deserialize, Serialize};
use tokio::sync::{broadcast, Mutex, OwnedSemaphorePermit, RwLock, Semaphore};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParallelConcurrencyConfig {
    pub flow_concurrency: usize,
    pub colab_g4_concurrency: usize,
    pub sume_concurrency: usize,
    pub audio_tts_concurrency: usize,
    pub local_rocm_concurrency: usize,
}

impl Default for ParallelConcurrencyConfig {
    fn default() -> Self {
        Self {
            flow_concurrency: 8,
            colab_g4_concurrency: 4,
            sume_concurrency: 8,
            audio_tts_concurrency: 6,
            local_rocm_concurrency: 2,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LaneUtilization {
    pub flow_active: usize,
    pub flow_max: usize,
    pub colab_g4_active: usize,
    pub colab_g4_max: usize,
    pub sume_active: usize,
    pub sume_max: usize,
    pub audio_tts_active: usize,
    pub audio_tts_max: usize,
    pub local_rocm_active: usize,
    pub local_rocm_max: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum JobStatus {
    PendingApproval,
    Queued,
    Running,
    Completed,
    Failed,
    Rejected,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RenderJob {
    pub id: String,
    pub created_at: String,
    pub requested_by: String,
    pub episode_id: String,
    pub scene_id: Option<String>,
    pub model: String,
    pub engine: String, // "h3", "flow", "sume", "colab"
    pub dry_run: bool,
    pub estimated_credits: i64,
    pub status: JobStatus,
    pub progress_message: String,
    pub output_video_url: Option<String>,
    pub log_tail: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StudioEvent {
    pub timestamp: String,
    pub event_type: String,
    pub job_id: Option<String>,
    pub message: String,
    pub status: Option<JobStatus>,
}

#[derive(Clone)]
pub struct RenderQueue {
    pub jobs: Arc<RwLock<Vec<RenderJob>>>,
    pub gpu_lock: Arc<Mutex<()>>,
    pub event_tx: broadcast::Sender<StudioEvent>,
    pub require_approval_for_quality: Arc<RwLock<bool>>,
    pub daily_credit_limit_per_member: Arc<RwLock<i64>>,
    pub concurrency_config: Arc<RwLock<ParallelConcurrencyConfig>>,
    pub flow_semaphore: Arc<RwLock<Arc<Semaphore>>>,
    pub colab_g4_semaphore: Arc<RwLock<Arc<Semaphore>>>,
    pub sume_semaphore: Arc<RwLock<Arc<Semaphore>>>,
    pub audio_tts_semaphore: Arc<RwLock<Arc<Semaphore>>>,
    pub local_rocm_semaphore: Arc<RwLock<Arc<Semaphore>>>,
}

impl RenderQueue {
    pub fn new() -> Self {
        Self::with_config(ParallelConcurrencyConfig::default())
    }

    pub fn with_config(cfg: ParallelConcurrencyConfig) -> Self {
        let (event_tx, _) = broadcast::channel(256);
        Self {
            jobs: Arc::new(RwLock::new(Vec::new())),
            gpu_lock: Arc::new(Mutex::new(())),
            event_tx,
            require_approval_for_quality: Arc::new(RwLock::new(true)),
            daily_credit_limit_per_member: Arc::new(RwLock::new(300)),
            concurrency_config: Arc::new(RwLock::new(cfg.clone())),
            flow_semaphore: Arc::new(RwLock::new(Arc::new(Semaphore::new(cfg.flow_concurrency)))),
            colab_g4_semaphore: Arc::new(RwLock::new(Arc::new(Semaphore::new(cfg.colab_g4_concurrency)))),
            sume_semaphore: Arc::new(RwLock::new(Arc::new(Semaphore::new(cfg.sume_concurrency)))),
            audio_tts_semaphore: Arc::new(RwLock::new(Arc::new(Semaphore::new(cfg.audio_tts_concurrency)))),
            local_rocm_semaphore: Arc::new(RwLock::new(Arc::new(Semaphore::new(cfg.local_rocm_concurrency)))),
        }
    }

    pub async fn acquire_lane_permit(&self, lane: &str) -> OwnedSemaphorePermit {
        let sem = match lane {
            "flow" => self.flow_semaphore.read().await.clone(),
            "colab" | "colab_g4" => self.colab_g4_semaphore.read().await.clone(),
            "sume" => self.sume_semaphore.read().await.clone(),
            "audio" | "audio_tts" | "music" => self.audio_tts_semaphore.read().await.clone(),
            "h3" | "local_rocm" | "rocm" => self.local_rocm_semaphore.read().await.clone(),
            _ => self.flow_semaphore.read().await.clone(),
        };
        sem.acquire_owned().await.expect("Semaphore should not be closed")
    }

    pub async fn get_lane_utilization(&self) -> LaneUtilization {
        let cfg = self.concurrency_config.read().await.clone();
        let flow_sem = self.flow_semaphore.read().await.clone();
        let colab_sem = self.colab_g4_semaphore.read().await.clone();
        let sume_sem = self.sume_semaphore.read().await.clone();
        let audio_sem = self.audio_tts_semaphore.read().await.clone();
        let rocm_sem = self.local_rocm_semaphore.read().await.clone();

        LaneUtilization {
            flow_active: cfg.flow_concurrency.saturating_sub(flow_sem.available_permits()),
            flow_max: cfg.flow_concurrency,
            colab_g4_active: cfg.colab_g4_concurrency.saturating_sub(colab_sem.available_permits()),
            colab_g4_max: cfg.colab_g4_concurrency,
            sume_active: cfg.sume_concurrency.saturating_sub(sume_sem.available_permits()),
            sume_max: cfg.sume_concurrency,
            audio_tts_active: cfg.audio_tts_concurrency.saturating_sub(audio_sem.available_permits()),
            audio_tts_max: cfg.audio_tts_concurrency,
            local_rocm_active: cfg.local_rocm_concurrency.saturating_sub(rocm_sem.available_permits()),
            local_rocm_max: cfg.local_rocm_concurrency,
        }
    }

    pub async fn update_concurrency_config(&self, new_cfg: ParallelConcurrencyConfig) {
        let mut cfg = self.concurrency_config.write().await;
        *cfg = new_cfg.clone();
        *self.flow_semaphore.write().await = Arc::new(Semaphore::new(new_cfg.flow_concurrency));
        *self.colab_g4_semaphore.write().await = Arc::new(Semaphore::new(new_cfg.colab_g4_concurrency));
        *self.sume_semaphore.write().await = Arc::new(Semaphore::new(new_cfg.sume_concurrency));
        *self.audio_tts_semaphore.write().await = Arc::new(Semaphore::new(new_cfg.audio_tts_concurrency));
        *self.local_rocm_semaphore.write().await = Arc::new(Semaphore::new(new_cfg.local_rocm_concurrency));
    }

    pub fn emit(&self, event_type: &str, job_id: Option<String>, message: impl Into<String>, status: Option<JobStatus>) {
        let evt = StudioEvent {
            timestamp: Local::now().format("%H:%M:%S").to_string(),
            event_type: event_type.to_string(),
            job_id,
            message: message.into(),
            status,
        };
        let _ = self.event_tx.send(evt);
    }

    pub fn estimate_model_credits(model: &str, scene_count: usize, dry_run: bool) -> i64 {
        if dry_run {
            return 0;
        }
        let per_clip = match model {
            "minimax-h3" | "h3" => 0,
            "heygen-video-1" | "sume:heygen-video-1" => 1,
            "latentsync" | "sume:latentsync" | "kling-lipsync" => 1,
            "seedance-2-mini" | "sume:seedance-2-mini" | "vidu-q4-reference" => 3,
            "seedance-2-fast" | "sume:seedance-2-fast" | "wan-3.0" | "sume:wan-3.0" => 4,
            "seedance-2" | "sume:seedance-2" | "sume:minimax-h3-max" | "minimax-h3-max" => 5,
            "seedance-2.5" | "sume:seedance-2.5" | "omnihuman-2" => 8,
            "kling-4" | "kling-4-omni" | "sume:kling-4-omni" => 12,
            "veo-lite" => 5,
            "veo-fast" => 10,
            "omni-flash" => 12,
            "veo-quality" => 100,
            _ => 10,
        };
        per_clip * (scene_count.max(1) as i64)
    }

    pub async fn enqueue_job(
        &self,
        requested_by: String,
        episode_id: String,
        scene_id: Option<String>,
        model: String,
        dry_run: bool,
        scene_count: usize,
        is_admin_approved: bool,
    ) -> RenderJob {
        let engine = if model == "minimax-h3" || model == "h3" {
            "h3".to_string()
        } else if crate::sume_router::SumeEngine::is_sume_model(&model) {
            "sume".to_string()
        } else {
            "flow".to_string()
        };
        let estimated_credits = Self::estimate_model_credits(&model, scene_count, dry_run);
        let need_approval = *self.require_approval_for_quality.read().await
            && model == "veo-quality"
            && !dry_run
            && !is_admin_approved;

        let status = if need_approval {
            JobStatus::PendingApproval
        } else {
            JobStatus::Queued
        };

        let progress_message = if need_approval {
            format!(
                "👑 申请使用旗舰 Veo 3.1 Quality (预计消耗 {} 点)，等待管理员确认后开跑",
                estimated_credits
            )
        } else {
            "已加入制片队列，准备调度引擎...".to_string()
        };

        let job = RenderJob {
            id: Uuid::new_v4().to_string()[..8].to_string(),
            created_at: Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
            requested_by,
            episode_id,
            scene_id,
            model,
            engine,
            dry_run,
            estimated_credits,
            status: status.clone(),
            progress_message: progress_message.clone(),
            output_video_url: None,
            log_tail: String::new(),
        };

        self.jobs.write().await.insert(0, job.clone());
        self.emit(
            "job_created",
            Some(job.id.clone()),
            progress_message,
            Some(status),
        );
        job
    }

    pub async fn update_job_status(
        &self,
        job_id: &str,
        status: JobStatus,
        progress_message: impl Into<String>,
        output_video_url: Option<String>,
        log_tail: Option<String>,
    ) {
        let msg = progress_message.into();
        let mut jobs = self.jobs.write().await;
        if let Some(j) = jobs.iter_mut().find(|j| j.id == job_id) {
            j.status = status.clone();
            j.progress_message = msg.clone();
            if output_video_url.is_some() {
                j.output_video_url = output_video_url;
            }
            if let Some(l) = log_tail {
                j.log_tail = l;
            }
        }
        drop(jobs);
        self.emit("job_updated", Some(job_id.to_string()), msg, Some(status));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_render_queue_parallel_concurrency_lanes() {
        let queue = RenderQueue::new();
        let util = queue.get_lane_utilization().await;
        assert_eq!(util.flow_max, 8);
        assert_eq!(util.colab_g4_max, 4);
        assert_eq!(util.sume_max, 8);
        assert_eq!(util.audio_tts_max, 6);
        assert_eq!(util.local_rocm_max, 2);
        assert_eq!(util.flow_active, 0);

        // Test acquiring permits concurrently
        let p1 = queue.acquire_lane_permit("flow").await;
        let p2 = queue.acquire_lane_permit("flow").await;
        let util2 = queue.get_lane_utilization().await;
        assert_eq!(util2.flow_active, 2);

        let p_colab = queue.acquire_lane_permit("colab_g4").await;
        let util3 = queue.get_lane_utilization().await;
        assert_eq!(util3.colab_g4_active, 1);

        drop(p1);
        drop(p2);
        drop(p_colab);
        let util4 = queue.get_lane_utilization().await;
        assert_eq!(util4.flow_active, 0);
        assert_eq!(util4.colab_g4_active, 0);
    }
}
