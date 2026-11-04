use std::path::PathBuf;
use director_core::{
    agent_plugin::{
        current_os, AgentPluginManifest, AgentPluginRegistry, AgentTaskRequest,
    },
    compiler::format_mmss_ms,
    DirectorLinter, SceneSpec, StoryboardCompiler,
};

#[test]
fn test_current_os_detection() {
    let os = current_os();
    assert!(
        os == "macos" || os == "linux" || os == "windows",
        "OS should be macos, linux, or windows, got {}",
        os
    );
}

#[test]
fn test_format_mmss_ms() {
    assert_eq!(format_mmss_ms(0.0), "00:00.000");
    assert_eq!(format_mmss_ms(1.1), "00:01.100");
    assert_eq!(format_mmss_ms(2.425), "00:02.425");
    assert_eq!(format_mmss_ms(65.123), "01:05.123");
}

#[test]
fn test_4beat_compiler_output() {
    let compiler = StoryboardCompiler { characters: vec![] };
    let sc = SceneSpec {
        id: "test_shot_01".to_string(),
        duration: 8,
        action: "Chancellor looks over the military map in candlelit tent.".to_string(),
        facial_progression: Some("brow glabella micro-tension relaxes, eyelids widen into sharp focus, jaw sets firmly".to_string()),
        prop_interaction: Some("fingers gripping white crane feather fan".to_string()),
        listener_reaction: Some("general nods with respectful chest inhalation".to_string()),
        env_micro_physics: Some("candle wick flickering in brass saucer, breath mist curling".to_string()),
        sub_beat_emotions: vec![
            "composed_restraint:0.35".to_string(),
            "pause:300ms".to_string(),
            "decisive_command:0.85".to_string(),
        ],
        ..Default::default()
    };

    let desc = compiler.compile_4beat_micro_acting_description(&sc, 90);
    // 90 frames / 24 = 3.75s
    assert!(desc.contains("During 00:00.000–00:01.100"), "Missing Beat 1 timestamp: {}", desc);
    assert!(desc.contains("Beat 1: Subtext & Preparatory Airlock"), "Missing Beat 1 title: {}", desc);
    assert!(desc.contains("Beat 2: Opening Delivery & Micro-Expression Shift"), "Missing Beat 2 title: {}", desc);
    assert!(desc.contains("Beat 3: Climax Accent, Tactile Prop Force & Active Listener Reaction"), "Missing Beat 3 title: {}", desc);
    assert!(desc.contains("Beat 4: Emotional Resonance & Environmental Micro-Physics Tail Anchor"), "Missing Beat 4 title: {}", desc);
    assert!(desc.contains("During 00:01.100–"), "Missing Beat 2 start window: {}", desc);
    assert!(desc.contains("Sub-beat emotion trajectory"), "Missing sub-beat emotion arc: {}", desc);
}

#[test]
fn test_4beat_compiler_with_custom_beats() {
    let compiler = StoryboardCompiler { characters: vec![] };
    let sc = SceneSpec {
        id: "custom_beats_shot".to_string(),
        micro_beats: vec![
            "During 00:00.000–00:01.100: Custom airlock hold with lips closed.".to_string(),
            "During 00:01.100–00:02.300: Custom delivery opening.".to_string(),
            "During 00:02.300–00:03.200: Custom climax tactile force.".to_string(),
            "During 00:03.200–00:03.750: Custom latent relay anchor.".to_string(),
        ],
        ..Default::default()
    };

    let desc = compiler.compile_4beat_micro_acting_description(&sc, 90);
    assert!(desc.contains("Custom airlock hold"));
    assert!(desc.contains("Custom delivery opening"));
    assert!(desc.contains("Custom climax tactile force"));
    assert!(desc.contains("Custom latent relay anchor"));
}

#[test]
fn test_h3_prompt_no_robotic_stationary_lock() {
    let compiler = StoryboardCompiler { characters: vec![] };
    let sc = SceneSpec {
        id: "natural_shot".to_string(),
        duration: 8,
        action: "A dignified strategist reviews battle plan.".to_string(),
        facial_progression: Some("brow glabella tightens slightly".to_string()),
        ..Default::default()
    };
    let fact_sheet = director_core::FactSheet::default();
    let prompt_val = compiler.compile_h3_prompt_block(&sc, &fact_sheet);
    let prompt_str = prompt_val
        .get("prompt")
        .and_then(|p: &serde_json::Value| p.as_str())
        .unwrap_or("");

    // Robotic wooden statue locks must NOT be present
    assert!(!prompt_str.contains("with head held completely level and stationary"));
    assert!(!prompt_str.contains("settles into a stationary hold"));

    // Natural headroom and eye-line preservation MUST be present
    assert!(prompt_str.contains("Maintain natural headroom and axis preservation"));
    assert!(prompt_str.contains("steady eye-line axis"));
}

#[test]
fn test_linter_rule_h3_5_micro_acting_lock() {
    let linter = DirectorLinter::new(PathBuf::from("."));

    // 1. Scene without any micro-acting cues or fields should trigger Rule H3-5
    let bare_scene = SceneSpec {
        id: "shot_bare".to_string(),
        action: "A man stands in the room.".to_string(),
        framing: "medium".to_string(),
        duration: 8,
        ..Default::default()
    };
    let report_bare = linter.lint_scenes("test_bare", &[bare_scene]);
    assert!(
        report_bare
            .issues
            .iter()
            .any(|i| i.layer.contains("L4-微表演与四节拍细节密度锁")),
        "Expected L4 Rule H3-5 warning on bare scene, but issues were: {:?}",
        report_bare.issues
    );

    // 2. Scene with facial_progression and prop_interaction should PASS Rule H3-5
    let enriched_scene = SceneSpec {
        id: "shot_enriched".to_string(),
        action: "Strategist studies the parchment.".to_string(),
        framing: "medium".to_string(),
        duration: 8,
        facial_progression: Some("brow glabella tightens with inhalation, eyelids narrow in focus".to_string()),
        prop_interaction: Some("fingers gripping edge of parchment".to_string()),
        env_micro_physics: Some("candle flame trembling, breath mist drifting".to_string()),
        ..Default::default()
    };
    let report_enriched = linter.lint_scenes("test_enriched", &[enriched_scene]);
    assert!(
        !report_enriched
            .issues
            .iter()
            .any(|i| i.layer.contains("L4-微表演与四节拍细节密度锁")),
        "Expected 0 H3-5 issues for enriched scene, but got: {:?}",
        report_enriched.issues
    );
}

#[test]
fn test_linter_rule_h3_3_negative_leakage() {
    let linter = DirectorLinter::new(PathBuf::from("."));
    let negative_scene = SceneSpec {
        id: "shot_neg".to_string(),
        action: "The actor speaks without turning her face away from center.".to_string(),
        framing: "medium".to_string(),
        duration: 8,
        facial_progression: Some("brow glabella tightens".to_string()),
        ..Default::default()
    };
    let report = linter.lint_scenes("test_neg", &[negative_scene]);
    assert!(
        report
            .issues
            .iter()
            .any(|i| i.layer.contains("L4-H3正言锁头律")),
        "Expected H3-3 warning on negative phrasing, got: {:?}",
        report.issues
    );
}

#[test]
fn test_agent_plugin_manifest_serde() {
    let manifest_toml = r#"
id = "custom-agent"
name = "Custom Agent CLI"
kind = "custom_cli"
command = "custom_agent"
args_template = ["--task", "{task_type}", "--prompt", "{prompt}"]
capabilities = ["expand_micro_acting", "polish_scene"]
enabled = true
priority = 88
os_targets = ["macos", "linux", "windows"]
description = "Custom autonomous agent"
"#;

    let parsed: AgentPluginManifest = toml::from_str(manifest_toml).expect("Failed to parse TOML manifest");
    assert_eq!(parsed.id, "custom-agent");
    assert_eq!(parsed.kind, "custom_cli");
    assert_eq!(parsed.priority, 88);
    assert!(parsed.capabilities.contains(&"expand_micro_acting".to_string()));
    assert!(parsed.is_available_on_current_os());
}

#[test]
fn test_agent_plugin_registry_builtin_and_load() {
    let mut registry = AgentPluginRegistry::new();
    let plugins = registry.list_plugins();

    // Verify all core builtin adapters are registered
    assert!(registry.get_plugin("antigravity").is_some(), "Antigravity plugin missing");
    assert!(registry.get_plugin("codex").is_some(), "Codex plugin missing");
    assert!(registry.get_plugin("claude-code").is_some(), "Claude Code plugin missing");
    assert!(registry.get_plugin("gemini-cli").is_some(), "Gemini CLI plugin missing");
    assert!(registry.get_plugin("colab-operator").is_some(), "Colab operator missing");
    assert!(registry.get_plugin("openai-http").is_some(), "OpenAI HTTP missing");

    // Test priority sorting (antigravity=100 > codex=90 > claude-code=85 > gemini-cli=80)
    assert!(plugins[0].priority >= plugins[1].priority);

    // Test loading sample manifests from workspace plugins/agents/
    let ws_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf();
    let plugins_dir = ws_root.join("plugins").join("agents");
    if plugins_dir.exists() {
        let count = registry.load_from_dir(&plugins_dir);
        assert!(count >= 3, "Expected to load at least 3 manifests from plugins/agents, loaded {}", count);
    }
}

#[test]
fn test_agent_task_request_selection() {
    let registry = AgentPluginRegistry::new();
    let req = AgentTaskRequest {
        task_type: "expand_micro_acting".to_string(),
        prompt: "Generate 4-beat micro acting for scene 1".to_string(),
        workspace_dir: None,
        preferred_plugin: Some("openai-http".to_string()),
        conversation_id: None,
        extra_context: None,
    };
    let plugin = registry.select_plugin_for_task(&req);
    assert!(plugin.is_some());
    assert_eq!(plugin.unwrap().id, "openai-http");
}

#[test]
fn test_episodes_lint_cleanly() {
    let ws_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf();

    let linter = DirectorLinter::new(&ws_root);

    let ep02_path = ws_root.join("episodes").join("ep02_orientation").join("movie.toml");
    if ep02_path.exists() {
        let report = linter.lint_manifest_file(&ep02_path).expect("Failed to lint ep02");
        assert!(
            report.passed,
            "ep02_orientation failed lint: error_count={}, issues: {:?}",
            report.error_count, report.issues
        );
        assert_eq!(report.error_count, 0, "ep02_orientation should have 0 errors");
    }

    let ep04_path = ws_root.join("episodes").join("ep04_beifa").join("movie.toml");
    if ep04_path.exists() {
        let report = linter.lint_manifest_file(&ep04_path).expect("Failed to lint ep04");
        assert!(
            report.passed,
            "ep04_beifa failed lint: error_count={}, issues: {:?}",
            report.error_count, report.issues
        );
        assert_eq!(report.error_count, 0, "ep04_beifa should have 0 errors");
    }

    let alien_thief_root = ws_root.join("projects").join("alien_thief");
    let alien_thief_manifest = alien_thief_root.join("episodes").join("ep01_lottery_heist").join("movie.toml");
    if alien_thief_manifest.exists() {
        let alien_linter = DirectorLinter::new(&alien_thief_root);
        let report = alien_linter.lint_manifest_file(&alien_thief_manifest).expect("Failed to lint alien_thief ep01");
        assert!(
            report.passed,
            "alien_thief ep01 failed lint: error_count={}, issues: {:?}",
            report.error_count, report.issues
        );
        assert_eq!(report.error_count, 0, "alien_thief ep01 should have 0 errors");
        assert_eq!(report.issues.len(), 0, "alien_thief ep01 should have 0 warnings and 0 errors");
    }
}
