pub const INDEX_HTML: &str = r##"<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <title>AetherDirector Studio — 天枢 AI 影视工业工作台</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-app: #09090b;
      --bg-sidebar: #0d0d10;
      --bg-surface: #131317;
      --bg-surface-hover: #19191f;
      --bg-elevated: #1c1c22;
      --bg-input: #0a0a0d;
      --border-hairline: rgba(255, 255, 255, 0.08);
      --border-strong: rgba(255, 255, 255, 0.16);
      --text-main: #f4f4f5;
      --text-sub: #a1a1aa;
      --text-muted: #71717a;
      --safe-bottom: env(safe-area-inset-bottom, 0px);
    }

    * {
      box-sizing: border-box;
      -webkit-tap-highlight-color: transparent;
    }

    body {
      background-color: var(--bg-app);
      color: var(--text-main);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
      -webkit-font-smoothing: antialiased;
      margin: 0;
      height: 100dvh;
      overflow: hidden;
    }

    .font-mono {
      font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
    }

    /* 细腻高光面板 */
    .surface-card {
      background-color: var(--bg-surface);
      border: 1px solid var(--border-hairline);
      box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.04), 0 4px 20px -4px rgba(0, 0, 0, 0.45);
      border-radius: 12px;
      transition: border-color 0.18s ease, box-shadow 0.18s ease;
    }
    .surface-card-selected {
      border-color: rgba(255, 255, 255, 0.36) !important;
      box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.08), 0 0 0 1px rgba(255, 255, 255, 0.12), 0 8px 28px -6px rgba(0, 0, 0, 0.6);
    }

    /* 表单控件：在移动端强制 >= 16px 字号防止 iOS 自动放大视口 */
    .field-input {
      background-color: var(--bg-input);
      border: 1px solid var(--border-hairline);
      color: var(--text-main);
      border-radius: 8px;
      transition: all 0.15s ease;
    }
    @media (max-width: 767px) {
      input.field-input, textarea.field-input, select.field-input {
        font-size: 16px !important;
      }
    }
    .field-input:focus {
      outline: none;
      border-color: rgba(255, 255, 255, 0.38);
      box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.06);
    }

    /* 按钮系统 */
    .btn-white {
      background: #f4f4f5;
      color: #09090b;
      font-weight: 600;
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.8);
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }
    .btn-white:active { transform: scale(0.98); }

    .btn-ghost {
      background: rgba(255, 255, 255, 0.04);
      color: #d4d4d8;
      border: 1px solid var(--border-hairline);
      border-radius: 8px;
      font-weight: 500;
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }
    .btn-ghost:active { background: rgba(255, 255, 255, 0.1); }

    /* 桌面端分段控制器 */
    .seg-group {
      background: #0c0c0f;
      border: 1px solid var(--border-hairline);
      padding: 3px;
      border-radius: 10px;
      display: inline-flex;
      gap: 2px;
    }
    .seg-btn {
      padding: 6px 12px;
      border-radius: 7px;
      font-size: 12px;
      font-weight: 500;
      color: var(--text-sub);
      transition: all 0.16s ease;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
    }
    .seg-btn.active {
      background: #1f1f26;
      color: #ffffff;
      box-shadow: 0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06);
    }

    /* 隐藏横向滚动条但保留滑动 */
    .no-scrollbar::-webkit-scrollbar { display: none; }
    .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }

    /* 抽屉动画 */
    .drawer-backdrop {
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.22s ease;
    }
    .drawer-backdrop.open {
      opacity: 1;
      pointer-events: auto;
    }
    .drawer-panel-right {
      transform: translateX(100%);
      transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .drawer-backdrop.open .drawer-panel-right {
      transform: translateX(0);
    }
    .drawer-panel-bottom {
      transform: translateY(100%);
      transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .drawer-backdrop.open .drawer-panel-bottom {
      transform: translateY(0);
    }

    /* 移动端安全区适配 */
    .pb-safe {
      padding-bottom: calc(0.5rem + var(--safe-bottom));
    }

    @keyframes toastIn {
      from { opacity: 0; transform: translateY(10px) scale(0.97); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    .toast-item {
      animation: toastIn 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.14); border-radius: 9999px; }
  </style>
</head>
<body class="flex flex-col selection:bg-zinc-700 selection:text-white">

  <!-- Toast 通知容器：在移动端避开底部导航栏 -->
  <div id="toastContainer" class="fixed bottom-20 lg:bottom-5 right-4 left-4 sm:left-auto sm:w-80 z-[95] flex flex-col gap-2 pointer-events-none"></div>

  <!-- 顶部主工作栏 (响应式自适应) -->
  <header class="h-13 md:h-14 shrink-0 bg-[#0c0c0f]/95 backdrop-blur-md border-b border-white/[0.07] px-3 md:px-4 flex items-center justify-between gap-2 z-30">
    <!-- 左区：品牌 + 项目切换器 -->
    <div class="flex items-center gap-2 min-w-0 flex-1 lg:flex-initial">
      <div class="w-7 h-7 rounded-lg bg-zinc-100 text-zinc-950 flex items-center justify-center font-mono font-bold text-xs shrink-0">
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <rect x="2" y="3" width="20" height="18" rx="3"/>
          <path d="M7 3v18M17 3v18M2 9h5M2 15h5M17 9h5M17 15h5"/>
        </svg>
      </div>
      <span class="text-sm font-semibold tracking-tight text-zinc-100 hidden md:inline shrink-0">AetherDirector Studio</span>
      <span class="text-zinc-700 text-sm hidden md:inline">/</span>

      <!-- 项目下拉选择与新建按钮 -->
      <div class="flex items-center gap-1.5 min-w-0 flex-1 sm:flex-initial">
        <div class="relative min-w-0 flex-1 sm:w-52 md:w-64">
          <select id="projectSwitcher" onchange="switchProject(this.value)" class="w-full appearance-none pl-2.5 pr-7 py-1.5 rounded-lg bg-zinc-900/90 border border-white/[0.08] text-xs font-medium text-zinc-100 truncate cursor-pointer focus:outline-none">
          </select>
          <svg class="w-3.5 h-3.5 text-zinc-400 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg>
        </div>
        <button onclick="openNewProjectModal()" title="新建独立项目" class="px-2.5 py-1.5 btn-ghost text-xs shrink-0">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
          <span class="hidden sm:inline">新项目</span>
        </button>
      </div>
    </div>

    <!-- 中区：桌面端 Segmented 主视图切换器 (移动端隐藏，改用底部 TabBar) -->
    <div class="seg-group hidden lg:inline-flex">
      <button onclick="switchTab('studio')" id="tabBtn-studio" class="seg-btn active">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M3 10h6M3 15h6"/></svg>
        <span>分镜工作台</span>
      </button>
      <button onclick="switchTab('assets')" id="tabBtn-assets" class="seg-btn">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M20 7h-9m9 10h-9M4 7h.01M4 17h.01"/><rect x="3" y="4" width="18" height="6" rx="1"/><rect x="3" y="14" width="18" height="6" rx="1"/></svg>
        <span>项目资产中心</span>
        <span id="assetSummaryBadge" class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-white/[0.06] text-zinc-300">0</span>
      </button>
      <button onclick="switchTab('theater')" id="tabBtn-theater" class="seg-btn">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
        <span>成片与素材库</span>
        <span id="finalVideoCount" class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-white/[0.06] text-zinc-300">0</span>
      </button>
      <button onclick="switchTab('queue')" id="tabBtn-queue" class="seg-btn">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4"/></svg>
        <span>任务与配额</span>
        <span id="pendingBadge" class="hidden px-1.5 py-0.2 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[10px] font-mono">0</span>
      </button>
    </div>

    <!-- 右区：算力/积分 + 算力与配额详情 + AI 助手抽屉 + 新建剧集 -->
    <div class="flex items-center gap-1.5 shrink-0">
      <div class="hidden xl:flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-zinc-900/90 border border-white/[0.08] text-[11px] font-mono shadow-sm">
        <span class="flex items-center gap-1.5 text-zinc-300" title="本机 GPU / 渲染引擎">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          <span id="gpuBadge">Strix Halo</span>
        </span>
        <span class="text-zinc-700">|</span>
        <span class="flex items-center gap-1.5 text-sky-300" title="Google Colab Ultra Cloud GPU 算力池 (1,873 CCU)">
          <span class="w-1.5 h-1.5 rounded-full bg-sky-400"></span>
          <span>Colab <strong id="topColabBadge" class="text-sky-200">1,873 CCU</strong></span>
        </span>
        <span class="text-zinc-700">|</span>
        <span class="flex items-center gap-1.5 text-amber-300" title="Google Flow 视频与定妆积分 (9,895 Credits)">
          <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
          <span>Flow <strong id="creditBalance" class="text-amber-200">9,895 Cr</strong></span>
        </span>
        <span class="text-zinc-700">|</span>
        <span class="flex items-center gap-1.5 text-purple-300" title="Google Flow Music (MusicFX / Lyria 2 + ACE-Step 1.5)">
          <span class="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
          <span id="topMusicBadge">Lyria/ACE Ready</span>
        </span>
        <span id="creditCapacity" class="text-zinc-500 hidden 2xl:inline"></span>
      </div>

      <button onclick="openQuotaModal()" class="px-2.5 py-1.5 rounded-lg bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/30 text-indigo-300 hover:text-indigo-200 text-xs font-medium flex items-center gap-1.5 transition shadow-sm" title="三合一算力与配额监控中心 (Colab · Google Flow · Flow Music)">
        <svg class="w-3.5 h-3.5 text-indigo-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>
        <span class="font-medium">📊 算力与配额详情</span>
      </button>

      <button onclick="toggleCopilotDrawer(true)" class="px-2.5 py-1.5 btn-ghost text-xs relative" title="AI 导演助手与 L1-L5 门禁诊断">
        <svg class="w-4 h-4 text-zinc-300" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <span class="hidden md:inline">AI 助手</span>
        <span id="headerLintDot" class="w-2 h-2 rounded-full bg-emerald-400"></span>
      </button>

      <button onclick="openNewEpisodeModal()" class="px-2.5 md:px-3.5 py-1.5 btn-white text-xs">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
        <span>新剧集</span>
      </button>
    </div>
  </header>

  <!-- 主工作区容器 (自适应桌面端与移动端高度) -->
  <div class="flex-1 flex overflow-hidden relative">

    <!-- ==================== VIEW 1: 分镜工作台 (Studio Workbench) ==================== -->
    <section id="tab-studio" class="flex-1 flex flex-col lg:flex-row overflow-hidden">

      <!-- 桌面端左侧固定栏 (仅 lg 及以上显示) -->
      <aside class="hidden lg:flex w-72 shrink-0 bg-[#0d0d10] border-r border-white/[0.06] flex-col justify-between overflow-y-auto p-4 gap-4">
        <div class="space-y-4">
          <div class="surface-card p-3.5 space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-mono uppercase tracking-wider text-zinc-500">ACTIVE PROJECT</span>
              <button onclick="switchTab('assets')" class="text-[11px] text-zinc-400 hover:text-zinc-100 transition">管理资产 →</button>
            </div>
            <div>
              <div id="activeProjectCardTitle" class="text-sm font-semibold text-zinc-100 truncate">加载中...</div>
              <div id="activeProjectCardSub" class="text-[11px] text-zinc-500 mt-0.5 truncate"></div>
            </div>
            <div class="grid grid-cols-4 gap-1.5 text-center">
              <button onclick="switchTab('assets'); switchAssetSubTab('chars')" class="p-1.5 rounded-lg bg-zinc-900/80 hover:bg-zinc-800/80 border border-white/[0.05] transition">
                <div id="statChars" class="font-mono font-semibold text-zinc-100 text-xs">0</div>
                <div class="text-[10px] text-zinc-500">角色</div>
              </button>
              <button onclick="switchTab('assets'); switchAssetSubTab('images')" class="p-1.5 rounded-lg bg-zinc-900/80 hover:bg-zinc-800/80 border border-white/[0.05] transition">
                <div id="statImages" class="font-mono font-semibold text-zinc-100 text-xs">0</div>
                <div class="text-[10px] text-zinc-500">母图</div>
              </button>
              <button onclick="switchTab('assets'); switchAssetSubTab('rooms')" class="p-1.5 rounded-lg bg-zinc-900/80 hover:bg-zinc-800/80 border border-white/[0.05] transition">
                <div id="statRooms" class="font-mono font-semibold text-zinc-100 text-xs">0</div>
                <div class="text-[10px] text-zinc-500">空间</div>
              </button>
              <button onclick="switchTab('theater')" class="p-1.5 rounded-lg bg-zinc-900/80 hover:bg-zinc-800/80 border border-white/[0.05] transition">
                <div id="statClips" class="font-mono font-semibold text-zinc-100 text-xs">0</div>
                <div class="text-[10px] text-zinc-500">视频</div>
              </button>
            </div>
          </div>

          <div class="space-y-2">
            <div class="flex items-center justify-between px-1">
              <span class="text-[11px] font-medium text-zinc-400">剧集工程列表</span>
              <button onclick="openNewEpisodeModal()" class="text-[11px] text-zinc-400 hover:text-white">+ 新建</button>
            </div>
            <div id="episodeList" class="space-y-1.5"></div>
          </div>
        </div>

        <div class="surface-card p-3.5 space-y-2.5">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-zinc-200">整集渲染输出</span>
            <input id="memberNameInput" type="text" value="主创导演" title="提交人署名" class="w-24 px-2 py-0.5 rounded field-input text-[11px] text-right text-zinc-300" />
          </div>
          <div class="space-y-1.5">
            <button onclick="submitEpisodeRender('minimax-h3', false)" class="w-full py-2 px-3 btn-ghost text-xs flex items-center justify-between">
              <span class="flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                <span>本机 H3 预演整集</span>
              </span>
              <span class="font-mono text-[10px] text-emerald-400">FREE</span>
            </button>
            <button onclick="submitEpisodeRender('veo-fast', false)" class="w-full py-2 px-3 btn-ghost text-xs flex items-center justify-between">
              <span>云端 Veo Fast 成片</span>
              <span class="font-mono text-[10px] text-zinc-400">10/镜</span>
            </button>
            <button onclick="submitEpisodeRender('veo-quality', false)" class="w-full py-2 px-3 btn-white text-xs flex items-center justify-between">
              <span>Veo 3.1 Quality 母带</span>
              <span class="font-mono text-[10px] opacity-70">100/镜</span>
            </button>
            <button onclick="submitEpisodeRender('heygen-video-1', false)" class="w-full py-2 px-3 btn-ghost text-xs flex items-center justify-between border border-emerald-500/20">
              <span>Sume · HeyGen Video 1</span>
              <span class="font-mono text-[10px] text-emerald-400">礼券/低价</span>
            </button>
            <button onclick="submitEpisodeRender('seedance-2.5', false)" class="w-full py-2 px-3 btn-ghost text-xs flex items-center justify-between">
              <span>Sume · Seedance 2.5</span>
              <span class="font-mono text-[10px] text-zinc-400">半价直连</span>
            </button>
          </div>
        </div>
      </aside>

      <!-- 主分镜画布区 (移动端 + 桌面端共用) -->
      <div class="flex-1 flex flex-col overflow-hidden bg-[#09090b]">
        <!-- 移动端专属：剧集横向滑动胶囊条 + 整集制片快捷按钮 (仅 <lg 显示) -->
        <div class="lg:hidden shrink-0 bg-[#0d0d10] border-b border-white/[0.06] px-3 py-2 flex items-center justify-between gap-2">
          <div id="mobileEpisodePills" class="flex items-center gap-1.5 overflow-x-auto no-scrollbar flex-1 py-0.5"></div>
          <button onclick="toggleMobileRenderSheet(true)" class="px-2.5 py-1.5 rounded-lg bg-zinc-100 text-zinc-950 font-semibold text-xs shrink-0 flex items-center gap-1 shadow">
            <span>🎬 整集制片</span>
          </button>
        </div>

        <!-- 画布固定工具栏 -->
        <div class="shrink-0 border-b border-white/[0.06] bg-[#0c0c0f]/90 px-3 md:px-6 py-2.5 space-y-2">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="flex items-center gap-2 min-w-0 flex-1">
              <h2 id="currentEpTitle" class="text-sm md:text-base font-semibold text-zinc-100 truncate">加载中...</h2>
              <span id="currentEpMeta" class="text-xs font-mono text-zinc-500 hidden xl:inline"></span>
              <button onclick="toggleCopilotDrawer(true)" id="studioLintBadgeBtn" class="px-2 py-0.5 rounded-md text-[11px] font-mono shrink-0 cursor-pointer transition"></button>
            </div>

            <div class="flex items-center gap-1.5 shrink-0">
              <div class="seg-group">
                <button onclick="setStudioSubView('storyboard')" id="subViewBtn-storyboard" class="seg-btn active !py-1 !px-2 text-[11px] md:text-xs">分镜</button>
                <button onclick="setStudioSubView('script')" id="subViewBtn-script" class="seg-btn !py-1 !px-2 text-[11px] md:text-xs">剧本</button>
              </div>

              <button onclick="compileSeedanceModal()" class="px-2.5 py-1.5 btn-ghost text-xs hidden sm:inline-flex" title="编译 Seedance 2.0 多模态节点清单">
                <span>🎯 Seedance 节点</span>
              </button>
              <button onclick="exportJianyingDraft()" class="px-2.5 py-1.5 btn-ghost text-xs hidden sm:inline-flex" title="一键导出非破坏性 5 轨剪映草稿与 SRT 字幕">
                <span>✂️ 剪映5轨草稿</span>
              </button>
              <button onclick="addBlankScene()" class="px-2.5 py-1.5 btn-ghost text-xs" title="新增镜头">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
                <span class="hidden sm:inline">新镜头</span>
              </button>
              <button onclick="saveCurrentEpisode()" id="btnSaveEpisode" class="px-3 py-1.5 btn-white text-xs">
                <span>保存</span>
              </button>
            </div>
          </div>

          <!-- 焦点镜头资产横向滑动注入条 -->
          <div class="flex items-center justify-between gap-2 overflow-x-auto no-scrollbar py-0.5">
            <div id="studioQuickAssetBar" class="flex items-center gap-1.5 shrink-0"></div>
            <button onclick="openAssetPickerForCurrentScene()" class="text-[11px] text-zinc-400 hover:text-white shrink-0 pl-2">
              选母图 →
            </button>
          </div>
        </div>

        <!-- 分镜卡片滚动区 / 文学剧本编辑区 -->
        <div class="flex-1 overflow-y-auto px-3 md:px-6 py-4 space-y-3.5 pb-20 lg:pb-6">
          <!-- 本集已合成母带快速审片条 -->
          <div id="epFinalVideosBar" class="hidden surface-card p-3">
            <div class="text-[10px] font-mono uppercase tracking-wider text-zinc-400 mb-2">MASTERED EPISODES · 本集已合成成片</div>
            <div id="epFinalVideosList" class="flex gap-2 overflow-x-auto no-scrollbar pb-0.5"></div>
          </div>

          <!-- 视图 A：可视化分镜卡片列表 -->
          <div id="studioStoryboardView" class="space-y-3.5 max-w-[1360px] mx-auto">
            <div id="sceneCardsContainer" class="space-y-3.5"></div>
          </div>

          <!-- 视图 B：沉浸式文学剧本编辑器 -->
          <div id="studioScriptView" class="hidden max-w-4xl mx-auto surface-card p-4 md:p-6 space-y-3.5">
            <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
              <div>
                <h3 class="text-sm font-semibold text-zinc-100">文学剧本正文 (`script.md`)</h3>
                <p class="text-xs text-zinc-500 mt-0.5">支持直接编辑，或点击右上角「AI 助手」通过 MCP 自动改稿。</p>
              </div>
              <button onclick="saveCurrentScript()" class="px-3.5 py-1.5 btn-white text-xs shrink-0">保存剧本</button>
            </div>
            <textarea id="scriptMarkdownEditor" rows="18" class="w-full p-3 md:p-4 field-input text-xs font-mono leading-relaxed"></textarea>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== VIEW 2: 项目资产中心 (Project Asset Center) ==================== -->
    <section id="tab-assets" class="hidden flex-1 overflow-y-auto p-3 md:p-6 pb-20 lg:pb-6">
      <div class="max-w-[1440px] mx-auto space-y-4 md:space-y-6">
        <div class="surface-card p-4 md:p-5 flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div class="flex items-center gap-2">
              <h2 class="text-base font-semibold text-zinc-100">项目全资产中心</h2>
              <span id="assetCenterProjBadge" class="text-[11px] font-mono px-2 py-0.5 rounded bg-white/[0.06] text-zinc-300 truncate max-w-[180px]"></span>
            </div>
            <p class="text-xs text-zinc-500 mt-1">
              管理当前项目的角色设定、首帧参考母图、三维空间拓扑与全局摄影风格锁。
            </p>
          </div>
          <div class="seg-group overflow-x-auto no-scrollbar w-full md:w-auto">
            <button onclick="switchAssetSubTab('chars')" id="assetSubBtn-chars" class="seg-btn active flex-1 md:flex-initial justify-center">角色与音色</button>
            <button onclick="switchAssetSubTab('props')" id="assetSubBtn-props" class="seg-btn flex-1 md:flex-initial justify-center">道具/武魂</button>
            <button onclick="switchAssetSubTab('voices')" id="assetSubBtn-voices" class="seg-btn flex-1 md:flex-initial justify-center">17款音色库</button>
            <button onclick="switchAssetSubTab('images')" id="assetSubBtn-images" class="seg-btn flex-1 md:flex-initial justify-center">首帧母图</button>
            <button onclick="switchAssetSubTab('rooms')" id="assetSubBtn-rooms" class="seg-btn flex-1 md:flex-initial justify-center">三维空间</button>
            <button onclick="switchAssetSubTab('style')" id="assetSubBtn-style" class="seg-btn flex-1 md:flex-initial justify-center">画风与声学</button>
          </div>
        </div>

        <!-- 子面板 A: 角色与造型库 -->
        <div id="assetSub-chars" class="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div class="lg:col-span-4 surface-card p-4 md:p-5 space-y-3.5 h-fit">
            <div>
              <h3 class="text-sm font-semibold text-zinc-100">角色资产与换装卡 (`profiles.toml`)</h3>
              <p class="text-xs text-zinc-500 mt-0.5">支持主角/配角/路人三级划分、16:9纯白底四视图卡、图生图换装版本与 48kHz 音色锚点绑定。</p>
            </div>
            <div class="space-y-3 text-xs">
              <div class="grid grid-cols-3 gap-2">
                <div class="col-span-2">
                  <label class="block text-zinc-400 mb-1">角色唯一 ID (建议2-3常用汉字)</label>
                  <input id="newCharName" placeholder="如: 沈照, 林薇, Alex" class="w-full px-3 py-2 field-input font-mono" />
                </div>
                <div>
                  <label class="block text-zinc-400 mb-1">角色层级</label>
                  <select id="newCharTier" class="w-full px-2 py-2 field-input">
                    <option value="protagonist">主角 (四视图+音色)</option>
                    <option value="supporting">配角 (跨片段固定)</option>
                    <option value="extra">路人 (免参考卡)</option>
                  </select>
                </div>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="block text-zinc-400 mb-1">绑定 48kHz 音色锚点</label>
                  <select id="newCharVoice" class="w-full px-2.5 py-2 field-input font-mono text-[11px]"></select>
                </div>
                <div>
                  <label class="block text-zinc-400 mb-1">服装版本标识 (换装卡)</label>
                  <input id="newCharCostume" value="v1_常规常服" placeholder="v1_base / v2_战甲" class="w-full px-2.5 py-2 field-input font-mono" />
                </div>
              </div>
              <div>
                <label class="block text-zinc-400 mb-1">核心外貌与干净常服结构 (不含场景血污雨水)</label>
                <textarea id="newCharApp" rows="3" placeholder="描述角色面部特征、年龄质感、发型、头身比、服装内外层结构与鞋履配饰..." class="w-full px-3 py-2 field-input"></textarea>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="block text-zinc-500 mb-1">现代/日常造型扩展</label>
                  <input id="newCharAppModern" placeholder="可选：日常造型" class="w-full px-2.5 py-1.5 field-input" />
                </div>
                <div>
                  <label class="block text-zinc-500 mb-1">古风/特殊时期扩展</label>
                  <input id="newCharAppAncient" placeholder="可选：古装/战甲造型" class="w-full px-2.5 py-1.5 field-input" />
                </div>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="block text-zinc-400 mb-1">9:16 立绘候选母图</label>
                  <select id="newCharRefSelect" class="w-full px-2 py-2 field-input font-mono text-[11px]"></select>
                </div>
                <div>
                  <label class="block text-zinc-400 mb-1">16:9 纯白底四视图卡</label>
                  <select id="newCharTurnaroundSelect" class="w-full px-2 py-2 field-input font-mono text-[11px]"></select>
                </div>
              </div>
              <div class="flex gap-2 pt-1">
                <button onclick="createNewCharacter()" class="flex-1 py-2.5 btn-white">保存角色资产</button>
                <button onclick="clearCharacterForm()" class="px-3.5 py-2.5 btn-ghost">清空</button>
              </div>
            </div>
          </div>

          <div class="lg:col-span-8 surface-card p-4 md:p-5">
            <div class="flex items-center justify-between mb-3.5">
              <h3 class="text-sm font-semibold text-zinc-100">已登记的角色资产</h3>
              <span class="text-xs text-zinc-500 hidden sm:inline">支持一键注入当前正在编辑的分镜</span>
            </div>
            <div id="characterCards" class="grid grid-cols-1 md:grid-cols-2 gap-3"></div>
          </div>
        </div>

        <!-- 子面板 A2: 武魂 / 召唤物 / 关键道具连续性资产 -->
        <div id="assetSub-props" class="hidden grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div class="lg:col-span-4 surface-card p-4 md:p-5 space-y-3.5 h-fit">
            <div>
              <h3 class="text-sm font-semibold text-zinc-100">武魂 / 召唤物 / 关键道具 (`[continuity_props]`)</h3>
              <p class="text-xs text-zinc-500 mt-0.5">凡跨镜头反复出现或承担关键动作的武器、信物、武魂、坐骑均建立独立参考，防止造型漂移。</p>
            </div>
            <div class="space-y-2.5 text-xs">
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="block text-zinc-400 mb-1">唯一英文 ID (`prop_id`)</label>
                  <input id="propIdInput" placeholder="如: bronze_sword, spirit_wolf" class="w-full px-3 py-2 field-input font-mono" />
                </div>
                <div>
                  <label class="block text-zinc-400 mb-1">中文名称</label>
                  <input id="propNameInput" placeholder="如: 镇岳古剑 / 苍狼武魂" class="w-full px-3 py-2 field-input" />
                </div>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="block text-zinc-400 mb-1">主体类别</label>
                  <select id="propCategoryInput" class="w-full px-2.5 py-2 field-input">
                    <option value="weapon">神兵 / 武器 (Weapon)</option>
                    <option value="summon">武魂 / 召唤兽 (Summon)</option>
                    <option value="artifact">核心信物 / 法器 (Artifact)</option>
                    <option value="prop">常规关键道具 (Prop)</option>
                  </select>
                </div>
                <div>
                  <label class="block text-zinc-400 mb-1">形态版本 (`version_tag`)</label>
                  <input id="propVersionInput" value="v1_常态" placeholder="v1_常态 / v2_觉醒巨大化" class="w-full px-2.5 py-2 field-input font-mono" />
                </div>
              </div>
              <div>
                <label class="block text-zinc-400 mb-1">干净展示态结构、材质、比例与发光部位描述</label>
                <textarea id="propDescInput" rows="3" placeholder="描述无遮挡展示状态下的轮廓、材质（乌铁/青铜/冷玉）、主辅色与稳定识别特征..." class="w-full px-3 py-2 field-input"></textarea>
              </div>
              <div>
                <label class="block text-zinc-400 mb-1">绑定独立参考图 (`ref_image`)</label>
                <select id="propRefImgSelect" class="w-full px-2.5 py-2 field-input font-mono text-[11px]"></select>
              </div>
              <button onclick="saveContinuityProp()" class="w-full py-2.5 btn-white">保存连续性道具/武魂</button>
            </div>
          </div>

          <div class="lg:col-span-8 surface-card p-4 md:p-5">
            <h3 class="text-sm font-semibold text-zinc-100 mb-3.5">已登记的连续性道具与武魂主体</h3>
            <div id="propCards" class="grid grid-cols-1 md:grid-cols-2 gap-3.5 text-xs"></div>
          </div>
        </div>

        <!-- 子面板 A3: 17款 48kHz 标准内置音色库 (试听与一键绑定) -->
        <div id="assetSub-voices" class="hidden surface-card p-4 md:p-5 space-y-4">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h3 class="text-sm font-semibold text-zinc-100">内置 48kHz / 16-bit PCM 标准角色音色锚点库 (`assets/voices/`)</h3>
              <p class="text-xs text-zinc-500 mt-0.5">吸收自 director Cinematic Drama 实测验证的 17 款中英文纯净人声锚点，可直接试听并用于 Seedance 2.0 音色参考或本地 IndexTTS-2 零样本克隆。</p>
            </div>
          </div>
          <div id="voiceLibraryGrid" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3.5 text-xs"></div>
        </div>

        <!-- 子面板 B: 首帧参考母图画廊 -->
        <div id="assetSub-images" class="hidden grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div class="lg:col-span-4 surface-card p-4 md:p-5 space-y-4 h-fit">
            <div>
              <h3 class="text-sm font-semibold text-zinc-100">上传首帧参考母图</h3>
              <p class="text-xs text-zinc-500 mt-0.5">支持直接从手机相册或电脑选择图片上传，上传后可立即绑定给角色或分镜。</p>
            </div>
            <label for="uploadImgFile" class="flex flex-col items-center justify-center border border-dashed border-zinc-700 hover:border-zinc-500 rounded-xl p-5 cursor-pointer bg-zinc-950/50 transition text-center space-y-2">
              <svg class="w-7 h-7 text-zinc-400" fill="none" stroke="currentColor" stroke-width="1.6" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/></svg>
              <div class="text-xs font-medium text-zinc-200">点击选择相册或本地图片</div>
              <div id="uploadFileNameLabel" class="text-[11px] font-mono text-zinc-500">JPG / PNG / WebP</div>
              <input id="uploadImgFile" type="file" accept="image/*" onchange="document.getElementById('uploadFileNameLabel').textContent = this.files[0]?.name || '未选择文件'" class="hidden" />
            </label>
            <button onclick="uploadAnchorImage()" class="w-full py-2.5 btn-white text-xs">
              上传至当前项目母图库
            </button>
          </div>

          <div class="lg:col-span-8 surface-card p-4 md:p-5">
            <div class="flex items-center justify-between mb-3.5">
              <h3 class="text-sm font-semibold text-zinc-100">项目参考母图画廊 (`characters/images/`)</h3>
              <span class="text-xs text-zinc-500">点击图片可全屏检视</span>
            </div>
            <div id="imageGallery" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3.5"></div>
          </div>
        </div>

        <!-- 子面板 C: 三维空间拓扑 -->
        <div id="assetSub-rooms" class="hidden grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div class="lg:col-span-4 surface-card p-4 md:p-5 space-y-3.5 h-fit">
            <div>
              <h3 class="text-sm font-semibold text-zinc-100">三维空间拓扑坐标 (`[spatial_rooms]`)</h3>
              <p class="text-xs text-zinc-500 mt-0.5">固定同一场景左、中、右三维陈设坐标与内外景锚点，杜绝跨镜头空间穿帮。</p>
            </div>
            <div class="space-y-2.5 text-xs">
              <div>
                <label class="block text-zinc-400 mb-1">空间唯一 ID (`room_id`)</label>
                <input id="roomIdInput" placeholder="例如: studio_loft, command_tent" class="w-full px-3 py-2 field-input font-mono" />
              </div>
              <div>
                <label class="block text-zinc-400 mb-1">空间名称与用途说明</label>
                <input id="roomDescInput" placeholder="例如: 主角公寓客厅（落地窗夜景）" class="w-full px-3 py-2 field-input" />
              </div>
              <div>
                <label class="block text-zinc-500 mb-1">左侧固定陈设 (`camera_left`)</label>
                <input id="roomLeftInput" placeholder="rainy window on camera-left" class="w-full px-3 py-1.5 field-input" />
              </div>
              <div>
                <label class="block text-zinc-500 mb-1">中景核心区 (`center_foreground`)</label>
                <input id="roomCenterInput" placeholder="oak desk in center foreground" class="w-full px-3 py-1.5 field-input" />
              </div>
              <div>
                <label class="block text-zinc-500 mb-1">右侧固定陈设 (`camera_right`)</label>
                <input id="roomRightInput" placeholder="dark bookshelf on camera-right" class="w-full px-3 py-1.5 field-input" />
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="block text-zinc-500 mb-1">外景建置母图</label>
                  <select id="roomExtImgSelect" class="w-full px-2 py-1.5 field-input font-mono text-[11px]"></select>
                </div>
                <div>
                  <label class="block text-zinc-500 mb-1">内景主母图</label>
                  <select id="roomIntImgSelect" class="w-full px-2 py-1.5 field-input font-mono text-[11px]"></select>
                </div>
              </div>
              <button onclick="saveSpatialRoom()" class="w-full py-2.5 mt-1 btn-white">保存空间拓扑资产</button>
            </div>
          </div>

          <div class="lg:col-span-8 surface-card p-4 md:p-5">
            <h3 class="text-sm font-semibold text-zinc-100 mb-3.5">已配置的三维空间拓扑</h3>
            <div id="roomCards" class="grid grid-cols-1 md:grid-cols-2 gap-3.5 text-xs"></div>
          </div>
        </div>

        <!-- 子面板 D: 摄影风格锁与声学空间 -->
        <div id="assetSub-style" class="hidden grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div class="lg:col-span-6 surface-card p-4 md:p-5 space-y-3.5">
            <div>
              <h3 class="text-sm font-semibold text-zinc-100">Cinematic Drama 预设画风与胶片风格锁 (`[style_lock]`)</h3>
              <p class="text-xs text-zinc-500 mt-0.5">支持一键应用样片验证画风（真人电影 ARRI / 半写实 3D 国漫 / 东方奇幻暗黑 3D / 2D 故事解说），自动锁死全片视觉语言。</p>
            </div>
            <div id="stylePresetsRow" class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs"></div>
            <div class="space-y-2.5 text-xs">
              <div>
                <label class="block text-zinc-400 mb-1">摄影机与镜头基底 (`camera_base`)</label>
                <input id="styleCameraBase" class="w-full px-3 py-2 field-input" />
              </div>
              <div>
                <label class="block text-zinc-400 mb-1">全局布光基调 (`lighting_base`)</label>
                <input id="styleLightingBase" class="w-full px-3 py-2 field-input" />
              </div>
              <div>
                <label class="block text-zinc-400 mb-1">胶片颗粒质感 (`film_stock`)</label>
                <input id="styleFilmStock" class="w-full px-3 py-2 field-input" />
              </div>
              <div>
                <label class="block text-zinc-400 mb-1">通用画面后缀 (`global_suffix`)</label>
                <input id="styleGlobalSuffix" class="w-full px-3 py-2 field-input" />
              </div>
              <div>
                <label class="block text-zinc-400 mb-1">现代/特定场景后缀 (`modern_suffix`)</label>
                <input id="styleModernSuffix" class="w-full px-3 py-2 field-input" />
              </div>
              <div>
                <label class="block text-zinc-400 mb-1">负面排除词 (`negative_prompt`)</label>
                <textarea id="styleNegativePrompt" rows="2" class="w-full px-3 py-2 field-input"></textarea>
              </div>
              <button onclick="saveStyleLock()" class="w-full py-2.5 btn-white">保存全局摄影风格锁</button>
            </div>
          </div>

          <div class="lg:col-span-6 surface-card p-4 md:p-5 space-y-4">
            <h3 class="text-sm font-semibold text-zinc-100">声学环境与滤波配置 (`[acoustic_spaces]`)</h3>
            <div class="space-y-2.5 text-xs p-3.5 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
              <div class="font-medium text-zinc-300">新增 / 更新声学环境</div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <input id="acSpaceId" placeholder="声学ID (如: indoor_room)" class="px-2.5 py-2 field-input font-mono" />
                <input id="acDesc" placeholder="环境说明" class="px-2.5 py-2 field-input" />
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <input id="acFilter" placeholder="FFmpeg 滤镜 (如: lowpass=f=800,volume=0.2)" class="px-2.5 py-2 field-input font-mono" />
                <input id="acCue" placeholder="环境音提示词 (Audio Cue)" class="px-2.5 py-2 field-input" />
              </div>
              <button onclick="saveAcousticSpace()" class="w-full py-2 btn-ghost font-medium">保存声学空间</button>
            </div>
            <div id="acousticCards" class="space-y-2 max-h-80 overflow-y-auto text-xs"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== VIEW 3: 成片与素材库 (Screening Room) ==================== -->
    <section id="tab-theater" class="hidden flex-1 overflow-y-auto p-3 md:p-6 pb-20 lg:pb-6">
      <div class="max-w-[1440px] mx-auto space-y-5">
        <div class="surface-card p-4 md:p-5">
          <div class="mb-3.5">
            <h2 class="text-base font-semibold text-zinc-100">整集母带审片室 (`output/final_episodes/`)</h2>
            <p class="text-xs text-zinc-500 mt-0.5">当前项目已合成的全部整集视频成片，支持手机全屏播放</p>
          </div>
          <div id="theaterGrid" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"></div>
        </div>

        <div class="surface-card p-4 md:p-5">
          <div class="mb-3.5">
            <h2 class="text-sm font-semibold text-zinc-200">单镜原始生成素材 (`output/raw_clips/`)</h2>
            <p class="text-xs text-zinc-500 mt-0.5">按剧集归档的所有单镜头生成片段</p>
          </div>
          <div id="rawClipsGrid" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3.5"></div>
        </div>
      </div>
    </section>

    <!-- ==================== VIEW 4: 任务与配额 (Render Queue & Guard) ==================== -->
    <section id="tab-queue" class="hidden flex-1 overflow-y-auto p-3 md:p-6 pb-20 lg:pb-6">
      <div class="max-w-[1440px] mx-auto space-y-6">

        <!-- 3-in-1 Quota & Capacity Matrix Dashboard Section -->
        <div class="surface-card p-4 md:p-6 space-y-4">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/[0.06] pb-3.5">
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>
              </div>
              <div>
                <h2 class="text-base font-semibold text-zinc-100 flex items-center gap-2">
                  <span>三合一算力与配额监控中心</span>
                  <span class="text-xs px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-mono">LIVE CLUSTER</span>
                </h2>
                <p class="text-xs text-zinc-400 mt-0.5">Google Colab Cloud GPU · Google Flow (Veo/Nano-Pro) · Google Flow Music (Lyria/ACE-Step)</p>
              </div>
            </div>
            <div class="flex items-center gap-2 text-xs font-mono text-zinc-400">
              <span id="queueQuotaUpdated">更新时间: 实时同步中...</span>
              <button onclick="refreshQuotaSummary()" class="px-2.5 py-1 btn-ghost text-xs flex items-center gap-1">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                <span>刷新</span>
              </button>
            </div>
          </div>

          <!-- 3-Column Card Matrix Grid -->
          <div id="queueQuotaCards" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <!-- Cards populated dynamically by renderQuotaDashboard -->
          </div>

          <!-- Multi-Lane High-Concurrency Dispatcher Status & Tuning Panel -->
          <div class="p-4 rounded-xl bg-zinc-900/90 border border-white/[0.08] space-y-3.5 shadow-md">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/[0.06] pb-2.5">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                <span class="text-xs font-semibold text-zinc-200">全通道高并发信号量调度池 (Multi-Lane Concurrency Pool)</span>
                <span class="text-[10px] text-zinc-500 font-mono hidden md:inline">拒绝串行排队 · 满载压榨云端与显卡算力</span>
              </div>
              <button onclick="saveConcurrencyConfig()" class="px-2.5 py-1 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] font-medium transition flex items-center gap-1 shadow-sm">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M5 13l4 4L19 7"/></svg>
                <span>保存并发配置</span>
              </button>
            </div>

            <!-- Live Lane Badges Strip -->
            <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5 font-mono text-xs">
              <div class="p-2.5 rounded-lg bg-zinc-950/70 border border-amber-500/20 space-y-1">
                <div class="text-[10px] text-amber-400 font-medium">Flow 视频并发槽</div>
                <div class="flex items-baseline justify-between">
                  <span id="laneBadgeFlow" class="text-sm font-bold text-amber-300">0 / 8 槽</span>
                  <span class="text-[10px] text-zinc-500">云端批处理</span>
                </div>
              </div>
              <div class="p-2.5 rounded-lg bg-zinc-950/70 border border-sky-500/20 space-y-1">
                <div class="text-[10px] text-sky-400 font-medium">Colab G4 并发流</div>
                <div class="flex items-baseline justify-between">
                  <span id="laneBadgeColab" class="text-sm font-bold text-sky-300">0 / 4 槽</span>
                  <span class="text-[10px] text-zinc-500">单卡多流+多实例</span>
                </div>
              </div>
              <div class="p-2.5 rounded-lg bg-zinc-950/70 border border-indigo-500/20 space-y-1">
                <div class="text-[10px] text-indigo-400 font-medium">Sume API 并发槽</div>
                <div class="flex items-baseline justify-between">
                  <span id="laneBadgeSume" class="text-sm font-bold text-indigo-300">0 / 8 槽</span>
                  <span class="text-[10px] text-zinc-500">多模态路由</span>
                </div>
              </div>
              <div class="p-2.5 rounded-lg bg-zinc-950/70 border border-purple-500/20 space-y-1">
                <div class="text-[10px] text-purple-400 font-medium">TTS/Music 并发槽</div>
                <div class="flex items-baseline justify-between">
                  <span id="laneBadgeAudio" class="text-sm font-bold text-purple-300">0 / 6 槽</span>
                  <span class="text-[10px] text-zinc-500">语音与配乐</span>
                </div>
              </div>
              <div class="p-2.5 rounded-lg bg-zinc-950/70 border border-emerald-500/20 space-y-1 col-span-2 sm:col-span-1">
                <div class="text-[10px] text-emerald-400 font-medium">Local ROCm 预取槽</div>
                <div class="flex items-baseline justify-between">
                  <span id="laneBadgeRocm" class="text-sm font-bold text-emerald-300">0 / 2 槽</span>
                  <span class="text-[10px] text-zinc-500">双流重叠预取</span>
                </div>
              </div>
            </div>

            <!-- Tuning Form Inputs -->
            <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5 text-xs font-mono pt-1">
              <div class="space-y-1">
                <label class="text-[10px] text-zinc-400">Flow 并发上限</label>
                <input id="cfgFlowConcurrency" type="number" min="1" max="32" value="8" class="w-full px-2.5 py-1.5 field-input text-xs" />
              </div>
              <div class="space-y-1">
                <label class="text-[10px] text-zinc-400">Colab G4 并发流</label>
                <input id="cfgColabConcurrency" type="number" min="1" max="16" value="4" class="w-full px-2.5 py-1.5 field-input text-xs" />
              </div>
              <div class="space-y-1">
                <label class="text-[10px] text-zinc-400">Sume API 并发上限</label>
                <input id="cfgSumeConcurrency" type="number" min="1" max="32" value="8" class="w-full px-2.5 py-1.5 field-input text-xs" />
              </div>
              <div class="space-y-1">
                <label class="text-[10px] text-zinc-400">TTS/配乐并发上限</label>
                <input id="cfgAudioConcurrency" type="number" min="1" max="16" value="6" class="w-full px-2.5 py-1.5 field-input text-xs" />
              </div>
              <div class="space-y-1 col-span-2 sm:col-span-1">
                <label class="text-[10px] text-zinc-400">Local ROCm 预取流</label>
                <input id="cfgRocmConcurrency" type="number" min="1" max="8" value="2" class="w-full px-2.5 py-1.5 field-input text-xs" />
              </div>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div class="lg:col-span-4 surface-card p-4 md:p-5 space-y-4 h-fit">
          <!-- 移动端可见的硬件与云端算力概览卡 -->
          <div class="p-3 rounded-xl bg-zinc-900/80 border border-white/[0.06] space-y-1.5 text-xs font-mono">
            <div class="flex items-center justify-between">
              <span class="text-zinc-400">本机引擎:</span>
              <span id="mobileGpuBadge" class="text-emerald-400">Strix Halo 96G (0积分)</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-zinc-400">云端积分余额:</span>
              <span id="mobileCreditBalance" class="text-zinc-100 font-semibold">--</span>
            </div>
          </div>

          <div>
            <h3 class="text-sm font-semibold text-zinc-100">云端积分防火墙与审批策略</h3>
            <p class="text-xs text-zinc-500 mt-1 leading-relaxed">
              开启旗舰档审批锁后，本机 Strix Halo (H3) 与云端 Fast 档可自由使用；提交 100点/镜 的 Veo 3.1 Quality 母带任务时需管理员批准。
            </p>
          </div>
          <label class="flex items-center gap-2.5 text-xs text-zinc-200 cursor-pointer pt-1">
            <input id="chkQualityApproval" type="checkbox" checked class="w-4 h-4 accent-zinc-200 rounded" />
            <span>启用旗舰档 (Veo Quality 100点/镜) 审批锁</span>
          </label>
          <div class="space-y-1 text-xs">
            <label class="text-zinc-400">每日免审额度上限 (点)</label>
            <input id="inpDailyLimit" type="number" value="300" class="w-full px-3 py-2 field-input font-mono" />
          </div>
          <div class="space-y-1 text-xs">
            <label class="text-zinc-400">管理员审批口令</label>
            <input id="inpAdminPin" type="password" value="2280" class="w-full px-3 py-2 field-input font-mono" />
          </div>
          <button onclick="savePolicy()" class="w-full py-2.5 btn-white text-xs">保存配额策略</button>
        </div>

        <div class="lg:col-span-8 surface-card p-4 md:p-5">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-semibold text-zinc-100">渲染任务队列与执行日志</h3>
            <button onclick="loadJobs()" class="px-2.5 py-1 btn-ghost text-xs">刷新队列</button>
          </div>
          <div id="jobsList" class="space-y-2.5"></div>
        </div>
      </div>
    </section>

  </div>

  <!-- ==================== 移动端专属：底部固定导航栏 (Bottom App Bar, 仅 <lg 显示) ==================== -->
  <nav class="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-[#0c0c0f]/95 backdrop-blur-lg border-t border-white/[0.08] grid grid-cols-4 pb-safe">
    <button onclick="switchTab('studio')" id="mTabBtn-studio" class="py-2 flex flex-col items-center justify-center gap-1 text-zinc-100">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.9" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M3 10h6M3 15h6"/></svg>
      <span class="text-[10px] font-medium">分镜台</span>
    </button>
    <button onclick="switchTab('assets')" id="mTabBtn-assets" class="py-2 flex flex-col items-center justify-center gap-1 text-zinc-500">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.9" viewBox="0 0 24 24"><path d="M20 7h-9m9 10h-9M4 7h.01M4 17h.01"/><rect x="3" y="4" width="18" height="6" rx="1"/><rect x="3" y="14" width="18" height="6" rx="1"/></svg>
      <span class="text-[10px] font-medium">资产库</span>
    </button>
    <button onclick="switchTab('theater')" id="mTabBtn-theater" class="py-2 flex flex-col items-center justify-center gap-1 text-zinc-500">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.9" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
      <span class="text-[10px] font-medium">审片室</span>
    </button>
    <button onclick="switchTab('queue')" id="mTabBtn-queue" class="py-2 flex flex-col items-center justify-center gap-1 text-zinc-500 relative">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.9" viewBox="0 0 24 24"><path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4"/></svg>
      <span class="text-[10px] font-medium">任务/配额</span>
    </button>
  </nav>

  <!-- ==================== 移动端专属：底部上拉式整集渲染面板 (Mobile Render Bottom Sheet) ==================== -->
  <div id="mobileRenderSheet" class="drawer-backdrop fixed inset-0 bg-black/60 backdrop-blur-[2px] z-50 flex items-end lg:hidden" onclick="if(event.target===this) toggleMobileRenderSheet(false)">
    <div class="drawer-panel-bottom w-full bg-[#131318] border-t border-white/[0.1] rounded-t-2xl p-5 pb-safe space-y-4 shadow-2xl">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-sm font-semibold text-zinc-100">整集一键渲染输出</h3>
          <p class="text-xs text-zinc-500 mt-0.5">选择渲染引擎生成当前剧集视频</p>
        </div>
        <button onclick="toggleMobileRenderSheet(false)" class="p-1.5 rounded-lg text-zinc-400">✕</button>
      </div>
      <div class="space-y-2">
        <button onclick="toggleMobileRenderSheet(false); submitEpisodeRender('minimax-h3', false)" class="w-full py-3 px-4 btn-ghost text-xs flex items-center justify-between">
          <span class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>本机 Strix Halo (H3) 免费预演整集</span>
          </span>
          <span class="font-mono text-emerald-400">0 积分</span>
        </button>
        <button onclick="toggleMobileRenderSheet(false); submitEpisodeRender('veo-fast', false)" class="w-full py-3 px-4 btn-ghost text-xs flex items-center justify-between">
          <span>云端 Google Veo Fast 快速成片</span>
          <span class="font-mono text-zinc-400">10点 / 镜</span>
        </button>
        <button onclick="toggleMobileRenderSheet(false); submitEpisodeRender('veo-quality', false)" class="w-full py-3 px-4 btn-white text-xs flex items-center justify-between">
          <span>云端 Veo 3.1 Quality 旗舰母带</span>
          <span class="font-mono opacity-75">100点 / 镜</span>
        </button>
        <button onclick="toggleMobileRenderSheet(false); submitEpisodeRender('heygen-video-1', false)" class="w-full py-3 px-4 btn-ghost text-xs flex items-center justify-between">
          <span>Sume · HeyGen Video 1 (原生嘴型)</span>
          <span class="font-mono text-emerald-400">100张礼券 / $0.01/s</span>
        </button>
        <button onclick="toggleMobileRenderSheet(false); submitEpisodeRender('seedance-2.5', false)" class="w-full py-3 px-4 btn-ghost text-xs flex items-center justify-between">
          <span>Sume · Seedance 2.5 旗舰多模态</span>
          <span class="font-mono text-zinc-400">$0.10/s</span>
        </button>
      </div>
    </div>
  </div>

  <!-- ==================== 侧滑抽屉：AI 导演助手 (MCP) & L1-L5 门禁诊断 ==================== -->
  <div id="copilotDrawer" class="drawer-backdrop fixed inset-0 bg-black/60 backdrop-blur-[2px] z-50 flex justify-end" onclick="if(event.target===this) toggleCopilotDrawer(false)">
    <div class="drawer-panel-right w-full max-w-md bg-[#111115] border-l border-white/[0.08] h-full flex flex-col justify-between p-4 md:p-5 shadow-2xl">
      <div class="space-y-4 overflow-y-auto pr-1">
        <div class="flex items-center justify-between border-b border-white/[0.07] pb-3">
          <div>
            <h3 class="text-sm font-semibold text-zinc-100">AI 导演助手 & 工业门禁诊断</h3>
            <p class="text-[11px] text-zinc-500 mt-0.5">Antigravity MCP 双向直连 · L1-L5 实时规范检查</p>
          </div>
          <button onclick="toggleCopilotDrawer(false)" class="p-1.5 rounded-lg hover:bg-white/[0.06] text-zinc-400 hover:text-white">✕</button>
        </div>

        <div class="surface-card p-4 space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-zinc-200">呼叫 Antigravity 代理改稿</span>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">MCP ONLINE</span>
          </div>
          <p class="text-xs text-zinc-500 leading-relaxed">
            输入自然语言改稿或分镜调整需求，Antigravity 助手收到后会直接通过 MCP 修改当前剧集的 `script.md` 与 `movie.toml`。
          </p>
          <textarea id="agentDemandInput" rows="3" placeholder="例如：把第2幕台词改得更克制内敛，或者给本集增加一幕特写镜头..." class="w-full p-2.5 field-input text-xs"></textarea>
          <button onclick="sendDemandToAgent(null)" id="btnSendAgentDemand" class="w-full py-2.5 btn-white text-xs">
            发送改稿指令给 Antigravity
          </button>
          <div id="agentDemandsHistory" class="space-y-1.5 max-h-44 overflow-y-auto pt-1 text-[11px]"></div>
        </div>

        <div class="surface-card p-4 space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-zinc-200">L1-L5 导演门禁质检报告</span>
            <span id="lintStatusPill" class="text-[11px] font-mono px-2 py-0.5 rounded">--</span>
          </div>
          <div id="lintIssuesBox" class="space-y-2 text-xs"></div>
        </div>
      </div>

      <div id="liveEventBanner" class="pt-3 border-t border-white/[0.06] text-[11px] font-mono text-zinc-500 truncate">
        READY · 实时事件通道已连接
      </div>
    </div>
  </div>

  <!-- ==================== 弹窗 1：可视化母图快选器 ==================== -->
  <div id="assetPickerModal" class="fixed inset-0 bg-black/80 z-50 hidden items-end sm:items-center justify-center p-0 sm:p-4 backdrop-blur-sm" onclick="if(event.target===this) closeAssetPickerModal()">
    <div class="surface-card w-full max-w-3xl rounded-t-2xl sm:rounded-xl p-4 md:p-5 space-y-4 shadow-2xl max-h-[85vh] flex flex-col">
      <div class="flex items-center justify-between border-b border-white/[0.07] pb-3">
        <div>
          <h3 class="text-sm font-semibold text-zinc-100">选择首帧参考母图</h3>
          <p id="assetPickerTargetLabel" class="text-xs text-zinc-500 mt-0.5">点击任意母图即可立即绑定到当前分镜镜头</p>
        </div>
        <button onclick="closeAssetPickerModal()" class="px-2.5 py-1 btn-ghost text-xs">关闭 ✕</button>
      </div>
      <div id="assetPickerGrid" class="grid grid-cols-2 sm:grid-cols-3 gap-3 overflow-y-auto p-1"></div>
    </div>
  </div>

  <!-- ==================== 弹窗 2：新建项目 ==================== -->
  <div id="newProjectModal" class="fixed inset-0 bg-black/80 z-50 hidden items-end sm:items-center justify-center p-0 sm:p-4 backdrop-blur-sm">
    <div class="surface-card max-w-lg w-full rounded-t-2xl sm:rounded-xl p-5 md:p-6 space-y-4 shadow-2xl pb-safe">
      <div class="flex items-center justify-between">
        <h3 class="text-base font-semibold text-zinc-100">新建短视频创作项目</h3>
        <button onclick="closeNewProjectModal()" class="text-zinc-500 hover:text-zinc-200 p-1">✕</button>
      </div>
      <p class="text-xs text-zinc-400 leading-relaxed">
        每个项目在 <code class="text-zinc-200 font-mono">projects/&lt;id&gt;/</code> 下拥有独立隔离的角色库、首帧母图、空间拓扑与剧集目录。
      </p>
      <div class="space-y-3 text-xs">
        <div>
          <label class="block text-zinc-400 mb-1">项目英文标识 ID (文件夹名)</label>
          <input id="modalProjId" placeholder="例如: neon_city, brand_film, short_drama" class="w-full px-3 py-2.5 field-input font-mono" />
        </div>
        <div>
          <label class="block text-zinc-400 mb-1">项目中文名称</label>
          <input id="modalProjName" placeholder="例如：深秋叙事短片 / 赛博悬疑短剧" class="w-full px-3 py-2.5 field-input text-sm" />
        </div>
        <div class="grid grid-cols-2 gap-2.5">
          <div>
            <label class="block text-zinc-400 mb-1">题材与视觉基调</label>
            <input id="modalProjSub" value="电影感写实短片" class="w-full px-3 py-2 field-input" />
          </div>
          <div>
            <label class="block text-zinc-400 mb-1">默认画幅比例</label>
            <select id="modalProjAspect" class="w-full px-3 py-2 field-input">
              <option value="16:9">16:9 横屏宽银幕</option>
              <option value="9:16">9:16 竖屏短视频</option>
            </select>
          </div>
        </div>
      </div>
      <div class="flex justify-end gap-2 pt-2">
        <button onclick="closeNewProjectModal()" class="px-4 py-2.5 btn-ghost text-xs">取消</button>
        <button onclick="createNewProject()" class="px-5 py-2.5 btn-white text-xs">创建项目</button>
      </div>
    </div>
  </div>

  <!-- ==================== 弹窗 3：新建剧集分镜 ==================== -->
  <div id="newEpModal" class="fixed inset-0 bg-black/80 z-50 hidden items-end sm:items-center justify-center p-0 sm:p-4 backdrop-blur-sm">
    <div class="surface-card max-w-xl w-full rounded-t-2xl sm:rounded-xl p-5 md:p-6 space-y-4 shadow-2xl pb-safe">
      <div class="flex items-center justify-between">
        <h3 class="text-base font-semibold text-zinc-100">新建剧集与自动分镜编译</h3>
        <button onclick="closeNewEpisodeModal()" class="text-zinc-500 hover:text-zinc-200 p-1">✕</button>
      </div>
      <p class="text-xs text-zinc-400 leading-relaxed">
        输入本集剧情梗概（以句号分隔每一幕），系统将自动结合当前项目的角色、空间与镜头风格生成分镜表。
      </p>
      <div class="space-y-3 text-xs">
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
          <div class="sm:col-span-2">
            <label class="block text-zinc-400 mb-1">剧集标题</label>
            <input id="modalEpTitle" placeholder="例如：第1集：序幕" class="w-full px-3 py-2 field-input text-sm" />
          </div>
          <div>
            <label class="block text-zinc-400 mb-1">目录英文标识</label>
            <input id="modalEpDir" placeholder="ep01_prologue" class="w-full px-3 py-2 field-input font-mono" />
          </div>
        </div>
        <div>
          <label class="block text-zinc-400 mb-1">分幕剧情梗概（用句号分隔每一幕镜头）</label>
          <textarea id="modalStoryIdea" rows="4" placeholder="输入每一幕的画面与动作描述，用句号隔开..." class="w-full px-3 py-2 field-input text-sm"></textarea>
        </div>
      </div>
      <div class="flex justify-end gap-2 pt-2">
        <button onclick="closeNewEpisodeModal()" class="px-4 py-2.5 btn-ghost text-xs">取消</button>
        <button onclick="createEpisodeWithAi()" id="btnCreateEpAi" class="px-5 py-2.5 btn-white text-xs">生成分镜工程</button>
      </div>
    </div>
  </div>

  <!-- ==================== 弹窗 4：媒体检视器 ==================== -->
  <div id="videoModal" class="fixed inset-0 bg-black/90 z-50 hidden items-center justify-center p-3 md:p-4" onclick="if(event.target===this) closeVideoModal()">
    <div class="surface-card max-w-4xl w-full p-3.5 md:p-4 space-y-3">
      <div class="flex items-center justify-between">
        <h3 id="videoModalTitle" class="text-xs font-mono text-zinc-200 truncate">MEDIA PREVIEW</h3>
        <button onclick="closeVideoModal()" class="px-2.5 py-1 btn-ghost text-xs">关闭 ✕</button>
      </div>
      <video id="videoModalPlayer" controls playsinline class="w-full rounded-lg bg-black max-h-[75vh]"></video>
      <img id="imageModalViewer" class="hidden w-full rounded-lg bg-black max-h-[75vh] object-contain" />
    </div>
  </div>

  <!-- ==================== 弹窗：三合一算力与配额监控中心 ==================== -->
  <div id="quotaDetailModal" class="fixed inset-0 bg-black/85 z-50 hidden items-center justify-center p-3 md:p-6 backdrop-blur-md" onclick="if(event.target===this) closeQuotaModal()">
    <div class="surface-card max-w-5xl w-full max-h-[92vh] flex flex-col overflow-hidden shadow-2xl border border-white/[0.1] bg-[#0c0c10]">
      <!-- 模态框标题栏 -->
      <div class="p-4 md:p-5 border-b border-white/[0.08] flex items-center justify-between shrink-0 bg-zinc-950/60">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/40 flex items-center justify-center text-indigo-300">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>
          </div>
          <div>
            <h2 class="text-base font-semibold text-zinc-100 flex items-center gap-2">
              <span>三合一算力与配额监控中心</span>
              <span class="text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-mono">Google AI Ultra</span>
            </h2>
            <p class="text-xs text-zinc-400 mt-0.5">Colab Cloud GPU · Google Flow (Veo/Nano-Pro) · Google Flow Music (Lyria/ACE-Step)</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button onclick="refreshQuotaSummary()" class="px-2.5 py-1.5 btn-ghost text-xs flex items-center gap-1">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
            <span class="hidden sm:inline">刷新配额</span>
          </button>
          <button onclick="closeQuotaModal()" class="px-2.5 py-1.5 btn-ghost text-xs text-zinc-400 hover:text-white">✕ 关闭</button>
        </div>
      </div>

      <!-- 模态框主体内容 (滚动区域) -->
      <div class="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        <!-- 3-Column Card Matrix Grid -->
        <div id="modalQuotaCards" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4.5">
          <!-- Populated by JavaScript renderQuotaCards -->
        </div>

        <!-- Google Flow Music 快速试听与合成器 -->
        <div class="p-4 md:p-5 rounded-2xl bg-gradient-to-br from-purple-950/20 via-zinc-900/60 to-zinc-950/80 border border-purple-500/20 space-y-4">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div class="flex items-center gap-2.5">
              <span class="text-lg">🎵</span>
              <div>
                <h3 class="text-sm font-semibold text-purple-200">Google Flow Music / ACE-Step 1.5 极速配乐与拟音合成器</h3>
                <p class="text-xs text-zinc-400 mt-0.5">支持古风管弦、高燃交响、诙谐爵士、赛博朋克合成器等多种曲风，全自动时间对齐与广播级母带混音</p>
              </div>
            </div>
            <span class="text-xs font-mono text-purple-300 bg-purple-500/10 px-2.5 py-1 rounded-full border border-purple-500/20">500首/日 · 0 Credits 扣减</span>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
            <div class="sm:col-span-6 space-y-1">
              <label class="text-[11px] font-mono text-zinc-400">配乐提示词 (Prompt)</label>
              <input id="musicPromptInput" type="text" value="三国英雄史诗出山，古风笛箫与宏大交响战役配乐" class="w-full px-3 py-2 field-input text-xs" />
            </div>
            <div class="sm:col-span-3 space-y-1">
              <label class="text-[11px] font-mono text-zinc-400">情绪曲风 (Mood)</label>
              <select id="musicMoodSelect" class="w-full px-3 py-2 field-input text-xs">
                <option value="guofeng" selected>古风国风 (Guofeng Pentatonic)</option>
                <option value="epic">史诗宏大 (Epic Orchestral)</option>
                <option value="comic">幽默轻快 (Comic Quirky)</option>
                <option value="jazz">沉静爵士 (Jazzy Noir)</option>
                <option value="cyberpunk">赛博合成器 (Cyberpunk Synth)</option>
              </select>
            </div>
            <div class="sm:col-span-3 space-y-1">
              <label class="text-[11px] font-mono text-zinc-400">时长: <span id="musicDurationLabel" class="text-purple-300">15.0</span> 秒</label>
              <input id="musicDurationInput" type="range" min="5" max="60" value="15" step="1" oninput="document.getElementById('musicDurationLabel').textContent = this.value + '.0'" class="w-full accent-purple-400" />
            </div>
          </div>

          <div class="flex items-center justify-between pt-1">
            <div id="musicGenStatus" class="text-xs text-zinc-400 font-mono truncate max-w-md">就绪，点击开始生成并试听</div>
            <button onclick="testGenerateMusic()" id="btnGenerateMusic" class="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium flex items-center gap-1.5 transition shadow-lg shadow-purple-600/20">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              <span>立即生成配乐</span>
            </button>
          </div>

          <div id="musicAudioPlayerBox" class="hidden pt-2 border-t border-white/[0.06]">
            <audio id="musicAudioPlayer" controls class="w-full h-9 rounded-lg"></audio>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ==================== 弹窗 5：极简登录验证 ==================== -->
  <div id="loginModal" class="fixed inset-0 bg-[#09090b] z-[100] hidden items-center justify-center p-4">
    <div class="surface-card max-w-sm w-full p-6 md:p-7 space-y-5 shadow-2xl">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-lg bg-zinc-100 text-zinc-950 flex items-center justify-center font-mono font-bold text-sm">
          AD
        </div>
        <div>
          <h2 class="text-base font-semibold text-zinc-100">AetherDirector Studio</h2>
          <p class="text-xs text-zinc-500">天枢 · AI 影视工业工作台 · 访问验证</p>
        </div>
      </div>
      <div class="space-y-3">
        <input id="loginPasswordInput" type="password" placeholder="输入工作台访问密码..." onkeydown="if(event.key==='Enter') submitLogin()" class="w-full px-3.5 py-2.5 field-input text-sm" />
        <p id="loginErrorMsg" class="hidden text-xs text-red-400"></p>
        <button onclick="submitLogin()" class="w-full py-2.5 btn-white text-xs">
          解锁进入工作台
        </button>
      </div>
    </div>
  </div>

  <script>
    let G_PROJECTS = [];
    let G_ACTIVE_PROJECT_ID = '';
    let G_ASSETS = {
      project_id: '',
      media_prefix: '',
      project_meta: {},
      style_lock: {},
      characters: [],
      spatial_rooms: {},
      acoustic_spaces: {},
      arc_phases: [],
      images: [],
      final_videos: [],
      raw_clips: []
    };
    let G_EPISODES = [];
    let G_CURRENT_EP = null;
    let G_SELECTED_SCENE_IDX = 0;

    function showToast(message, type = 'info') {
      const container = document.getElementById('toastContainer');
      const el = document.createElement('div');
      const dotColor = type === 'error' ? 'bg-red-400' : type === 'warn' ? 'bg-amber-400' : 'bg-emerald-400';
      el.className = 'toast-item pointer-events-auto surface-card px-3.5 py-2.5 flex items-center gap-2.5 text-xs text-zinc-100 shadow-xl';
      el.innerHTML = `
        <span class="w-2 h-2 rounded-full ${dotColor} shrink-0"></span>
        <span class="leading-relaxed flex-1">${message}</span>
      `;
      container.appendChild(el);
      setTimeout(() => {
        el.style.opacity = '0';
        el.style.transition = 'opacity 0.2s ease';
        setTimeout(() => el.remove(), 220);
      }, 3000);
    }

    window.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        if (!document.getElementById('studioScriptView').classList.contains('hidden')) {
          saveCurrentScript();
        } else {
          saveCurrentEpisode();
        }
      }
    });

    function mediaUrlForProjectPath(relPath) {
      if (!relPath) return '';
      if (relPath.startsWith('http') || relPath.startsWith('/media/')) return relPath;
      const prefix = G_ASSETS.media_prefix || '';
      return `/media${prefix}/${relPath}`;
    }

    function toggleCopilotDrawer(open) {
      const dr = document.getElementById('copilotDrawer');
      if (open) dr.classList.add('open');
      else dr.classList.remove('open');
    }

    function toggleMobileRenderSheet(open) {
      const sh = document.getElementById('mobileRenderSheet');
      if (open) sh.classList.add('open');
      else sh.classList.remove('open');
    }

    function setStudioSubView(mode) {
      const isScript = mode === 'script';
      document.getElementById('studioStoryboardView').classList.toggle('hidden', isScript);
      document.getElementById('studioScriptView').classList.toggle('hidden', !isScript);
      document.getElementById('subViewBtn-storyboard').classList.toggle('active', !isScript);
      document.getElementById('subViewBtn-script').classList.toggle('active', isScript);
    }

    async function initApp() {
      const authRes = await fetch('/api/v1/auth/check');
      const authData = await authRes.json();
      if (!authData.authenticated) {
        const modal = document.getElementById('loginModal');
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        document.getElementById('loginPasswordInput').focus();
        return;
      }
      await refreshAllProjectData();
      connectSse();
    }

    async function refreshAllProjectData() {
      await Promise.all([
        loadProjects(),
        loadSystemStatus(),
        loadAssets(),
        loadEpisodes(),
        loadJobs(),
        loadAgentDemands()
      ]);
      if (G_EPISODES.length > 0) {
        const keepId = G_CURRENT_EP && G_EPISODES.some(e => e.id === G_CURRENT_EP.id)
          ? G_CURRENT_EP.id
          : G_EPISODES[0].id;
        await selectEpisode(keepId);
      } else {
        G_CURRENT_EP = null;
        renderCurrentEpisodeStudio();
      }
    }

    async function submitLogin() {
      const password = document.getElementById('loginPasswordInput').value;
      const errEl = document.getElementById('loginErrorMsg');
      errEl.classList.add('hidden');
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });
      if (res.ok) {
        const modal = document.getElementById('loginModal');
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        showToast('欢迎进入 Director Studio 工作台');
        await initApp();
      } else {
        errEl.textContent = '访问密码不正确，请重试';
        errEl.classList.remove('hidden');
      }
    }

    async function loadProjects() {
      const res = await fetch('/api/v1/projects');
      G_PROJECTS = await res.json();
      const active = G_PROJECTS.find(p => p.is_active) || G_PROJECTS[0];
      if (active) {
        G_ACTIVE_PROJECT_ID = active.id;
      }
      const sel = document.getElementById('projectSwitcher');
      sel.innerHTML = G_PROJECTS.map(p => `
        <option value="${p.id}" ${p.is_active ? 'selected' : ''}>
          ${p.name} (${p.episode_count}集)
        </option>
      `).join('');

      if (active) {
        document.getElementById('activeProjectCardTitle').textContent = active.name;
        document.getElementById('activeProjectCardSub').textContent = `${active.id} · ${active.subtitle || 'Studio Project'} · ${active.aspect}`;
        document.getElementById('assetCenterProjBadge').textContent = `${active.name}`;
      }
    }

    async function switchProject(projectId) {
      const res = await fetch('/api/v1/projects/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId })
      });
      if (res.ok) {
        G_ACTIVE_PROJECT_ID = projectId;
        G_CURRENT_EP = null;
        showToast(`已切换至项目：${projectId}`);
        await refreshAllProjectData();
      }
    }

    function openNewProjectModal() {
      document.getElementById('newProjectModal').classList.remove('hidden');
      document.getElementById('newProjectModal').classList.add('flex');
    }
    function closeNewProjectModal() {
      document.getElementById('newProjectModal').classList.add('hidden');
      document.getElementById('newProjectModal').classList.remove('flex');
    }

    async function createNewProject() {
      const id = document.getElementById('modalProjId').value.trim();
      const name = document.getElementById('modalProjName').value.trim();
      const subtitle = document.getElementById('modalProjSub').value.trim();
      const aspect = document.getElementById('modalProjAspect').value;
      if (!id || !name) {
        showToast('请填写项目英文 ID 与中文名称', 'warn');
        return;
      }
      const res = await fetch('/api/v1/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, name, subtitle, aspect })
      });
      if (res.ok) {
        closeNewProjectModal();
        G_CURRENT_EP = null;
        showToast(`已创建并进入项目《${name}》`);
        await refreshAllProjectData();
      } else {
        showToast(await res.text(), 'error');
      }
    }

    let G_QUOTA_SUMMARY = null;

    function buildQuotaCardsHtml(q) {
      if (!q) return '';
      const colab = q.colab || {};
      const flow = q.flow_video || {};
      const music = q.flow_music || {};

      return `
        <!-- Card 1: Google Colab Cloud GPU -->
        <div class="rounded-2xl p-4 md:p-5 bg-gradient-to-b from-sky-950/25 via-zinc-900/80 to-zinc-950/90 border border-sky-500/30 space-y-4 shadow-lg">
          <div class="flex items-start justify-between gap-2">
            <div class="flex items-center gap-2">
              <div class="w-7 h-7 rounded-lg bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-300">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 00-9.78 2.096A4.001 4.001 0 003 15z"/></svg>
              </div>
              <div>
                <div class="text-xs font-mono uppercase tracking-wider text-sky-400 font-semibold">Google Colab Cloud GPU</div>
                <div class="text-[11px] text-zinc-400">${colab.tier || 'Google AI Ultra'}</div>
              </div>
            </div>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-sky-500/15 text-sky-300 border border-sky-500/30">CLOUD GPU</span>
          </div>

          <div>
            <div class="flex items-baseline justify-between">
              <div class="text-2xl font-bold font-mono text-zinc-100">${(colab.remaining_ccu || 0).toLocaleString()} <span class="text-xs font-normal text-zinc-400">CCU</span></div>
              <div class="text-xs font-mono text-sky-300">${colab.percentage || 0}%</div>
            </div>
            <div class="w-full bg-zinc-800 rounded-full h-2 mt-1.5 overflow-hidden">
              <div class="bg-gradient-to-r from-sky-500 to-cyan-400 h-2 rounded-full transition-all" style="width: ${Math.min(100, Math.max(0, colab.percentage || 0))}%"></div>
            </div>
            <div class="flex justify-between text-[10px] font-mono text-zinc-500 mt-1">
              <span>当前余额 / 总额: ${(colab.total_pool_ccu || 2000).toLocaleString()} CCU</span>
              <span>速率: ${colab.burn_rate || 0} CCU/h</span>
            </div>
          </div>

          <div class="space-y-2.5 pt-2 border-t border-white/[0.06] text-xs">
            <div class="flex items-start justify-between gap-1">
              <span class="text-zinc-400 shrink-0 font-medium">1. 到期时间:</span>
              <span class="font-mono text-zinc-200 text-right text-[11px]">${colab.expires_at || '2026-12-01'} <span class="px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 text-[10px]">剩 ${colab.days_remaining || 26} 天</span></span>
            </div>
            <div class="flex items-start justify-between gap-1">
              <span class="text-zinc-400 shrink-0 font-medium">2. 刷新时间:</span>
              <span class="font-mono text-zinc-300 text-right text-[11px]">${colab.refreshes_at || '每月 1 日 16:00 CST'}</span>
            </div>
            <div class="p-2.5 rounded-xl bg-black/40 border border-white/[0.05] space-y-1.5 font-mono text-[11px]">
              <div class="text-[10px] text-zinc-400 font-sans font-medium">3. 剩余用量与预计可生成时长:</div>
              <div class="flex items-center justify-between text-zinc-200">
                <span class="text-zinc-400">G4 96GB 实例:</span>
                <span class="text-sky-300 font-semibold">${colab.estimates?.g4_video_hours || 0} 小时</span>
              </div>
              <div class="text-[10px] text-emerald-400 pl-2">↳ 预计可生成 ~${(colab.estimates?.estimated_video_minutes || 0).toLocaleString()} 分钟 1080p AI 视频</div>
              <div class="flex items-center justify-between text-zinc-200 pt-0.5">
                <span class="text-zinc-400">L4 24GB 实例:</span>
                <span class="text-cyan-300 font-semibold">${colab.estimates?.l4_audio_hours || 0} 小时</span>
              </div>
              <div class="text-[10px] text-cyan-400 pl-2">↳ 预计可生成 ~${(colab.estimates?.estimated_audio_minutes || 0).toLocaleString()} 分钟 多情绪语音</div>
            </div>
          </div>
        </div>

        <!-- Card 2: Google Flow Video & Image -->
        <div class="rounded-2xl p-4 md:p-5 bg-gradient-to-b from-amber-950/25 via-zinc-900/80 to-zinc-950/90 border border-amber-500/30 space-y-4 shadow-lg">
          <div class="flex items-start justify-between gap-2">
            <div class="flex items-center gap-2">
              <div class="w-7 h-7 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-300">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
              </div>
              <div>
                <div class="text-xs font-mono uppercase tracking-wider text-amber-400 font-semibold">Google Flow Video & Image</div>
                <div class="text-[11px] text-zinc-400">${flow.tier || 'Google AI Ultra'}</div>
              </div>
            </div>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">VEO 3.1 & NANO</span>
          </div>

          <div>
            <div class="flex items-baseline justify-between">
              <div class="text-2xl font-bold font-mono text-zinc-100">${(flow.remaining_credits || 0).toLocaleString()} <span class="text-xs font-normal text-zinc-400">Credits</span></div>
              <div class="text-xs font-mono text-amber-300">${flow.percentage || 0}%</div>
            </div>
            <div class="w-full bg-zinc-800 rounded-full h-2 mt-1.5 overflow-hidden">
              <div class="bg-gradient-to-r from-amber-500 to-yellow-400 h-2 rounded-full transition-all" style="width: ${Math.min(100, Math.max(0, flow.percentage || 0))}%"></div>
            </div>
            <div class="flex justify-between text-[10px] font-mono text-zinc-500 mt-1">
              <span>当前额度 / 总配额: ${(flow.total_credits || 10000).toLocaleString()} 点</span>
              <span>账号: ${flow.account || 'jl.kingbright@gmail.com'}</span>
            </div>
          </div>

          <div class="space-y-2.5 pt-2 border-t border-white/[0.06] text-xs">
            <div class="flex items-start justify-between gap-1">
              <span class="text-zinc-400 shrink-0 font-medium">1. 到期时间:</span>
              <span class="font-mono text-zinc-200 text-right text-[11px]">${flow.expires_at || '2026-12-01'} <span class="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px]">剩 ${flow.days_remaining || 26} 天</span></span>
            </div>
            <div class="flex items-start justify-between gap-1">
              <span class="text-zinc-400 shrink-0 font-medium">2. 刷新时间:</span>
              <span class="font-mono text-zinc-300 text-right text-[11px]">${flow.refreshes_at || '每月 1 日 16:00 CST 自动补满'}</span>
            </div>
            <div class="p-2.5 rounded-xl bg-black/40 border border-white/[0.05] space-y-1.5 font-mono text-[11px]">
              <div class="text-[10px] text-zinc-400 font-sans font-medium">3. 剩余用量与预计可生成时长:</div>
              <div class="flex items-center justify-between text-zinc-200">
                <span class="text-zinc-400">Veo 3.1 Fast:</span>
                <span class="text-amber-300 font-semibold">${flow.estimates?.veo_fast_shots || 0} 镜 (10点/镜)</span>
              </div>
              <div class="text-[10px] text-emerald-400 pl-2">↳ 预计可生成 ~${flow.estimates?.estimated_fast_video_minutes || 0} 分钟 (${(flow.estimates?.estimated_fast_video_seconds || 0).toLocaleString()}秒) 高清视频</div>
              <div class="flex items-center justify-between text-zinc-200 pt-0.5">
                <span class="text-zinc-400">Veo 3.1 Quality:</span>
                <span class="text-yellow-300 font-semibold">${flow.estimates?.veo_quality_shots || 0} 镜 (100点/镜)</span>
              </div>
              <div class="text-[10px] text-yellow-400 pl-2">↳ 预计可生成 ~${flow.estimates?.estimated_quality_video_minutes || 0} 分钟 (${(flow.estimates?.estimated_quality_video_seconds || 0).toLocaleString()}秒) 旗舰母带</div>
              <div class="flex items-center justify-between text-zinc-400 pt-0.5">
                <span>Nano-Pro 定妆生图:</span>
                <span class="text-emerald-400 font-semibold">${flow.estimates?.nano_pro_images || '0点/张 (无限免费 ∞ 张)'}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Card 3: Google Flow Music & ACE-Step 1.5 -->
        <div class="rounded-2xl p-4 md:p-5 bg-gradient-to-b from-purple-950/25 via-zinc-900/80 to-zinc-950/90 border border-purple-500/30 space-y-4 shadow-lg">
          <div class="flex items-start justify-between gap-2">
            <div class="flex items-center gap-2">
              <div class="w-7 h-7 rounded-lg bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-300">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/></svg>
              </div>
              <div>
                <div class="text-xs font-mono uppercase tracking-wider text-purple-400 font-semibold">Google Flow Music</div>
                <div class="text-[11px] text-zinc-400">${music.tier || 'MusicFX / Lyria 2 + ACE-Step 1.5'}</div>
              </div>
            </div>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/30">MUSICFX & ACE</span>
          </div>

          <div>
            <div class="flex items-baseline justify-between">
              <div class="text-2xl font-bold font-mono text-zinc-100">${music.daily_remaining_tracks || 500} <span class="text-xs font-normal text-zinc-400">/ ${music.daily_quota_tracks || 500} 首 (今日)</span></div>
              <div class="text-xs font-mono text-purple-300">100% (0点扣减)</div>
            </div>
            <div class="w-full bg-zinc-800 rounded-full h-2 mt-1.5 overflow-hidden">
              <div class="bg-gradient-to-r from-purple-500 to-pink-400 h-2 rounded-full transition-all" style="width: 100%"></div>
            </div>
            <div class="flex justify-between text-[10px] font-mono text-zinc-500 mt-1">
              <span>扣点规则: 0 Credits 扣减 (免费额度)</span>
              <span>本地状态: 无限时长合成</span>
            </div>
          </div>

          <div class="space-y-2.5 pt-2 border-t border-white/[0.06] text-xs">
            <div class="flex items-start justify-between gap-1">
              <span class="text-zinc-400 shrink-0 font-medium">1. 到期时间:</span>
              <span class="font-mono text-zinc-200 text-right text-[11px]">${music.expires_at || '2026-12-01'} <span class="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 text-[10px]">随 Ultra 订阅长效</span></span>
            </div>
            <div class="flex items-start justify-between gap-1">
              <span class="text-zinc-400 shrink-0 font-medium">2. 刷新时间:</span>
              <span class="font-mono text-zinc-300 text-right text-[11px]">${music.refreshes_at || '每日 16:00 CST 自动刷新日度配额'}</span>
            </div>
            <div class="p-2.5 rounded-xl bg-black/40 border border-white/[0.05] space-y-1.5 font-mono text-[11px]">
              <div class="text-[10px] text-zinc-400 font-sans font-medium">3. 剩余用量与预计可生成时长:</div>
              <div class="flex items-center justify-between text-zinc-200">
                <span class="text-zinc-400">MusicFX / Lyria 2:</span>
                <span class="text-purple-300 font-semibold">今日预计 ~${music.estimates?.estimated_music_minutes || 250} 分钟</span>
              </div>
              <div class="text-[10px] text-pink-400 pl-2">↳ 按日度 500 首 × 30s 高保真配乐折算</div>
              <div class="flex items-center justify-between text-zinc-200 pt-0.5">
                <span class="text-zinc-400">SoundFX 戏剧拟音:</span>
                <span class="text-purple-300 font-semibold">~${music.estimates?.estimated_sfx_count || 1000} 条电影拟音</span>
              </div>
              <div class="flex items-center justify-between text-zinc-400 pt-0.5">
                <span>ACE-Step 1.5 本地/Cubex:</span>
                <span class="text-emerald-400 font-semibold">无限时长 ∞ (本地离线合成)</span>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    function renderQuotaDashboard(q) {
      const html = buildQuotaCardsHtml(q);
      const queueCards = document.getElementById('queueQuotaCards');
      if (queueCards) queueCards.innerHTML = html;
      const modalCards = document.getElementById('modalQuotaCards');
      if (modalCards) modalCards.innerHTML = html;
      const updatedEl = document.getElementById('queueQuotaUpdated');
      if (updatedEl && q.updated_at) updatedEl.textContent = `更新时间: ${q.updated_at}`;

      if (q.lane_utilization) {
        const u = q.lane_utilization;
        const bFlow = document.getElementById('laneBadgeFlow');
        if (bFlow) bFlow.textContent = `${u.flow_active} / ${u.flow_max} 槽`;
        const bColab = document.getElementById('laneBadgeColab');
        if (bColab) bColab.textContent = `${u.colab_g4_active} / ${u.colab_g4_max} 槽`;
        const bSume = document.getElementById('laneBadgeSume');
        if (bSume) bSume.textContent = `${u.sume_active} / ${u.sume_max} 槽`;
        const bAudio = document.getElementById('laneBadgeAudio');
        if (bAudio) bAudio.textContent = `${u.audio_tts_active} / ${u.audio_tts_max} 槽`;
        const bRocm = document.getElementById('laneBadgeRocm');
        if (bRocm) bRocm.textContent = `${u.local_rocm_active} / ${u.local_rocm_max} 槽`;
      }

      if (q.concurrency_config) {
        const c = q.concurrency_config;
        const iFlow = document.getElementById('cfgFlowConcurrency');
        if (iFlow && !iFlow.matches(':focus')) iFlow.value = c.flow_concurrency;
        const iColab = document.getElementById('cfgColabConcurrency');
        if (iColab && !iColab.matches(':focus')) iColab.value = c.colab_g4_concurrency;
        const iSume = document.getElementById('cfgSumeConcurrency');
        if (iSume && !iSume.matches(':focus')) iSume.value = c.sume_concurrency;
        const iAudio = document.getElementById('cfgAudioConcurrency');
        if (iAudio && !iAudio.matches(':focus')) iAudio.value = c.audio_tts_concurrency;
        const iRocm = document.getElementById('cfgRocmConcurrency');
        if (iRocm && !iRocm.matches(':focus')) iRocm.value = c.local_rocm_concurrency;
      }
    }

    async function saveConcurrencyConfig() {
      const flow_concurrency = parseInt(document.getElementById('cfgFlowConcurrency').value) || 8;
      const colab_g4_concurrency = parseInt(document.getElementById('cfgColabConcurrency').value) || 4;
      const sume_concurrency = parseInt(document.getElementById('cfgSumeConcurrency').value) || 8;
      const audio_tts_concurrency = parseInt(document.getElementById('cfgAudioConcurrency').value) || 6;
      const local_rocm_concurrency = parseInt(document.getElementById('cfgRocmConcurrency').value) || 2;

      try {
        const res = await fetch('/api/v1/queue/concurrency', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            flow_concurrency,
            colab_g4_concurrency,
            sume_concurrency,
            audio_tts_concurrency,
            local_rocm_concurrency
          })
        });
        const data = await res.json();
        if (res.ok && data.ok) {
          showToast('✅ 全通道并发调度池配置已保存生效！');
          await refreshQuotaSummary();
        } else {
          showToast('保存并发配置失败', 'error');
        }
      } catch (e) {
        showToast('保存配置异常', 'error');
      }
    }

    async function refreshQuotaSummary() {
      try {
        const res = await fetch('/api/v1/quota/summary');
        if (res.ok) {
          const quota = await res.json();
          G_QUOTA_SUMMARY = quota;
          const topColab = document.getElementById('topColabBadge');
          if (topColab && quota.colab) {
            topColab.textContent = `${quota.colab.remaining_ccu.toLocaleString()} CCU`;
          }
          if (quota.flow_video) {
            document.getElementById('creditBalance').textContent = `${quota.flow_video.remaining_credits.toLocaleString()} Cr`;
          }
          renderQuotaDashboard(quota);
        }
      } catch (e) {
        console.error('Quota summary error:', e);
      }
    }

    function openQuotaModal() {
      if (!G_QUOTA_SUMMARY) {
        refreshQuotaSummary();
      } else {
        renderQuotaDashboard(G_QUOTA_SUMMARY);
      }
      const modal = document.getElementById('quotaDetailModal');
      if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
      }
    }

    function closeQuotaModal() {
      const modal = document.getElementById('quotaDetailModal');
      if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
      }
    }

    async function testGenerateMusic() {
      const prompt = document.getElementById('musicPromptInput').value.trim();
      const mood = document.getElementById('musicMoodSelect').value;
      const duration_sec = parseFloat(document.getElementById('musicDurationInput').value) || 15.0;
      const statusEl = document.getElementById('musicGenStatus');
      const btn = document.getElementById('btnGenerateMusic');

      if (!prompt) {
        showToast('请输入配乐提示词', 'error');
        return;
      }

      btn.disabled = true;
      statusEl.textContent = '⏳ 正在调度 Google Flow Music / ACE-Step 引擎并母带混音中...';

      try {
        const res = await fetch('/api/v1/music/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, mood, duration_sec })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          statusEl.innerHTML = `<span class="text-emerald-400">✓ ${data.message}</span> (${data.engine})`;
          const playerBox = document.getElementById('musicAudioPlayerBox');
          const player = document.getElementById('musicAudioPlayer');
          const fname = data.output_path.split('/').pop().split('\\\\').pop();
          player.src = `/media/renders/${encodeURIComponent(fname)}`;
          player.onerror = () => {
            player.src = `/media/projects?file=${encodeURIComponent(fname)}`;
          };
          playerBox.classList.remove('hidden');
          player.play().catch(() => {});
          showToast(`已生成配乐: ${data.engine}`);
        } else {
          statusEl.textContent = `❌ 生成失败: ${data.message || '未知错误'}`;
          showToast(`生成失败: ${data.message || '未知错误'}`, 'error');
        }
      } catch (e) {
        statusEl.textContent = `❌ 请求错误: ${e.message}`;
        showToast('请求超时或网络异常', 'error');
      } finally {
        btn.disabled = false;
      }
    }

    async function loadSystemStatus() {
      try {
        const res = await fetch('/api/v1/system/status');
        const data = await res.json();
        G_ACTIVE_PROJECT_ID = data.active_project_id || G_ACTIVE_PROJECT_ID;
        document.getElementById('gpuBadge').textContent = `${data.local_gpu.device_name} ${data.local_gpu.vram_gb}G`;
        document.getElementById('creditBalance').textContent = `${data.credits.balance.toLocaleString()} Cr`;
        const mBal = document.getElementById('mobileCreditBalance');
        if (mBal) mBal.textContent = `${data.credits.balance.toLocaleString()} 点 (Q:${data.credits.clips_quality}镜 / F:${data.credits.clips_fast}镜)`;
        document.getElementById('creditCapacity').textContent = `· Q:${data.credits.clips_quality}镜 / F:${data.credits.clips_fast}镜`;
        document.getElementById('chkQualityApproval').checked = data.require_approval_for_quality;
        document.getElementById('inpDailyLimit').value = data.daily_credit_limit;

        if (data.quota_summary) {
          G_QUOTA_SUMMARY = data.quota_summary;
          const colab = data.quota_summary.colab;
          if (colab) {
            const topColab = document.getElementById('topColabBadge');
            if (topColab) topColab.textContent = `${colab.remaining_ccu.toLocaleString()} CCU`;
          }
          renderQuotaDashboard(data.quota_summary);
        } else {
          refreshQuotaSummary();
        }

        const badge = document.getElementById('pendingBadge');
        if (data.pending_approvals_count > 0) {
          badge.textContent = data.pending_approvals_count;
          badge.classList.remove('hidden');
        } else {
          badge.classList.add('hidden');
        }
      } catch (e) {
        console.error('Status error:', e);
      }
    }

    async function loadAssets() {
      const res = await fetch('/api/v1/assets');
      G_ASSETS = await res.json();
      const charCount = (G_ASSETS.characters || []).length;
      const imgCount = (G_ASSETS.images || []).length;
      const roomCount = Object.keys(G_ASSETS.spatial_rooms || {}).length;
      const clipCount = (G_ASSETS.final_videos || []).length + (G_ASSETS.raw_clips || []).length;

      document.getElementById('statChars').textContent = charCount;
      document.getElementById('statImages').textContent = imgCount;
      document.getElementById('statRooms').textContent = roomCount;
      document.getElementById('statClips').textContent = clipCount;
      document.getElementById('assetSummaryBadge').textContent = `${charCount + imgCount + roomCount}`;

      renderAssetsTab();
      renderStudioQuickAssetBar();
      renderTheaterTab();
    }

    function renderStudioQuickAssetBar() {
      const bar = document.getElementById('studioQuickAssetBar');
      if (!bar) return;
      const chars = (G_ASSETS.characters || []).map(c => `
        <button onclick="injectCharacterIntoSelectedScene('${c.name}')" class="px-2 py-1 rounded-md bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-[11px] font-mono text-zinc-200 shrink-0">
          @${c.name}
        </button>
      `).join('');

      const rooms = Object.keys(G_ASSETS.spatial_rooms || {}).map(r => `
        <button onclick="injectRoomIntoSelectedScene('${r}')" class="px-2 py-1 rounded-md bg-white/[0.03] hover:bg-white/[0.09] border border-white/[0.06] text-[11px] font-mono text-zinc-400 shrink-0">
          #${r}
        </button>
      `).join('');

      bar.innerHTML = `
        <span class="text-[11px] text-zinc-500 mr-0.5 shrink-0">镜头 <strong class="text-zinc-200 font-mono">#${String(G_SELECTED_SCENE_IDX + 1).padStart(2, '0')}</strong> 注入:</span>
        ${chars || '<span class="text-xs text-zinc-600">无角色</span>'}
        <span class="text-zinc-800 mx-0.5">/</span>
        ${rooms || '<span class="text-xs text-zinc-600">无空间</span>'}
      `;
    }

    function selectFocusScene(idx) {
      if (G_SELECTED_SCENE_IDX === idx) return;
      G_SELECTED_SCENE_IDX = idx;
      renderStudioQuickAssetBar();
      document.querySelectorAll('[data-scene-card]').forEach((el, i) => {
        el.classList.toggle('surface-card-selected', i === idx);
      });
    }

    function injectCharacterIntoSelectedScene(charName) {
      if (!G_CURRENT_EP || !G_CURRENT_EP.scenes[G_SELECTED_SCENE_IDX]) {
        showToast('请先选择或新建一幕分镜', 'warn');
        return;
      }
      const sc = G_CURRENT_EP.scenes[G_SELECTED_SCENE_IDX];
      sc.characters = sc.characters || [];
      if (!sc.characters.includes(charName)) {
        sc.characters.push(charName);
      }
      if (!sc.speaker) {
        sc.speaker = charName;
      }
      if (!sc.action.includes(`@${charName}`)) {
        sc.action = `@${charName} ${sc.action}`.trim();
      }
      const cObj = (G_ASSETS.characters || []).find(c => c.name === charName);
      if (cObj) {
        const bestImg = (sc.era === 'modern' ? cObj.ref_image_modern : cObj.ref_image_ancient) || cObj.ref_image;
        if (bestImg && !sc.ref_image) {
          sc.ref_image = bestImg;
        }
      }
      renderCurrentEpisodeStudio();
      showToast(`已将角色 @${charName} 注入镜头 #${G_SELECTED_SCENE_IDX + 1}`);
    }

    function injectRoomIntoSelectedScene(roomId) {
      if (!G_CURRENT_EP || !G_CURRENT_EP.scenes[G_SELECTED_SCENE_IDX]) return;
      const sc = G_CURRENT_EP.scenes[G_SELECTED_SCENE_IDX];
      sc.room_id = roomId;
      const rObj = (G_ASSETS.spatial_rooms || {})[roomId];
      if (rObj) {
        if (rObj.interior_anchor_image && !sc.ref_image) {
          sc.ref_image = rObj.interior_anchor_image;
        }
        if (rObj.center_foreground && !sc.action.toLowerCase().includes(rObj.center_foreground.toLowerCase())) {
          sc.action = `${sc.action.replace(/\.$/, '')}, positioned near ${rObj.center_foreground}, with ${rObj.camera_left}.`;
        }
      }
      renderCurrentEpisodeStudio();
      showToast(`已将空间 #${roomId} 绑定至镜头 #${G_SELECTED_SCENE_IDX + 1}`);
    }

    function openAssetPickerForScene(sceneIdx) {
      G_SELECTED_SCENE_IDX = sceneIdx;
      openAssetPickerForCurrentScene();
    }

    function openAssetPickerForCurrentScene() {
      if (!G_CURRENT_EP || !G_CURRENT_EP.scenes.length) {
        showToast('请先选择或新建一个剧集', 'warn');
        return;
      }
      const sc = G_CURRENT_EP.scenes[G_SELECTED_SCENE_IDX] || G_CURRENT_EP.scenes[0];
      document.getElementById('assetPickerTargetLabel').textContent = `正在为镜头 #${G_SELECTED_SCENE_IDX + 1} (${sc.id}) 选择首帧参考母图`;
      const grid = document.getElementById('assetPickerGrid');
      const imgs = G_ASSETS.images || [];
      if (imgs.length === 0) {
        grid.innerHTML = `<div class="col-span-full py-12 text-center text-xs text-zinc-500">当前项目暂无母图，请先前往「资产库 → 首帧母图」上传</div>`;
      } else {
        grid.innerHTML = imgs.map(img => {
          const isCurrent = sc.ref_image === img.rel_path;
          return `
            <div onclick="applyImageToSelectedScene('${img.rel_path}'); closeAssetPickerModal();" class="rounded-xl overflow-hidden bg-zinc-900 border ${isCurrent ? 'border-white ring-1 ring-white/40' : 'border-white/[0.08]'} cursor-pointer transition">
              <div class="aspect-video bg-black overflow-hidden">
                <img src="${img.url}" class="w-full h-full object-cover" />
              </div>
              <div class="p-2 flex items-center justify-between gap-1">
                <span class="text-[11px] font-mono text-zinc-200 truncate">${img.name}</span>
                ${isCurrent ? `<span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-950 font-semibold shrink-0">当前</span>` : ''}
              </div>
            </div>
          `;
        }).join('');
      }
      const modal = document.getElementById('assetPickerModal');
      modal.classList.remove('hidden');
      modal.classList.add('flex');
    }

    function closeAssetPickerModal() {
      const modal = document.getElementById('assetPickerModal');
      modal.classList.add('hidden');
      modal.classList.remove('flex');
    }

    function applyImageToSelectedScene(relPath) {
      if (!G_CURRENT_EP || !G_CURRENT_EP.scenes || G_CURRENT_EP.scenes.length === 0) {
        showToast('当前项目还没有打开的剧集分镜', 'warn');
        return;
      }
      const idx = G_SELECTED_SCENE_IDX < G_CURRENT_EP.scenes.length ? G_SELECTED_SCENE_IDX : 0;
      G_CURRENT_EP.scenes[idx].ref_image = relPath;
      switchTab('studio');
      renderCurrentEpisodeStudio();
      showToast(`已将母图设为镜头 #${idx + 1} 首帧`);
    }

    async function loadEpisodes() {
      const res = await fetch('/api/v1/episodes');
      G_EPISODES = await res.json();
      renderEpisodeList();
      renderTheaterTab();
    }

    function renderEpisodeList() {
      const box = document.getElementById('episodeList');
      const mobilePills = document.getElementById('mobileEpisodePills');

      if (G_EPISODES.length === 0) {
        const emptyHtml = `<div class="p-3 rounded-xl bg-zinc-900/40 border border-white/[0.05] text-xs text-zinc-500 text-center">暂无剧集，点击右上角「新剧集」</div>`;
        if (box) box.innerHTML = emptyHtml;
        if (mobilePills) mobilePills.innerHTML = `<span class="text-xs text-zinc-500">当前项目暂无剧集</span>`;
        return;
      }

      if (box) {
        box.innerHTML = G_EPISODES.map(ep => {
          const active = G_CURRENT_EP && G_CURRENT_EP.id === ep.id;
          const dot = ep.lint_passed
            ? `<span class="w-1.5 h-1.5 rounded-full bg-emerald-400" title="门禁通过"></span>`
            : `<span class="px-1.5 py-0.2 rounded bg-red-500/15 text-red-400 text-[10px] font-mono">${ep.error_count}</span>`;
          return `
            <div onclick="selectEpisode('${ep.id}')" class="px-3 py-2.5 rounded-xl cursor-pointer transition border ${active ? 'bg-zinc-800/90 border-white/20 shadow-sm' : 'bg-zinc-900/30 border-white/[0.04] hover:bg-zinc-900/70'}">
              <div class="flex items-center justify-between gap-2">
                <span class="text-xs font-medium ${active ? 'text-white' : 'text-zinc-300'} truncate">${ep.title}</span>
                ${dot}
              </div>
              <div class="flex items-center justify-between mt-1 text-[10px] font-mono text-zinc-500">
                <span>${ep.scene_count} SHOTS</span>
                <span>${ep.final_videos.length} MASTER</span>
              </div>
            </div>
          `;
        }).join('');
      }

      if (mobilePills) {
        mobilePills.innerHTML = G_EPISODES.map(ep => {
          const active = G_CURRENT_EP && G_CURRENT_EP.id === ep.id;
          return `
            <button onclick="selectEpisode('${ep.id}')" class="px-3 py-1.5 rounded-lg text-xs font-medium shrink-0 transition border ${active ? 'bg-zinc-100 text-zinc-950 border-zinc-100 font-semibold' : 'bg-zinc-900 text-zinc-400 border-white/[0.07]'}">
              ${ep.title}
            </button>
          `;
        }).join('');
      }
    }

    async function selectEpisode(epId) {
      const res = await fetch(`/api/v1/episodes/${epId}`);
      if (!res.ok) return;
      G_CURRENT_EP = await res.json();
      G_SELECTED_SCENE_IDX = 0;
      renderEpisodeList();
      renderCurrentEpisodeStudio();
      renderStudioQuickAssetBar();
    }

    function renderCurrentEpisodeStudio() {
      const container = document.getElementById('sceneCardsContainer');
      if (!G_CURRENT_EP) {
        document.getElementById('currentEpTitle').textContent = '当前项目暂无剧集';
        document.getElementById('currentEpMeta').textContent = '';
        container.innerHTML = `
          <div class="surface-card p-10 md:p-14 text-center space-y-3 mt-4">
            <div class="text-sm font-semibold text-zinc-200">开始创建本项目的第一集分镜</div>
            <p class="text-xs text-zinc-500 max-w-md mx-auto">可先在「资产库」配置角色、上传首帧参考母图，或直接点击下方按钮用一句话故事梗概自动生成分镜。</p>
            <button onclick="openNewEpisodeModal()" class="px-4 py-2.5 btn-white text-xs">+ 新建第一集</button>
          </div>
        `;
        return;
      }

      document.getElementById('currentEpTitle').textContent = G_CURRENT_EP.title;
      document.getElementById('currentEpMeta').textContent =
        `${G_CURRENT_EP.dir_name} · ${G_CURRENT_EP.scenes.length} SHOTS`;
      document.getElementById('scriptMarkdownEditor').value = G_CURRENT_EP.script_markdown || '';

      const rep = G_CURRENT_EP.lint_report;
      const pill = document.getElementById('lintStatusPill');
      const studioLintBtn = document.getElementById('studioLintBadgeBtn');
      const headerDot = document.getElementById('headerLintDot');

      if (rep.passed) {
        pill.className = 'text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
        pill.textContent = '0 ERRORS';
        studioLintBtn.className = 'px-2 py-0.5 rounded-md text-[11px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
        studioLintBtn.textContent = '✓ 合规';
        headerDot.className = 'w-2 h-2 rounded-full bg-emerald-400';
      } else {
        pill.className = 'text-[11px] font-mono px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20';
        pill.textContent = `${rep.error_count} ERRORS`;
        studioLintBtn.className = 'px-2 py-0.5 rounded-md text-[11px] font-mono bg-red-500/15 text-red-300 border border-red-500/30';
        studioLintBtn.textContent = `! ${rep.error_count} 项待修复`;
        headerDot.className = 'w-2 h-2 rounded-full bg-red-400';
      }

      const issuesBox = document.getElementById('lintIssuesBox');
      if (rep.issues.length === 0) {
        issuesBox.innerHTML = `<div class="p-3 rounded-lg bg-zinc-900/70 border border-white/[0.06] text-zinc-300">全部镜头通过 L1-L5 门禁与资产完整性校验。</div>`;
      } else {
        issuesBox.innerHTML = rep.issues.map(iss => `
          <div class="p-3 rounded-lg ${iss.level === 'ERROR' ? 'bg-red-950/30 border border-red-500/30' : 'bg-zinc-900 border border-white/[0.07]'}">
            <div class="font-mono font-semibold ${iss.level === 'ERROR' ? 'text-red-400' : 'text-amber-400'}">[${iss.layer}] ${iss.scene_id}</div>
            <div class="text-zinc-200 mt-1">${iss.message}</div>
            <div class="text-zinc-400 mt-1 text-[11px]">建议: ${iss.suggestion}</div>
          </div>
        `).join('');
      }

      const finalsBar = document.getElementById('epFinalVideosBar');
      const finalsList = document.getElementById('epFinalVideosList');
      if (G_CURRENT_EP.final_videos && G_CURRENT_EP.final_videos.length > 0) {
        finalsBar.classList.remove('hidden');
        finalsList.innerHTML = G_CURRENT_EP.final_videos.slice(0, 8).map(v => `
          <button onclick="openVideoModal('${v.url}', '${v.name}')" class="shrink-0 px-3 py-2 btn-ghost text-left">
            <div class="text-xs font-medium text-zinc-100 truncate max-w-[200px]">▶ ${v.name}</div>
            <div class="text-[10px] font-mono text-zinc-500">${v.engine_tag} · ${(v.size_bytes / 1024 / 1024).toFixed(1)} MB</div>
          </button>
        `).join('');
      } else {
        finalsBar.classList.add('hidden');
      }

      const acousticOpts = Object.keys(G_ASSETS.acoustic_spaces || {});
      const roomOpts = ['', ...Object.keys(G_ASSETS.spatial_rooms || {})];
      const phaseOpts = (G_ASSETS.arc_phases && G_ASSETS.arc_phases.length) ? G_ASSETS.arc_phases : [
        'P1_Hook_Tension', 'P2_Escalation', 'P3_Climax_Turn', 'P4_Resolution'
      ];
      const projectChars = (G_ASSETS.characters || []).map(c => c.name);

      container.innerHTML = G_CURRENT_EP.scenes.map((sc, idx) => {
        const isFocused = idx === G_SELECTED_SCENE_IDX;
        const refUrl = sc.ref_image ? mediaUrlForProjectPath(sc.ref_image) : '';
        const clips = (G_CURRENT_EP.scene_media && G_CURRENT_EP.scene_media[sc.id]) || [];
        const activeChars = sc.characters || [];

        return `
          <div data-scene-card onclick="selectFocusScene(${idx})" class="surface-card p-3.5 md:p-4 ${isFocused ? 'surface-card-selected' : ''}">
            <!-- 卡片顶栏：移动端与桌面端自适应 -->
            <div class="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-white/[0.06]">
              <div class="flex flex-wrap items-center gap-1.5 flex-1 min-w-0">
                <span class="px-2 py-0.5 rounded-md font-mono text-xs ${isFocused ? 'bg-zinc-100 text-zinc-950 font-semibold' : 'bg-white/[0.06] text-zinc-300'}">#${String(idx + 1).padStart(2, '0')}</span>
                <input onchange="updateSceneField(${idx}, 'id', this.value)" value="${sc.id}" class="px-2 py-1 field-input text-xs font-mono w-32 sm:w-44" />
                <select onchange="updateSceneField(${idx}, 'era', this.value)" class="px-2 py-1 field-input text-xs">
                  <option value="modern" ${sc.era === 'modern' ? 'selected' : ''}>现代/日常</option>
                  <option value="ancient" ${sc.era === 'ancient' ? 'selected' : ''}>特殊/古风</option>
                </select>
                <select onchange="updateSceneField(${idx}, 'arc_phase', this.value)" class="px-2 py-1 field-input text-xs font-mono text-zinc-300 max-w-[150px] sm:max-w-none">
                  ${phaseOpts.map(p => `<option value="${p}" ${sc.arc_phase === p ? 'selected' : ''}>${p}</option>`).join('')}
                </select>
              </div>

              <div class="flex items-center gap-1.5 w-full sm:w-auto justify-end pt-1 sm:pt-0">
                <button onclick="event.stopPropagation(); polishSceneWithAi(${idx})" class="flex-1 sm:flex-initial px-2.5 py-1.5 sm:py-1 btn-ghost text-xs">
                  AI 润色
                </button>
                <button onclick="event.stopPropagation(); submitSingleSceneRender('${sc.id}', 'minimax-h3')" class="flex-1 sm:flex-initial px-2.5 py-1.5 sm:py-1 btn-ghost text-xs">
                  本机预演
                </button>
                <button onclick="event.stopPropagation(); submitSingleSceneRender('${sc.id}', 'veo-fast')" class="flex-1 sm:flex-initial px-2.5 py-1.5 sm:py-1 btn-ghost text-xs">
                  Fast 重绘
                </button>
                <button onclick="event.stopPropagation(); submitSingleSceneRender('${sc.id}', 'heygen-video-1')" class="flex-1 sm:flex-initial px-2.5 py-1.5 sm:py-1 btn-ghost text-xs text-emerald-300" title="Sume HeyGen Video 1">
                  HeyGen
                </button>
                <button onclick="event.stopPropagation(); submitSingleSceneRender('${sc.id}', 'seedance-2.5')" class="flex-1 sm:flex-initial px-2.5 py-1.5 sm:py-1 btn-ghost text-xs" title="Sume Seedance 2.5">
                  Seedance 2.5
                </button>
                <button onclick="event.stopPropagation(); removeScene(${idx})" title="删除此镜头" class="px-2.5 py-1.5 sm:py-1 btn-ghost text-zinc-500 hover:text-red-400 text-xs">✕</button>
              </div>
            </div>

            <!-- 镜头三列主体 -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
              <!-- 左列：首帧母图 + 空间/声学 -->
              <div class="lg:col-span-3 space-y-2.5">
                <div class="aspect-video rounded-lg overflow-hidden bg-zinc-950 border border-white/[0.08] relative">
                  ${refUrl
                    ? `<img src="${refUrl}" onclick="event.stopPropagation(); openImageModal('${refUrl}', '${sc.ref_image}')" class="w-full h-full object-cover cursor-pointer" />`
                    : `<div onclick="event.stopPropagation(); openAssetPickerForScene(${idx})" class="w-full h-full flex flex-col items-center justify-center text-xs text-zinc-500 cursor-pointer">
                         <span>+ 点击选择首帧母图</span>
                       </div>`
                  }
                  <button onclick="event.stopPropagation(); openAssetPickerForScene(${idx})" class="absolute bottom-2 right-2 px-2.5 py-1 rounded-md bg-black/80 text-[11px] text-zinc-100 border border-white/15 backdrop-blur-sm">
                    更换母图
                  </button>
                </div>

                <div class="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <label class="text-[10px] text-zinc-500 block mb-1">三维空间拓扑</label>
                    <select onchange="updateSceneRoom(${idx}, this.value)" class="w-full px-2 py-1.5 field-input font-mono text-[11px]">
                      ${roomOpts.map(r => `<option value="${r}" ${(sc.room_id || '') === r ? 'selected' : ''}>${r || '(外景/自由)'}</option>`).join('')}
                    </select>
                  </div>
                  <div>
                    <label class="text-[10px] text-zinc-500 block mb-1">声学滤波环境</label>
                    <select onchange="updateSceneField(${idx}, 'acoustic_space', this.value)" class="w-full px-2 py-1.5 field-input font-mono text-[11px]">
                      ${acousticOpts.map(a => `<option value="${a}" ${sc.acoustic_space === a ? 'selected' : ''}>${a}</option>`).join('')}
                    </select>
                  </div>
                </div>
              </div>

              <!-- 中列：角色胶囊 + 台词 + 画面描述 -->
              <div class="lg:col-span-6 space-y-2.5 text-xs">
                <div class="flex flex-wrap items-center gap-1.5">
                  <span class="text-[11px] text-zinc-500 mr-0.5">登场角色:</span>
                  ${projectChars.map(cname => {
                    const on = activeChars.includes(cname);
                    return `<button onclick="event.stopPropagation(); toggleSceneCharacter(${idx}, '${cname}')" class="px-2 py-0.5 rounded-md font-mono text-[11px] border transition ${on ? 'bg-zinc-100 text-zinc-950 border-zinc-100 font-semibold' : 'bg-zinc-900/80 border-white/[0.07] text-zinc-400'}">@${cname}</button>`;
                  }).join('')}
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <div>
                    <label class="text-zinc-500 block mb-1 text-[11px]">说话人 (Speaker)</label>
                    <select onchange="updateSceneField(${idx}, 'speaker', this.value)" class="w-full px-2.5 py-1.5 field-input font-medium">
                      <option value="">(无台词/旁白)</option>
                      ${projectChars.map(cname => `<option value="${cname}" ${sc.speaker === cname ? 'selected' : ''}>${cname}</option>`).join('')}
                    </select>
                  </div>
                  <div class="sm:col-span-2">
                    <label class="text-zinc-500 block mb-1 text-[11px]">镜头焦段与运镜参数</label>
                    <input onchange="updateSceneField(${idx}, 'camera_motion', this.value)" value="${sc.camera_motion || ''}" class="w-full px-2.5 py-1.5 field-input font-mono" />
                  </div>
                </div>

                <div>
                  <label class="text-zinc-400 block mb-1 text-[11px]">中文台词 / 旁白</label>
                  <textarea onchange="updateSceneField(${idx}, 'line', this.value)" rows="2" placeholder="输入本镜头角色对白或旁白..." class="w-full px-3 py-1.5 field-input text-sm">${sc.line || ''}</textarea>
                </div>

                <div>
                  <div class="flex items-center justify-between mb-1">
                    <label class="text-zinc-500 text-[11px]">摄影级画面描述 (Action Prompt)</label>
                    <button onclick="event.stopPropagation(); promptChineseVisualHint(${idx})" class="text-[11px] text-zinc-300 hover:text-white">中文转写 →</button>
                  </div>
                  <textarea onchange="updateSceneField(${idx}, 'action', this.value)" rows="3" class="w-full px-3 py-2 field-input font-mono text-[11px] leading-relaxed text-zinc-300">${sc.action || ''}</textarea>
                </div>
              </div>

              <!-- 右列：本镜历史生成片段 Takes & 非破坏性微剪分轨配置 -->
              <div class="lg:col-span-3 flex flex-col justify-between bg-[#0c0c0f] rounded-lg p-3 border border-white/[0.05] space-y-2.5">
                <div>
                  <div class="flex items-center justify-between mb-2">
                    <span class="text-[11px] font-mono uppercase text-zinc-400">TAKES (${clips.length})</span>
                    <span class="text-[10px] font-mono text-zinc-500">${sc.duration || 8}s · ${sc.shot_count || 5}镜 · ${sc.aspect || '16:9'}</span>
                  </div>
                  ${clips.length === 0 ? `<div class="text-xs text-zinc-600 py-3 text-center">暂无单镜渲染成片</div>` : `
                    <div class="space-y-1.5 max-h-28 overflow-y-auto">
                      ${clips.map(c => `
                        <button onclick="event.stopPropagation(); openVideoModal('${c.url}', '${c.name}')" class="w-full px-2.5 py-1.5 btn-ghost text-left flex items-center justify-between gap-1">
                          <span class="text-[11px] font-mono text-zinc-200 truncate">▶ ${c.name}</span>
                          <span class="text-[10px] font-mono text-zinc-500 shrink-0">${(c.size_bytes/1024/1024).toFixed(1)}M</span>
                        </button>
                      `).join('')}
                    </div>
                  `}
                </div>

                <div class="pt-2 border-t border-white/[0.06] space-y-2 text-[11px]">
                  <div class="grid grid-cols-3 gap-1.5">
                    <div>
                      <label class="text-[10px] text-zinc-500 block">切镜数</label>
                      <input type="number" min="1" max="6" value="${sc.shot_count || 5}" onchange="updateSceneField(${idx}, 'shot_count', parseInt(this.value)||5)" class="w-full px-1.5 py-1 field-input font-mono text-[11px]" />
                    </div>
                    <div>
                      <label class="text-[10px] text-zinc-500 block">掐头(s)</label>
                      <input type="number" step="0.05" min="0" value="${sc.trim_start_sec || 0}" onchange="updateSceneField(${idx}, 'trim_start_sec', parseFloat(this.value)||0)" class="w-full px-1.5 py-1 field-input font-mono text-[11px]" />
                    </div>
                    <div>
                      <label class="text-[10px] text-zinc-500 block">去尾毛刺</label>
                      <input type="number" step="0.05" min="0" value="${sc.trim_end_sec ?? 0.15}" onchange="updateSceneField(${idx}, 'trim_end_sec', parseFloat(this.value)||0)" class="w-full px-1.5 py-1 field-input font-mono text-[11px]" />
                    </div>
                  </div>
                  <div>
                    <input placeholder="MMAudio 动作拟音提示 (如: 拔剑金属声)" value="${sc.foley_cue || ''}" onchange="updateSceneField(${idx}, 'foley_cue', this.value)" class="w-full px-2 py-1 field-input text-[11px]" />
                  </div>
                  <div class="text-[10px] font-mono text-zinc-500 truncate">
                    REF: ${sc.ref_image || '未绑定'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    function toggleSceneCharacter(sceneIdx, charName) {
      if (!G_CURRENT_EP || !G_CURRENT_EP.scenes[sceneIdx]) return;
      const sc = G_CURRENT_EP.scenes[sceneIdx];
      sc.characters = sc.characters || [];
      const pos = sc.characters.indexOf(charName);
      if (pos >= 0) {
        sc.characters.splice(pos, 1);
      } else {
        sc.characters.push(charName);
        if (!sc.speaker) sc.speaker = charName;
        if (!sc.action.includes(`@${charName}`)) {
          sc.action = `@${charName} ${sc.action}`.trim();
        }
        const cObj = (G_ASSETS.characters || []).find(c => c.name === charName);
        if (cObj) {
          const bestImg = (sc.era === 'modern' ? cObj.ref_image_modern : cObj.ref_image_ancient) || cObj.ref_image;
          if (bestImg && !sc.ref_image) {
            sc.ref_image = bestImg;
          }
        }
      }
      renderCurrentEpisodeStudio();
    }

    function updateSceneRoom(sceneIdx, roomId) {
      if (!G_CURRENT_EP || !G_CURRENT_EP.scenes[sceneIdx]) return;
      const sc = G_CURRENT_EP.scenes[sceneIdx];
      sc.room_id = roomId || null;
      const rObj = (G_ASSETS.spatial_rooms || {})[roomId];
      if (rObj && rObj.interior_anchor_image && !sc.ref_image) {
        sc.ref_image = rObj.interior_anchor_image;
      }
      renderCurrentEpisodeStudio();
    }

    function updateSceneField(idx, field, val) {
      if (!G_CURRENT_EP || !G_CURRENT_EP.scenes[idx]) return;
      G_CURRENT_EP.scenes[idx][field] = val;
    }

    async function polishSceneWithAi(idx) {
      const sc = G_CURRENT_EP.scenes[idx];
      const res = await fetch('/api/v1/ai/polish-scene', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene: sc, chinese_visual_hint: null })
      });
      const data = await res.json();
      G_CURRENT_EP.scenes[idx] = data.scene;
      await saveCurrentEpisode();
      showToast(`镜头 #${idx + 1} 已完成 AI 合规润色`);
    }

    async function promptChineseVisualHint(idx) {
      const hint = prompt('请输入本镜头的中文画面描述（系统将结合项目角色与空间资产转写为摄影级英文提示词）：');
      if (!hint) return;
      const sc = G_CURRENT_EP.scenes[idx];
      const res = await fetch('/api/v1/ai/polish-scene', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene: sc, chinese_visual_hint: hint })
      });
      const data = await res.json();
      G_CURRENT_EP.scenes[idx] = data.scene;
      await saveCurrentEpisode();
      showToast(`已根据中文描述更新镜头 #${idx + 1} 画面提示词`);
    }

    function addBlankScene() {
      if (!G_CURRENT_EP) return;
      const nextNum = G_CURRENT_EP.scenes.length + 1;
      const firstChar = (G_ASSETS.characters && G_ASSETS.characters[0]) ? G_ASSETS.characters[0].name : 'Protagonist';
      const firstRoom = Object.keys(G_ASSETS.spatial_rooms || {})[0] || null;
      const firstAcoustic = Object.keys(G_ASSETS.acoustic_spaces || {})[0] || 'interior_room';
      const firstPhase = (G_ASSETS.arc_phases && G_ASSETS.arc_phases[0]) || 'P1_Hook_Tension';
      const firstImg = (G_ASSETS.images && G_ASSETS.images[0]) ? G_ASSETS.images[0].rel_path : null;

      G_CURRENT_EP.scenes.push({
        id: `${G_CURRENT_EP.id.split('_')[0]}_0${nextNum}_shot`,
        era: 'modern',
        action: `Cinematic medium shot, @${firstChar} stands in the scene with expressive eyes and natural lighting, subtle atmospheric depth.`,
        framing: 'medium',
        aspect: '16:9',
        duration: 8,
        model: 'veo-fast',
        room_id: firstRoom,
        arc_phase: firstPhase,
        acoustic_space: firstAcoustic,
        camera_motion: '50mm anamorphic lens, subtle slow push-in',
        ref_image: firstImg,
        characters: [firstChar],
        speaker: firstChar,
        line: ''
      });
      G_SELECTED_SCENE_IDX = G_CURRENT_EP.scenes.length - 1;
      renderCurrentEpisodeStudio();
      renderStudioQuickAssetBar();
      showToast(`已新增镜头 #${G_CURRENT_EP.scenes.length}`);
    }

    function removeScene(idx) {
      if (!confirm('确定要删除这一幕镜头吗？')) return;
      G_CURRENT_EP.scenes.splice(idx, 1);
      renderCurrentEpisodeStudio();
      showToast('已删除镜头');
    }

    async function saveCurrentEpisode() {
      if (!G_CURRENT_EP) return;
      const res = await fetch(`/api/v1/episodes/${G_CURRENT_EP.id}/scenes`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: G_CURRENT_EP.title,
          scenes: G_CURRENT_EP.scenes
        })
      });
      const data = await res.json();
      G_CURRENT_EP.lint_report = data.lint_report;
      renderCurrentEpisodeStudio();
      await loadEpisodes();
      showToast(data.lint_report.passed ? '分镜已保存 · L1-L5 门禁校验通过' : `分镜已保存 · 发现 ${data.lint_report.error_count} 项门禁提示`, data.lint_report.passed ? 'info' : 'warn');
    }

    async function submitEpisodeRender(model, dryRun) {
      if (!G_CURRENT_EP) return;
      await saveCurrentEpisode();
      const member = document.getElementById('memberNameInput').value || '主创导演';
      const res = await fetch('/api/v1/render/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          requested_by: member,
          episode_id: G_CURRENT_EP.id,
          scene_id: null,
          model,
          dry_run: dryRun
        })
      });
      if (!res.ok) {
        showToast(await res.text(), 'error');
        toggleCopilotDrawer(true);
        return;
      }
      await loadJobs();
      await loadSystemStatus();
      showToast(`已提交整集渲染任务 (${model})`);
      switchTab('queue');
    }

    async function submitSingleSceneRender(sceneId, model) {
      if (!G_CURRENT_EP) return;
      await saveCurrentEpisode();
      const member = document.getElementById('memberNameInput').value || '主创导演';
      const res = await fetch('/api/v1/render/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          requested_by: member,
          episode_id: G_CURRENT_EP.id,
          scene_id: sceneId,
          model,
          dry_run: false
        })
      });
      if (!res.ok) {
        showToast(await res.text(), 'error');
        return;
      }
      await loadJobs();
      showToast(`已提交单镜渲染任务：${sceneId}`);
      switchTab('queue');
    }

    function renderTheaterTab() {
      const finals = G_ASSETS.final_videos || [];
      const raws = G_ASSETS.raw_clips || [];
      document.getElementById('finalVideoCount').textContent = finals.length + raws.length;

      const grid = document.getElementById('theaterGrid');
      if (finals.length === 0) {
        grid.innerHTML = `<div class="col-span-full text-xs text-zinc-500 py-8 text-center">当前项目暂无已合成的整集母带</div>`;
      } else {
        grid.innerHTML = finals.map(v => `
          <div class="surface-card p-3.5 flex flex-col justify-between space-y-3">
            <div>
              <div class="flex items-center justify-between gap-2 mb-2">
                <span class="text-xs font-medium text-zinc-100 truncate">${v.name}</span>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-white/[0.06] text-zinc-300 shrink-0">${v.engine_tag}</span>
              </div>
              <video src="${v.url}" preload="metadata" controls playsinline class="w-full rounded-lg bg-black aspect-video"></video>
            </div>
            <div class="flex items-center justify-between text-[11px] font-mono text-zinc-500">
              <span class="truncate">${v.rel_path}</span>
              <span>${(v.size_bytes / 1024 / 1024).toFixed(2)} MB</span>
            </div>
          </div>
        `).join('');
      }

      const rawGrid = document.getElementById('rawClipsGrid');
      if (!rawGrid) return;
      if (raws.length === 0) {
        rawGrid.innerHTML = `<div class="col-span-full text-xs text-zinc-500 py-6 text-center">当前项目暂无单镜头原始素材</div>`;
      } else {
        rawGrid.innerHTML = raws.map(r => `
          <div class="p-3 rounded-xl bg-zinc-900/50 border border-white/[0.06] space-y-2">
            <div class="flex items-center justify-between text-xs font-mono">
              <span class="text-zinc-200 truncate">${r.name}</span>
              <span class="text-[10px] text-zinc-500">${(r.size_bytes / 1024 / 1024).toFixed(1)}M</span>
            </div>
            <video src="${r.url}" preload="metadata" controls playsinline class="w-full rounded-lg bg-black aspect-video"></video>
            <div class="text-[10px] font-mono text-zinc-500 flex justify-between">
              <span>${r.episode_id}</span>
              <span>${r.engine_tag}</span>
            </div>
          </div>
        `).join('');
      }
    }

    function switchAssetSubTab(sub) {
      ['chars', 'props', 'voices', 'images', 'rooms', 'style'].forEach(k => {
        const panel = document.getElementById(`assetSub-${k}`);
        const btn = document.getElementById(`assetSubBtn-${k}`);
        if (panel) panel.classList.toggle('hidden', k !== sub);
        if (btn) btn.classList.toggle('active', k === sub);
      });
    }

    function renderAssetsTab() {
      const imgOptionsHtml = `<option value="">(不绑定参考图)</option>` +
        (G_ASSETS.images || []).map(img => `<option value="${img.rel_path}">${img.name}</option>`).join('');
      ['newCharRefSelect', 'newCharTurnaroundSelect', 'propRefImgSelect', 'roomExtImgSelect', 'roomIntImgSelect'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = imgOptionsHtml;
      });

      const voicePresets = G_ASSETS.voice_presets || [];
      const voiceSelect = document.getElementById('newCharVoice');
      if (voiceSelect) {
        voiceSelect.innerHTML = voicePresets.map(v => `<option value="${v.id}">${v.label} (${v.gender_age})</option>`).join('') +
          `<option value="rigel">Rigel (系统默认男声)</option>`;
      }

      const voiceGrid = document.getElementById('voiceLibraryGrid');
      if (voiceGrid) {
        voiceGrid.innerHTML = voicePresets.map(v => `
          <div class="p-3.5 rounded-xl bg-zinc-900/60 border border-white/[0.07] flex flex-col justify-between space-y-2.5">
            <div class="space-y-1">
              <div class="flex items-center justify-between gap-2">
                <span class="font-mono font-semibold text-zinc-100 text-xs truncate">${v.label}</span>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-white/[0.06] text-zinc-300 shrink-0">${v.gender_age}</span>
              </div>
              <div class="text-zinc-400 text-[11px] leading-relaxed">${v.description}</div>
            </div>
            <div class="space-y-2 pt-1">
              <audio controls preload="none" src="${v.url}" class="w-full h-8"></audio>
              <button onclick="document.getElementById('newCharVoice').value='${v.id}'; switchAssetSubTab('chars'); showToast('已选中音色：${v.label}');" class="w-full py-1.5 btn-ghost text-[11px]">
                选用此音色锚点 →
              </button>
            </div>
          </div>
        `).join('');
      }

      const propBox = document.getElementById('propCards');
      if (propBox) {
        const propsEntries = Object.entries(G_ASSETS.continuity_props || {});
        if (propsEntries.length === 0) {
          propBox.innerHTML = `<div class="col-span-full text-xs text-zinc-500 py-8 text-center">暂无连续性道具/武魂资产，可在左侧新增</div>`;
        } else {
          propBox.innerHTML = propsEntries.map(([pid, p]) => `
            <div class="p-3.5 rounded-xl bg-zinc-900/60 border border-white/[0.07] flex flex-col justify-between space-y-2">
              <div class="space-y-1">
                <div class="flex items-center justify-between">
                  <span class="font-semibold text-zinc-100 text-xs">${p.name} <span class="font-mono text-zinc-500">(${pid})</span></span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-white/[0.06] text-zinc-300">${p.category} · ${p.version_tag || 'v1'}</span>
                </div>
                <div class="text-zinc-400 text-[11px]">${p.description || ''}</div>
                <div class="text-[10px] font-mono text-zinc-500">REF: ${p.ref_image || '未绑定'}</div>
              </div>
              <div class="flex justify-end gap-1.5 pt-2 border-t border-white/[0.05]">
                <button onclick="deleteContinuityProp('${pid}')" class="px-2.5 py-1 btn-ghost text-[11px] text-zinc-500 hover:text-red-400">删除</button>
              </div>
            </div>
          `).join('');
        }
      }

      const styleRow = document.getElementById('stylePresetsRow');
      if (styleRow) {
        const curPreset = (G_ASSETS.project_meta && G_ASSETS.project_meta.style_preset) || 'live_action_arri';
        styleRow.innerHTML = (G_ASSETS.style_presets || []).map(sp => {
          const active = sp.id === curPreset;
          return `
            <button onclick="applyStylePreset('${sp.id}')" class="p-3 rounded-xl border text-left transition flex flex-col justify-between gap-1.5 ${active ? 'bg-zinc-100 text-zinc-950 border-zinc-100' : 'bg-zinc-900/70 border-white/[0.08] text-zinc-200 hover:border-white/25'}">
              <div class="flex items-center justify-between gap-1">
                <span class="font-semibold text-xs">${sp.name}</span>
                ${active ? `<span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-950 text-zinc-100">当前锁定</span>` : ''}
              </div>
              <div class="text-[11px] ${active ? 'text-zinc-700' : 'text-zinc-400'} line-clamp-2">${sp.summary}</div>
            </button>
          `;
        }).join('');
      }

      const charBox = document.getElementById('characterCards');
      const chars = G_ASSETS.characters || [];
      if (chars.length === 0) {
        charBox.innerHTML = `<div class="col-span-full text-xs text-zinc-500 py-8 text-center">当前项目暂无角色，请在上方/左侧新增</div>`;
      } else {
        charBox.innerHTML = chars.map((c, idx) => {
          const imgRel = c.turnaround_ref_image || c.ref_image || c.ref_image_ancient || c.ref_image_modern || '';
          const imgUrl = imgRel ? mediaUrlForProjectPath(imgRel) : '';
          return `
            <div class="p-3.5 rounded-xl bg-zinc-900/60 border border-white/[0.07] flex flex-col justify-between gap-3">
              <div class="flex gap-3">
                ${imgUrl ? `<img src="${imgUrl}" onclick="openImageModal('${imgUrl}', '@${c.name}')" class="w-24 sm:w-28 h-20 object-cover rounded-lg shrink-0 cursor-pointer border border-white/10" />` : `<div class="w-24 sm:w-28 h-20 rounded-lg bg-zinc-950 border border-white/[0.06] flex items-center justify-center text-[10px] font-mono text-zinc-600 shrink-0">NO IMAGE</div>`}
                <div class="text-xs space-y-1 overflow-hidden flex-1">
                  <div class="flex items-center justify-between gap-1">
                    <span class="font-mono font-semibold text-zinc-100 text-sm truncate">@${c.name}</span>
                    <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-white/[0.05] text-zinc-300 shrink-0">${c.tier || 'protagonist'} · ${c.costume_version || 'v1'}</span>
                  </div>
                  <div class="text-[10px] font-mono text-emerald-400 truncate">🎙️ ${c.voice || '温厚沉稳青年男声-v1'}</div>
                  <div class="text-zinc-400 line-clamp-2 text-[11px]">${c.appearance || ''}</div>
                </div>
              </div>
              <div class="flex items-center justify-between pt-2.5 border-t border-white/[0.06] text-[11px]">
                <div class="flex gap-1.5">
                  <button onclick="editCharacter(${idx})" class="px-2.5 py-1.5 btn-ghost">编辑</button>
                  <button onclick="deleteCharacter('${c.name}')" class="px-2.5 py-1.5 btn-ghost text-zinc-500 hover:text-red-400">删除</button>
                </div>
                <button onclick="injectCharacterIntoSelectedScene('${c.name}'); switchTab('studio');" class="px-3 py-1.5 btn-white">
                  注入当前分镜 →
                </button>
              </div>
            </div>
          `;
        }).join('');
      }

      const roomBox = document.getElementById('roomCards');
      const rooms = Object.entries(G_ASSETS.spatial_rooms || {});
      if (rooms.length === 0) {
        roomBox.innerHTML = `<div class="col-span-full text-xs text-zinc-500 py-8 text-center">暂无三维空间拓扑，可在上方/左侧新增</div>`;
      } else {
        roomBox.innerHTML = rooms.map(([k, r]) => `
          <div class="p-3.5 rounded-xl bg-zinc-900/60 border border-white/[0.07] flex flex-col justify-between space-y-2.5">
            <div class="space-y-1">
              <div class="flex items-center justify-between">
                <span class="font-mono font-semibold text-zinc-100 text-sm">#${k}</span>
                <div class="flex gap-1">
                  <button onclick="editRoom('${k}')" class="px-2 py-1 btn-ghost text-[11px]">编辑</button>
                  <button onclick="deleteRoom('${k}')" class="px-2 py-1 btn-ghost text-zinc-500 hover:text-red-400 text-[11px]">删除</button>
                </div>
              </div>
              <div class="text-zinc-300 text-xs">${r.description || ''}</div>
              <div class="text-zinc-500 text-[11px] font-mono">L: ${r.camera_left}</div>
              <div class="text-zinc-500 text-[11px] font-mono">C: ${r.center_foreground}</div>
              <div class="text-zinc-500 text-[11px] font-mono">R: ${r.camera_right}</div>
              <div class="text-[10px] font-mono text-zinc-400 pt-1">
                EXT: ${r.exterior_anchor_image || '-'} | INT: ${r.interior_anchor_image || '-'}
              </div>
            </div>
            <button onclick="injectRoomIntoSelectedScene('${k}'); switchTab('studio');" class="w-full py-2 btn-ghost text-[11px]">
              绑定到当前分镜 →
            </button>
          </div>
        `).join('');
      }

      const gal = document.getElementById('imageGallery');
      const imgs = G_ASSETS.images || [];
      if (imgs.length === 0) {
        gal.innerHTML = `<div class="col-span-full text-xs text-zinc-500 py-8 text-center">当前项目暂无首帧母图，请上传</div>`;
      } else {
        gal.innerHTML = imgs.map(img => `
          <div class="rounded-xl overflow-hidden bg-zinc-900/60 border border-white/[0.07] flex flex-col justify-between">
            <div>
              <img src="${img.url}" onclick="openImageModal('${img.url}', '${img.name}')" class="w-full aspect-video object-cover cursor-pointer" />
              <div class="p-2.5">
                <div class="text-xs font-mono font-medium text-zinc-200 truncate" title="${img.name}">${img.name}</div>
                <div class="text-[10px] font-mono text-zinc-500">${(img.size_bytes / 1024).toFixed(0)} KB</div>
              </div>
            </div>
            <div class="p-2.5 pt-0 flex items-center justify-between gap-1.5 text-[11px]">
              <button onclick="applyImageToSelectedScene('${img.rel_path}')" class="flex-1 py-1.5 px-2 btn-ghost">
                设为当前分镜首帧
              </button>
              <button onclick="deleteAnchorImage('${img.name}')" class="py-1.5 px-2.5 btn-ghost text-zinc-500 hover:text-red-400">✕</button>
            </div>
          </div>
        `).join('');
      }

      const sl = G_ASSETS.style_lock || {};
      document.getElementById('styleCameraBase').value = sl.camera_base || '';
      document.getElementById('styleLightingBase').value = sl.lighting_base || '';
      document.getElementById('styleFilmStock').value = sl.film_stock || '';
      document.getElementById('styleGlobalSuffix').value = sl.global_suffix || '';
      document.getElementById('styleModernSuffix').value = sl.modern_suffix || '';
      document.getElementById('styleNegativePrompt').value = sl.negative_prompt || '';

      const acBox = document.getElementById('acousticCards');
      acBox.innerHTML = Object.entries(G_ASSETS.acoustic_spaces || {}).map(([k, a]) => `
        <div class="p-3 rounded-xl bg-zinc-900/60 border border-white/[0.06] space-y-1">
          <div class="flex items-center justify-between">
            <span class="font-mono font-semibold text-zinc-200">${k}</span>
            <span class="font-mono text-[10px] px-2 py-0.5 rounded bg-zinc-950 text-zinc-400 border border-white/[0.06]">${a.ffmpeg_bg_filter}</span>
          </div>
          <div class="text-zinc-400">${a.description}</div>
          <div class="text-zinc-500 text-[11px] font-mono">Cue: ${a.h3_audio_cue}</div>
        </div>
      `).join('');
    }

    function editCharacter(idx) {
      const c = (G_ASSETS.characters || [])[idx];
      if (!c) return;
      document.getElementById('newCharName').value = c.name || '';
      document.getElementById('newCharTier').value = c.tier || 'protagonist';
      document.getElementById('newCharVoice').value = c.voice || '温厚沉稳青年男声-v1';
      document.getElementById('newCharCostume').value = c.costume_version || 'v1_常规常服';
      document.getElementById('newCharApp').value = c.appearance || '';
      document.getElementById('newCharAppModern').value = c.appearance_modern || '';
      document.getElementById('newCharAppAncient').value = c.appearance_ancient || '';
      document.getElementById('newCharRefSelect').value = c.ref_image || c.ref_image_ancient || c.ref_image_modern || '';
      if (document.getElementById('newCharTurnaroundSelect')) {
        document.getElementById('newCharTurnaroundSelect').value = c.turnaround_ref_image || '';
      }
      showToast(`已载入角色 @${c.name} 到表单`);
      document.getElementById('newCharName').scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function clearCharacterForm() {
      document.getElementById('newCharName').value = '';
      document.getElementById('newCharTier').value = 'protagonist';
      document.getElementById('newCharCostume').value = 'v1_常规常服';
      document.getElementById('newCharApp').value = '';
      document.getElementById('newCharAppModern').value = '';
      document.getElementById('newCharAppAncient').value = '';
      document.getElementById('newCharRefSelect').value = '';
      if (document.getElementById('newCharTurnaroundSelect')) {
        document.getElementById('newCharTurnaroundSelect').value = '';
      }
    }

    async function createNewCharacter() {
      const name = document.getElementById('newCharName').value.trim();
      const tier = document.getElementById('newCharTier').value || 'protagonist';
      const voice = document.getElementById('newCharVoice').value.trim() || '温厚沉稳青年男声-v1';
      const costume_version = document.getElementById('newCharCostume').value.trim() || 'v1_base';
      const appearance = document.getElementById('newCharApp').value.trim();
      const appearance_modern = document.getElementById('newCharAppModern').value.trim() || null;
      const appearance_ancient = document.getElementById('newCharAppAncient').value.trim() || null;
      const ref_image = document.getElementById('newCharRefSelect').value || null;
      const turnaround_ref_image = document.getElementById('newCharTurnaroundSelect') ? (document.getElementById('newCharTurnaroundSelect').value || null) : null;
      if (!name || !appearance) {
        showToast('请填写角色唯一 ID 与外貌描述', 'warn');
        return;
      }
      const res = await fetch('/api/v1/assets/characters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          tier,
          voice,
          costume_version,
          appearance,
          appearance_modern,
          appearance_ancient,
          ref_image,
          ref_image_modern: ref_image,
          ref_image_ancient: ref_image,
          turnaround_ref_image
        })
      });
      if (res.ok) {
        await loadAssets();
        await loadProjects();
        showToast(`角色资产 @${name} 已保存`);
      }
    }

    async function saveContinuityProp() {
      const prop_id = document.getElementById('propIdInput').value.trim();
      const name = document.getElementById('propNameInput').value.trim();
      const category = document.getElementById('propCategoryInput').value;
      const version_tag = document.getElementById('propVersionInput').value.trim() || 'v1_常态';
      const description = document.getElementById('propDescInput').value.trim();
      const ref_image = document.getElementById('propRefImgSelect').value || null;
      if (!prop_id || !name || !description) {
        showToast('请填写连续性道具/武魂的 ID、名称与造型描述', 'warn');
        return;
      }
      const res = await fetch('/api/v1/assets/props', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prop_id, name, category, version_tag, description, ref_image })
      });
      if (res.ok) {
        await loadAssets();
        showToast(`连续性道具/武魂 ${name} 已保存`);
      }
    }

    async function deleteContinuityProp(propId) {
      if (!confirm(`确定删除连续性道具/武魂 ${propId} 吗？`)) return;
      await fetch(`/api/v1/assets/props/${encodeURIComponent(propId)}`, { method: 'DELETE' });
      await loadAssets();
      showToast(`已删除道具 ${propId}`);
    }

    async function applyStylePreset(presetId) {
      const res = await fetch('/api/v1/assets/style-preset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset_id: presetId, no_subtitles_lock: true })
      });
      if (res.ok) {
        await loadAssets();
        showToast(`已切换项目全局画风锁：${presetId}`);
      }
    }

    async function compileSeedanceModal() {
      if (!G_CURRENT_EP) return;
      await saveCurrentEpisode();
      const res = await fetch(`/api/v1/episodes/${G_CURRENT_EP.id}/compile-seedance`);
      const data = await res.json();
      const text = JSON.stringify(data, null, 2);
      navigator.clipboard?.writeText(text);
      showToast('已编译 Seedance 2.0 多模态生产节点清单并复制到剪贴板！');
    }

    async function exportJianyingDraft() {
      if (!G_CURRENT_EP) return;
      await saveCurrentEpisode();
      const res = await fetch(`/api/v1/episodes/${G_CURRENT_EP.id}/export-jianying`, { method: 'POST' });
      const data = await res.json();
      if (data.ok) {
        showToast(`已导出剪映 5 轨非破坏性草稿与 SRT 字幕：${data.draft_dir}`);
      }
    }

    async function deleteCharacter(name) {
      if (!confirm(`确定要从当前项目删除角色 @${name} 吗？`)) return;
      await fetch(`/api/v1/assets/characters/${encodeURIComponent(name)}`, { method: 'DELETE' });
      await loadAssets();
      await loadProjects();
      showToast(`已删除角色 @${name}`);
    }

    function editRoom(roomId) {
      const r = (G_ASSETS.spatial_rooms || {})[roomId];
      if (!r) return;
      document.getElementById('roomIdInput').value = roomId;
      document.getElementById('roomDescInput').value = r.description || '';
      document.getElementById('roomLeftInput').value = r.camera_left || '';
      document.getElementById('roomCenterInput').value = r.center_foreground || '';
      document.getElementById('roomRightInput').value = r.camera_right || '';
      document.getElementById('roomExtImgSelect').value = r.exterior_anchor_image || '';
      document.getElementById('roomIntImgSelect').value = r.interior_anchor_image || '';
      showToast(`已载入空间 #${roomId} 到编辑器`);
      document.getElementById('roomIdInput').scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    async function saveSpatialRoom() {
      const room_id = document.getElementById('roomIdInput').value.trim();
      const description = document.getElementById('roomDescInput').value.trim();
      const camera_left = document.getElementById('roomLeftInput').value.trim();
      const center_foreground = document.getElementById('roomCenterInput').value.trim();
      const camera_right = document.getElementById('roomRightInput').value.trim();
      const exterior_anchor_image = document.getElementById('roomExtImgSelect').value || null;
      const interior_anchor_image = document.getElementById('roomIntImgSelect').value || null;
      if (!room_id || !description) {
        showToast('请填写空间 ID 与空间说明', 'warn');
        return;
      }
      const res = await fetch('/api/v1/assets/rooms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room_id,
          description,
          camera_left,
          center_foreground,
          camera_right,
          exterior_anchor_image,
          interior_anchor_image
        })
      });
      if (res.ok) {
        await loadAssets();
        await loadProjects();
        showToast(`三维空间拓扑 #${room_id} 已保存`);
      }
    }

    async function deleteRoom(roomId) {
      if (!confirm(`确定删除三维空间拓扑 ${roomId} 吗？`)) return;
      await fetch(`/api/v1/assets/rooms/${encodeURIComponent(roomId)}`, { method: 'DELETE' });
      await loadAssets();
      await loadProjects();
      showToast(`已删除空间 #${roomId}`);
    }

    async function saveStyleLock() {
      const payload = {
        camera_base: document.getElementById('styleCameraBase').value.trim(),
        lighting_base: document.getElementById('styleLightingBase').value.trim(),
        film_stock: document.getElementById('styleFilmStock').value.trim(),
        global_suffix: document.getElementById('styleGlobalSuffix').value.trim(),
        modern_suffix: document.getElementById('styleModernSuffix').value.trim(),
        negative_prompt: document.getElementById('styleNegativePrompt').value.trim()
      };
      const res = await fetch('/api/v1/assets/style-lock', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        await loadAssets();
        showToast('全局摄影机与胶片风格锁已更新');
      }
    }

    async function saveAcousticSpace() {
      const space_id = document.getElementById('acSpaceId').value.trim();
      const description = document.getElementById('acDesc').value.trim();
      const ffmpeg_bg_filter = document.getElementById('acFilter').value.trim() || 'volume=0.25';
      const h3_audio_cue = document.getElementById('acCue').value.trim();
      if (!space_id || !description) {
        showToast('请填写声学空间 ID 与说明', 'warn');
        return;
      }
      const res = await fetch('/api/v1/assets/acoustics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ space_id, description, ffmpeg_bg_filter, h3_audio_cue })
      });
      if (res.ok) {
        await loadAssets();
        showToast(`声学空间 ${space_id} 已保存`);
      }
    }

    async function uploadAnchorImage() {
      const inp = document.getElementById('uploadImgFile');
      if (!inp.files || !inp.files[0]) {
        showToast('请先选择一张图片文件', 'warn');
        return;
      }
      const fd = new FormData();
      fd.append('file', inp.files[0]);
      const res = await fetch('/api/v1/assets/upload-image', { method: 'POST', body: fd });
      if (res.ok) {
        inp.value = '';
        document.getElementById('uploadFileNameLabel').textContent = 'JPG / PNG / WebP';
        await loadAssets();
        await loadProjects();
        showToast('首帧参考母图已上传');
      }
    }

    async function deleteAnchorImage(name) {
      if (!confirm(`确定要删除母图 ${name} 吗？`)) return;
      await fetch(`/api/v1/assets/images/${encodeURIComponent(name)}`, { method: 'DELETE' });
      await loadAssets();
      await loadProjects();
      showToast(`已删除母图 ${name}`);
    }

    async function loadJobs() {
      const res = await fetch('/api/v1/render/jobs');
      const jobs = await res.json();
      const box = document.getElementById('jobsList');
      if (jobs.length === 0) {
        box.innerHTML = `<div class="text-xs text-zinc-500 py-8 text-center">暂无渲染任务</div>`;
        return;
      }
      box.innerHTML = jobs.map(j => {
        const isPending = j.status === 'pending_approval';
        return `
          <div class="p-3.5 rounded-xl bg-zinc-900/60 border ${isPending ? 'border-amber-500/50' : 'border-white/[0.06]'} space-y-2 text-xs">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="flex items-center gap-2">
                <span class="font-mono text-zinc-500">#${j.id}</span>
                <span class="font-semibold text-zinc-100">${j.episode_id} ${j.scene_id ? '· ' + j.scene_id : '(FULL)'}</span>
                <span class="px-2 py-0.5 rounded bg-white/[0.06] text-zinc-300 font-mono text-[11px]">${j.model}</span>
              </div>
              <div class="flex items-center gap-2 font-mono text-[11px]">
                <span class="text-zinc-400">${j.estimated_credits} 点</span>
                <span class="px-2 py-0.5 rounded uppercase ${j.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' : j.status === 'pending_approval' ? 'bg-amber-500/10 text-amber-300' : 'bg-white/[0.06] text-zinc-300'}">${j.status}</span>
              </div>
            </div>
            <div class="text-zinc-400">${j.progress_message}</div>
            ${isPending ? `
              <div class="flex items-center gap-2 pt-1">
                <button onclick="approveJob('${j.id}', true)" class="px-3 py-1.5 btn-white text-xs">批准执行</button>
                <button onclick="approveJob('${j.id}', false)" class="px-3 py-1.5 btn-ghost text-xs">驳回</button>
              </div>
            ` : ''}
            ${j.log_tail ? `<pre class="p-2.5 rounded-lg bg-black text-[10px] font-mono text-zinc-500 overflow-x-auto max-h-28">${j.log_tail}</pre>` : ''}
          </div>
        `;
      }).join('');
    }

    async function approveJob(jobId, approve) {
      const pin = document.getElementById('inpAdminPin').value || prompt('请输入管理员审批口令:');
      const res = await fetch(`/api/v1/render/jobs/${jobId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ admin_pin: pin, approve })
      });
      if (!res.ok) {
        showToast(await res.text(), 'error');
        return;
      }
      await loadJobs();
      await loadSystemStatus();
      showToast(approve ? '已批准任务执行' : '已驳回任务');
    }

    async function savePolicy() {
      const require_approval_for_quality = document.getElementById('chkQualityApproval').checked;
      const daily_credit_limit = parseInt(document.getElementById('inpDailyLimit').value || '300', 10);
      await fetch('/api/v1/system/policy', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ require_approval_for_quality, daily_credit_limit })
      });
      showToast('安全与配额策略已保存');
    }

    function openNewEpisodeModal() {
      const nextEpNum = G_EPISODES.length + 1;
      document.getElementById('modalEpTitle').value = `第${nextEpNum}集：新篇章`;
      document.getElementById('modalEpDir').value = `ep0${nextEpNum}_story`;
      document.getElementById('modalStoryIdea').value = '';
      document.getElementById('newEpModal').classList.remove('hidden');
      document.getElementById('newEpModal').classList.add('flex');
    }
    function closeNewEpisodeModal() {
      document.getElementById('newEpModal').classList.add('hidden');
      document.getElementById('newEpModal').classList.remove('flex');
    }

    async function createEpisodeWithAi() {
      const title = document.getElementById('modalEpTitle').value.trim();
      const dir_name = document.getElementById('modalEpDir').value.trim();
      const story_idea = document.getElementById('modalStoryIdea').value.trim();
      if (!title || !story_idea) {
        showToast('请填写剧集标题与剧情梗概', 'warn');
        return;
      }
      const btn = document.getElementById('btnCreateEpAi');
      btn.textContent = '编译中...';
      const res = await fetch('/api/v1/episodes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dir_name, title, story_idea, preferred_model: 'veo-fast' })
      });
      btn.textContent = '生成分镜工程';
      if (res.ok) {
        const data = await res.json();
        closeNewEpisodeModal();
        await loadEpisodes();
        await loadProjects();
        await selectEpisode(data.id);
        showToast(`已生成剧集《${title}》`);
        const member_name = document.getElementById('memberNameInput').value || '主创导演';
        fetch('/api/v1/agent/demand', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            member_name,
            episode_id: data.id,
            scene_id: null,
            demand_text: `在项目 [${G_ACTIVE_PROJECT_ID}] 下新建了剧集《${title}》，故事想法是：${story_idea}。请结合本项目的角色与空间资产，通过 MCP 进一步精修本集的文学剧本 script.md 与分镜 movie.toml。`
          })
        }).then(() => loadAgentDemands()).catch(() => {});
      } else {
        showToast(await res.text(), 'error');
      }
    }

    function openVideoModal(url, title) {
      document.getElementById('videoModalTitle').textContent = title;
      const player = document.getElementById('videoModalPlayer');
      const imgViewer = document.getElementById('imageModalViewer');
      imgViewer.classList.add('hidden');
      player.classList.remove('hidden');
      player.src = url;
      document.getElementById('videoModal').classList.remove('hidden');
      document.getElementById('videoModal').classList.add('flex');
      player.play();
    }

    function openImageModal(url, title) {
      document.getElementById('videoModalTitle').textContent = title;
      const player = document.getElementById('videoModalPlayer');
      const imgViewer = document.getElementById('imageModalViewer');
      player.pause();
      player.src = '';
      player.classList.add('hidden');
      imgViewer.src = url;
      imgViewer.classList.remove('hidden');
      document.getElementById('videoModal').classList.remove('hidden');
      document.getElementById('videoModal').classList.add('flex');
    }

    function closeVideoModal() {
      const player = document.getElementById('videoModalPlayer');
      player.pause();
      player.src = '';
      document.getElementById('videoModal').classList.add('hidden');
      document.getElementById('videoModal').classList.remove('flex');
    }

    function switchTab(tab) {
      ['studio', 'assets', 'theater', 'queue'].forEach(t => {
        document.getElementById(`tab-${t}`).classList.toggle('hidden', t !== tab);
        const dBtn = document.getElementById(`tabBtn-${t}`);
        if (dBtn) dBtn.classList.toggle('active', t === tab);
        const mBtn = document.getElementById(`mTabBtn-${t}`);
        if (mBtn) {
          mBtn.className = `py-2 flex flex-col items-center justify-center gap-1 ${t === tab ? 'text-zinc-100 font-semibold' : 'text-zinc-500'}`;
        }
      });
    }

    function connectSse() {
      const es = new EventSource('/api/v1/events/stream');
      es.onmessage = async (e) => {
        try {
          const evt = JSON.parse(e.data);
          document.getElementById('liveEventBanner').textContent = `[${evt.timestamp}] ${evt.message}`;
          await loadJobs();
          await loadSystemStatus();
          await loadAgentDemands();
          if (evt.event_type === 'project_switched' || evt.event_type === 'asset_updated') {
            await loadProjects();
            await loadAssets();
          }
          if (evt.event_type === 'mcp_updated' || evt.event_type === 'episode_saved' || evt.event_type === 'script_saved' || evt.event_type === 'project_switched') {
            await loadEpisodes();
            if (G_CURRENT_EP) {
              await selectEpisode(G_CURRENT_EP.id);
            }
          }
        } catch (_) {}
      };
    }

    async function saveCurrentScript() {
      if (!G_CURRENT_EP) return;
      const script_markdown = document.getElementById('scriptMarkdownEditor').value;
      const res = await fetch(`/api/v1/episodes/${G_CURRENT_EP.id}/script`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ script_markdown })
      });
      if (res.ok) {
        G_CURRENT_EP.script_markdown = script_markdown;
        showToast('文学剧本 script.md 已保存');
      }
    }

    async function sendDemandToAgent(sceneId) {
      if (!G_CURRENT_EP) return;
      const inp = document.getElementById('agentDemandInput');
      const demand_text = inp.value.trim();
      if (!demand_text) {
        showToast('请先输入改稿需求', 'warn');
        return;
      }
      const member_name = document.getElementById('memberNameInput').value || '主创导演';
      const btn = document.getElementById('btnSendAgentDemand');
      btn.textContent = '正在发送...';
      const res = await fetch('/api/v1/agent/demand', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          member_name,
          episode_id: G_CURRENT_EP.id,
          scene_id: sceneId,
          demand_text: `[项目: ${G_ACTIVE_PROJECT_ID}] ${demand_text}`
        })
      });
      btn.textContent = '发送改稿指令给 Antigravity';
      if (res.ok) {
        inp.value = '';
        await loadAgentDemands();
        showToast('改稿指令已发送至 Antigravity');
      } else {
        showToast(await res.text(), 'error');
      }
    }

    async function loadAgentDemands() {
      try {
        const res = await fetch('/api/v1/agent/demand');
        const list = await res.json();
        const box = document.getElementById('agentDemandsHistory');
        if (!box) return;
        box.innerHTML = list.slice(0, 6).map(d => `
          <div class="p-2.5 rounded-lg bg-zinc-900/80 border border-white/[0.06] space-y-1">
            <div class="flex items-center justify-between text-[10px] font-mono">
              <span class="text-zinc-300">${d.member_name} → ${d.episode_id}</span>
              <span class="${d.status === 'completed_via_mcp' ? 'text-emerald-400' : 'text-zinc-500'}">${d.status === 'completed_via_mcp' ? 'DONE' : 'PENDING'}</span>
            </div>
            <div class="text-zinc-400">${d.demand_text}</div>
            ${d.agent_reply ? `<div class="text-zinc-300 text-[10px] pt-0.5">${d.agent_reply}</div>` : ''}
          </div>
        `).join('');
      } catch (_) {}
    }

    initApp();
  </script>
</body>
</html>
"##;
