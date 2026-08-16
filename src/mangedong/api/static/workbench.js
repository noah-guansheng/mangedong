const state = {
  token: localStorage.getItem("md_token") || "",
  teamId: Number(localStorage.getItem("md_team_id") || 0),
  projectId: Number(localStorage.getItem("md_project_id") || 0),
  statusHistory: [],
  activeRoute: "",
};

const ROUTES = [
  { id: "dashboard", label: "Dashboard", group: "生产" },
  { id: "pipeline", label: "链路向导", group: "生产" },
  { id: "production", label: "生产工作台", group: "生产" },
  { id: "import", label: "漫画导入", group: "生产" },
  { id: "color", label: "上色生产", group: "生产" },
  { id: "timeline", label: "Shot / Timeline", group: "生产" },
  { id: "audio", label: "音频字幕", group: "生产" },
  { id: "review", label: "审核导出", group: "交付" },
  { id: "delivery", label: "质量交付", group: "交付" },
  { id: "compliance", label: "合规下载", group: "交付" },
  { id: "resources", label: "资源浏览", group: "交付" },
  { id: "ai", label: "AI / ComfyUI", group: "系统" },
  { id: "reports", label: "报表", group: "系统" },
  { id: "ops", label: "运维/Worker", group: "系统" },
  { id: "p2", label: "P2 管理", group: "系统" },
  { id: "notifications", label: "通知", group: "系统" },
  { id: "settings", label: "设置", group: "系统" },
  { id: "help", label: "帮助", group: "系统" },
  { id: "auth", label: "登录", group: "系统" },
];

const view = document.getElementById("view");
const statusBox = document.getElementById("status");
const statusHistory = document.getElementById("status-history");
const appRoot = document.getElementById("app");
const palette = document.getElementById("command-palette");
const paletteInput = document.getElementById("palette-input");
const paletteResults = document.getElementById("palette-results");

document.querySelectorAll("[data-route]").forEach((button) => {
  button.addEventListener("click", () => renderRoute(button.dataset.route));
});
document.getElementById("open-palette")?.addEventListener("click", openPalette);
document.getElementById("palette-form")?.addEventListener("submit", (event) => {
  event.preventDefault();
  const first = paletteResults.querySelector("button");
  if (first) renderRoute(first.dataset.route);
});
paletteInput?.addEventListener("input", () => renderPaletteResults(paletteInput.value));

function setStatus(message) {
  statusBox.textContent = message;
  state.statusHistory.unshift({ message, at: new Date().toLocaleTimeString() });
  state.statusHistory = state.statusHistory.slice(0, 5);
  statusHistory.innerHTML = `<ol>${state.statusHistory.map((entry) => `<li>${entry.at} - ${entry.message}</li>`).join("")}</ol>`;
}

function setShell(route) {
  state.activeRoute = route;
  appRoot.dataset.mode = route === "auth" ? "auth" : "workbench";
  document.querySelectorAll(".rail [data-route]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.route === route);
  });
  document.getElementById("team-chip").textContent = state.teamId ? `团队 #${state.teamId}` : "团队未选择";
  document.getElementById("project-chip").textContent = state.projectId ? `项目 #${state.projectId}` : "项目未选择";
  document.getElementById("setup-banner").hidden = Boolean(localStorage.getItem("md_models_ready")) || route === "ai" || route === "auth";
  const current = ROUTES.find((item) => item.id === route);
  document.title = current ? `${current.label} · mangedong` : "mangedong 生产工作台";
}

function page(kicker, title, lede, body, actions = "") {
  return `
    <header class="page-head">
      <div>
        <p class="kicker">${kicker}</p>
        <h1>${title}</h1>
      </div>
      <div class="page-actions">${actions}</div>
      <p class="lede">${lede}</p>
    </header>
    ${body}
  `;
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status}: ${detail}`);
  }
  return response.json();
}

function renderRoute(route) {
  if (palette?.open) palette.close();
  const routes = {
    auth: renderAuth,
    dashboard: renderDashboard,
    pipeline: renderPipeline,
    production: renderProduction,
    import: renderImport,
    color: renderColor,
    timeline: renderTimeline,
    audio: renderAudio,
    resources: renderResources,
    ai: renderAI,
    review: renderReview,
    delivery: renderDelivery,
    reports: renderReports,
    compliance: renderCompliance,
    p2: renderP2,
    ops: renderOps,
    notifications: renderNotifications,
    help: renderHelp,
    settings: renderSettings,
  };
  const result = (routes[route] || renderDashboard)();
  if (result && typeof result.catch === "function") {
    result.catch((error) => {
      setStatus(error.message);
      if (String(error.message).startsWith("401")) renderAuth();
    });
  }
  return result;
}

document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    openPalette();
    return;
  }
  if (event.key === "Escape") palette.close?.();
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement) return;
  const shortcuts = {
    d: "dashboard",
    p: "pipeline",
    i: "import",
    c: "color",
    t: "timeline",
    a: "audio",
    r: "reports",
    o: "ops",
    h: "help",
    m: "ai",
  };
  if (shortcuts[event.key]) renderRoute(shortcuts[event.key]);
});

function openPalette() {
  renderPaletteResults("");
  palette.showModal();
  paletteInput.value = "";
  paletteInput.focus();
}

function renderPaletteResults(query) {
  const needle = query.trim().toLowerCase();
  const matches = ROUTES.filter((route) => !needle || `${route.label} ${route.id} ${route.group}`.toLowerCase().includes(needle));
  paletteResults.innerHTML = matches
    .map(
      (route, index) => `
        <li>
          <button type="button" data-route="${route.id}" class="${index === 0 ? "is-active" : ""}">
            <span>${route.label}</span>
            <span class="muted">${route.group}</span>
          </button>
        </li>
      `,
    )
    .join("");
  paletteResults.querySelectorAll("[data-route]").forEach((button) => {
    button.addEventListener("click", () => renderRoute(button.dataset.route));
  });
}

function renderAuth() {
  setShell("auth");
  view.innerHTML = `
    <section class="auth-gate">
      <div class="auth-copy">
        <div>
          <p class="kicker">Studio workbench</p>
          <h1>把漫画做成能交货的番剧。</h1>
          <p>登录后先配模型，再进生产：导入、上色、镜头、配音、审片、导出都在同一张工作台上。</p>
        </div>
        <p class="muted">团队 / 工作室 Web SaaS · 本地对象存储 · Worker 已接通</p>
      </div>
      <div class="auth-panel">
        <p class="kicker">Account</p>
        <h2>登录 / 注册</h2>
        <form id="auth-form" class="surface">
          <label>Email <input name="email" type="email" value="owner@example.com" /></label>
          <label>Password <input name="password" type="password" value="password123" /></label>
          <label>Display name <input name="displayName" value="Owner" /></label>
          <button class="primary" type="submit">注册并登录</button>
        </form>
      </div>
    </section>
  `;
  document.getElementById("auth-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = {
      email: form.get("email"),
      password: form.get("password"),
      display_name: form.get("displayName"),
    };
    try {
      await api("/auth/register", { method: "POST", body: JSON.stringify(payload) });
    } catch (_) {
      // Existing users can continue to login.
    }
    const login = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: payload.email, password: payload.password }),
    });
    state.token = login.access_token;
    localStorage.setItem("md_token", state.token);
    setStatus("登录成功");
    await renderDashboard();
  });
}

async function renderDashboard() {
  setShell("dashboard");
  view.innerHTML = page(
    "Overview",
    "Dashboard",
    "当前工作室的项目清单。选中一个项目后，左侧生产模块都围绕它工作。",
    `<div id="dashboard-cards" class="stack"></div>`,
    `<button class="primary" id="create-project">创建默认项目</button>`,
  );
  const teams = await api("/teams");
  if (teams.length === 0) {
    const team = await api("/teams", { method: "POST", body: JSON.stringify({ name: "Default Studio" }) });
    state.teamId = team.id;
  } else {
    state.teamId = teams[0].id;
  }
  localStorage.setItem("md_team_id", state.teamId);
  const projects = await api(`/projects?team_id=${state.teamId}`);
  const rows = projects
    .map(
      (project) => `
        <tr>
          <td>${project.name}</td>
          <td>${project.status}</td>
          <td>#${project.id}</td>
          <td><button class="ghost" data-project-id="${project.id}">设为当前项目</button></td>
        </tr>
      `,
    )
    .join("");
  document.getElementById("dashboard-cards").innerHTML = `
    <section class="surface">
      <div class="metric-row">
        <div class="metric"><b>${state.teamId}</b><span>团队</span></div>
        <div class="metric"><b>${projects.length}</b><span>项目数</span></div>
        <div class="metric"><b>${state.projectId || "—"}</b><span>当前项目</span></div>
      </div>
    </section>
    <section class="surface">
      <h3>项目</h3>
      ${
        rows
          ? `<table class="data-table"><thead><tr><th>名称</th><th>状态</th><th>ID</th><th></th></tr></thead><tbody>${rows}</tbody></table>`
          : `<div class="empty">还没有项目。先创建一个默认剧集，再去「AI / ComfyUI」填 Key 和地址。</div>`
      }
    </section>
  `;
  document.getElementById("create-project").addEventListener("click", createDefaultProject);
  document.querySelectorAll("[data-project-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.projectId = Number(button.dataset.projectId);
      localStorage.setItem("md_project_id", state.projectId);
      setShell("dashboard");
      setStatus(`当前项目：${state.projectId}`);
    });
  });
  setStatus("Dashboard 已加载");
}

async function createDefaultProject() {
  const project = await api("/projects", {
    method: "POST",
    body: JSON.stringify({
      team_id: state.teamId,
      name: `Episode ${Date.now()}`,
      brief: {
        customer_name: "Demo Client",
        ip_name: "Demo IP",
        chapter_scope: "Chapter 1",
        estimated_runtime_minutes: 3,
        target_languages: ["zh", "ja", "en"],
        aspect_ratio: "16:9",
        resolution: "1920x1080",
        fps: 24,
        authorization_status: "licensed",
      },
    }),
  });
  state.projectId = project.id;
  localStorage.setItem("md_project_id", state.projectId);
  setStatus("项目已创建");
  await renderProduction();
}

async function ensureProject() {
  if (!state.projectId) await createDefaultProject();
}

async function renderProduction() {
  setShell("production");
  await ensureProject();
  const [assets, chapters, workItems, gates, jobs] = await Promise.all([
    api(`/projects/${state.projectId}/assets`),
    api(`/projects/${state.projectId}/chapters`),
    api(`/projects/${state.projectId}/work-items`),
    api(`/projects/${state.projectId}/production-gates`),
    api(`/projects/${state.projectId}/ai-jobs`),
  ]);
  view.innerHTML = page(
    "Floor",
    "生产工作台",
    "这一页是当前剧集的现场计数，不承担具体操作。导入、上色、镜头从左侧进入。",
    `
      <section class="surface">
        <div class="metric-row">
          <div class="metric"><b>${assets.length}</b><span>素材</span></div>
          <div class="metric"><b>${chapters.length}</b><span>章节</span></div>
          <div class="metric"><b>${workItems.length}</b><span>Work Items</span></div>
          <div class="metric"><b>${gates.length}</b><span>Gates</span></div>
          <div class="metric"><b>${jobs.length}</b><span>AI Jobs</span></div>
        </div>
      </section>
    `,
  );
  setStatus("生产工作台已加载");
}

async function renderPipeline() {
  setShell("pipeline");
  await ensureProject();
  view.innerHTML = page(
    "Sequence",
    "端到端链路向导",
    "按交货顺序走完一条剧集。先生成默认任务，再逐项落到导入、上色、镜头和音频。",
    `
      <ol class="steps">
        ${pipelineStep("1", "导入", "上传漫画或 PDF，生成章节、页面、分格")}
        ${pipelineStep("2", "上色", "执行参考上色、批量上色、局部修正")}
        ${pipelineStep("3", "Shot", "创建 Shot List 和 Animatic Preview")}
        ${pipelineStep("4", "音频", "创建台词、配音、字幕、BGM、混音")}
        ${pipelineStep("5", "审核", "创建审片包、返修、验收和 QC")}
        ${pipelineStep("6", "导出", "执行 preflight、freeze 和高级格式导出")}
      </ol>
      <section class="surface">
        <h3>快速生产任务</h3>
        <button class="primary" id="create-pipeline-work-items">创建默认生产任务</button>
        <div id="pipeline-result" class="muted"></div>
      </section>
    `,
  );
  document.getElementById("create-pipeline-work-items").addEventListener("click", async () => {
    const stages = ["import", "color", "shot", "audio", "review", "export"];
    await Promise.all(
      stages.map((stage) =>
        api(`/projects/${state.projectId}/work-items`, {
          method: "POST",
          body: JSON.stringify({ title: `${stage} task`, stage, priority: "normal" }),
        }),
      ),
    );
    document.getElementById("pipeline-result").textContent = "默认生产任务已创建";
    setStatus("链路任务已创建");
  });
}

function pipelineStep(index, title, description) {
  return `
    <li class="step">
      <span class="step-index">${index}</span>
      <div>
        <h3>${title}</h3>
        <p class="muted">${description}</p>
      </div>
    </li>
  `;
}

async function renderImport() {
  setShell("import");
  await ensureProject();
  view.innerHTML = page(
    "Ingest",
    "漫画导入",
    "左栏吃原作，右栏看这次导入写进了多少页。PDF 目前按占位页生成，漫画包走真实拆页。",
    `
      <div class="split">
        <form id="manga-import-form" class="surface" data-testid="manga-import-form">
          <h3>漫画 / CBZ / ZIP</h3>
          <label>章节名称 <input name="chapterTitle" value="Chapter 1" /></label>
          <label>漫画图片/CBZ/ZIP <input name="file" type="file" /></label>
          <button class="primary" type="submit">导入漫画</button>
        </form>
        <form id="pdf-import-form" class="surface" data-testid="pdf-import-form">
          <h3>PDF 章节</h3>
          <label>PDF 章节名称 <input name="chapterTitle" value="PDF Chapter" /></label>
          <label>页数 <input name="pageCount" type="number" min="1" value="1" /></label>
          <label>PDF 文件 <input name="file" type="file" /></label>
          <button class="ghost" type="submit">导入 PDF</button>
        </form>
      </div>
      <div id="import-result" class="surface"></div>
    `,
  );
  document.getElementById("manga-import-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    form.set("chapter_title", form.get("chapterTitle"));
    const result = await api(`/projects/${state.projectId}/imports/manga`, { method: "POST", body: form });
    document.getElementById("import-result").textContent = `导入成功：${result.data.page_count} 页`;
    setStatus("漫画导入完成");
  });
  document.getElementById("pdf-import-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    form.set("chapter_title", form.get("chapterTitle"));
    form.set("page_count", form.get("pageCount"));
    const result = await api(`/projects/${state.projectId}/imports/pdf`, { method: "POST", body: form });
    document.getElementById("import-result").textContent = `PDF 导入成功：${result.data.page_count} 页`;
    setStatus("PDF 导入完成");
  });
}

async function renderColor() {
  setShell("color");
  await ensureProject();
  view.innerHTML = page(
    "Paint",
    "上色生产",
    "单格出 PNG，或按项目范围批量跑。输出写进本地对象存储，不经过外部模型也能交货。",
    `
      <div class="split">
        <form id="colorize-form" class="surface" data-testid="colorize-form">
          <h3>单格上色</h3>
          <label>Panel ID <input name="panelId" type="number" min="1" /></label>
          <label>Palette
            <select name="palette">
              <option value="cel">cel</option>
              <option value="sunset">sunset</option>
              <option value="pastel">pastel</option>
            </select>
          </label>
          <button class="primary" type="submit">生成上色 PNG</button>
        </form>
        <form id="batch-color-form" class="surface" data-testid="batch-color-form">
          <h3>批量上色</h3>
          <label>范围 <input name="scope" value="project" /></label>
          <button class="ghost" type="submit">批量上色</button>
        </form>
      </div>
      <div id="color-result" class="surface"></div>
    `,
  );
  document.getElementById("colorize-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const panelId = form.get("panelId");
    const result = await api(`/panels/${panelId}/colorize`, {
      method: "POST",
      body: JSON.stringify({ data: { palette: form.get("palette") } }),
    });
    document.getElementById("color-result").textContent = `上色输出：${result.data.output_asset_uri}`;
  });
  document.getElementById("batch-color-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/projects/${state.projectId}/batch-colorize`, {
      method: "POST",
      body: JSON.stringify({ data: { scope: form.get("scope") } }),
    });
    document.getElementById("color-result").textContent = `批量任务：${result.status}`;
  });
}

async function renderTimeline() {
  setShell("timeline");
  await ensureProject();
  view.innerHTML = page(
    "Editorial",
    "Shot / Timeline",
    "先建镜头，再挂时间线。后续配音和审片都拿 Shot ID 往下传。",
    `
      <div class="split">
        <form id="shot-form" class="surface" data-testid="shot-form">
          <h3>新建 Shot</h3>
          <label>Shot 标题 <input name="title" value="Shot 001" /></label>
          <label>时长 <input name="duration" type="number" value="3" /></label>
          <button class="primary" type="submit">创建 Shot</button>
        </form>
        <form id="timeline-form" class="surface" data-testid="timeline-form">
          <h3>新建 Timeline</h3>
          <label>Timeline 名称 <input name="name" value="Main Timeline" /></label>
          <button class="ghost" type="submit">创建 Timeline</button>
        </form>
      </div>
      <div id="timeline-result" class="surface"></div>
    `,
  );
  document.getElementById("shot-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/projects/${state.projectId}/shots`, {
      method: "POST",
      body: JSON.stringify({ title: form.get("title"), duration_seconds: Number(form.get("duration")) }),
    });
    document.getElementById("timeline-result").textContent = `Shot 已创建：${result.id}`;
  });
  document.getElementById("timeline-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/projects/${state.projectId}/timelines`, {
      method: "POST",
      body: JSON.stringify({ name: form.get("name") }),
    });
    document.getElementById("timeline-result").textContent = `Timeline 已创建：${result.id}`;
  });
}

async function renderAudio() {
  setShell("audio");
  await ensureProject();
  view.innerHTML = page(
    "Sound",
    "音频字幕",
    "台词挂在 Shot 上，BGM 单独进时间线。配音文件由本地 Worker 写出 WAV / SRT。",
    `
      <div class="split">
        <form id="dialogue-form" class="surface" data-testid="dialogue-form">
          <h3>台词</h3>
          <label>Shot ID <input name="shotId" type="number" min="1" /></label>
          <label>台词 <input name="text" value="开始吧" /></label>
          <button class="primary" type="submit">创建台词</button>
        </form>
        <form id="music-form" class="surface" data-testid="music-form">
          <h3>BGM</h3>
          <label>BGM URI <input name="assetUri" value="local://bgm.wav" /></label>
          <button class="ghost" type="submit">添加 BGM</button>
        </form>
      </div>
      <div id="audio-result" class="surface"></div>
    `,
  );
  document.getElementById("dialogue-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/shots/${form.get("shotId")}/dialogue-lines`, {
      method: "POST",
      body: JSON.stringify({ edited_text: form.get("text"), source_language: "zh" }),
    });
    document.getElementById("audio-result").textContent = `DialogueLine 已创建：${result.id}`;
  });
  document.getElementById("music-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/projects/${state.projectId}/music-cues`, {
      method: "POST",
      body: JSON.stringify({ data: { asset_uri: form.get("assetUri") } }),
    });
    document.getElementById("audio-result").textContent = `MusicCue 已创建：${result.id}`;
  });
}

async function renderResources() {
  setShell("resources");
  await ensureProject();
  const [assets, chapters, workItems, gates, jobs] = await Promise.all([
    api(`/projects/${state.projectId}/assets`),
    api(`/projects/${state.projectId}/chapters`),
    api(`/projects/${state.projectId}/work-items`),
    api(`/projects/${state.projectId}/production-gates`),
    api(`/projects/${state.projectId}/ai-jobs`),
  ]);
  view.innerHTML = page(
    "Library",
    "资源浏览",
    "当前项目里已经落地的对象。点进具体生产页才能新建。",
    `
      <section class="stack">
        ${resourceCard("Assets", assets)}
        ${resourceCard("Chapters", chapters)}
        ${resourceCard("Work Items", workItems)}
        ${resourceCard("Production Gates", gates)}
        ${resourceCard("AI Jobs", jobs)}
      </section>
    `,
  );
  setStatus("资源浏览已加载");
}

function resourceCard(title, items) {
  const rows = items
    .slice(0, 5)
    .map((item) => `<tr><td>#${item.id}</td><td>${item.name || item.title || item.job_type || item.gate_type || item.status}</td></tr>`)
    .join("");
  return `
    <article class="surface">
      <h3>${title}</h3>
      <p class="muted">${items.length} items</p>
      ${rows ? `<table class="data-table"><tbody>${rows}</tbody></table>` : `<div class="empty">暂无记录</div>`}
    </article>
  `;
}

async function renderAI() {
  setShell("ai");
  await ensureProject();
  view.innerHTML = page(
    "Models",
    "AI / ComfyUI 配置",
    "API Key 填上面这块，ComfyUI 地址填下面这块。保存后整个团队都能用，不需要再翻设置页。",
    `
      <div class="callout">
        <strong>就在这一页。</strong>
        第三方模型的 Base URL / API Key / 模型名，以及 ComfyUI 的 http://127.0.0.1:8188 和 Token，全部写在下面两个表单里。
      </div>
      <form id="provider-form" class="surface" data-testid="provider-form">
        <h3>第三方 AI Provider</h3>
        <p class="muted">OpenAI 兼容接口、自建 HTTP、或本地模型网关。Key 只存在团队配置里。</p>
        <label>名称 <input name="name" value="OpenAI Compatible" /></label>
        <label>类型
          <select name="providerType">
            <option value="third_party_api">第三方 API</option>
            <option value="custom_http">自定义 HTTP</option>
            <option value="local_model">本地模型</option>
          </select>
        </label>
        <label>Base URL <input name="baseUrl" placeholder="https://api.example.com" /></label>
        <label>API Key <input name="apiKey" type="password" placeholder="sk-..." autocomplete="off" /></label>
        <label>模型 <input name="model" placeholder="video-model" /></label>
        <label>能力 <input name="capabilities" value="analyze,colorize,video_generate,voice_generate" /></label>
        <button class="primary" type="submit">保存 AI Provider</button>
      </form>
      <form id="comfyui-form" class="surface" data-testid="comfyui-form">
        <h3>远程 / 本地 ComfyUI</h3>
        <p class="muted">填你已经起好的 ComfyUI 地址。本机默认 http://127.0.0.1:8188，有鉴权就填 Token。</p>
        <label>名称 <input name="name" value="Local ComfyUI" /></label>
        <label>地址 <input name="baseUrl" value="http://127.0.0.1:8188" /></label>
        <label>鉴权
          <select name="authType">
            <option value="none">无</option>
            <option value="bearer">Bearer Token</option>
            <option value="basic">Basic</option>
            <option value="custom_header">自定义 Header</option>
          </select>
        </label>
        <label>Token <input name="token" type="password" autocomplete="off" /></label>
        <label>自定义 Header 名称 <input name="customHeaderName" placeholder="X-API-Key" /></label>
        <label>最大并发 <input name="maxConcurrency" type="number" min="1" value="1" /></label>
        <button class="primary" type="submit">保存 ComfyUI</button>
      </form>
      <form id="workflow-form" class="surface" data-testid="workflow-form">
        <h3>Workflow 模板</h3>
        <p class="muted">上传 ComfyUI 导出的 JSON，系统会解析节点，之后可以改可发布参数。</p>
        <label>名称 <input name="name" value="Image to Video Workflow" /></label>
        <label>类型
          <select name="workflowType">
            <option value="image_to_video">图生视频</option>
            <option value="colorize">上色</option>
            <option value="first_last_frame_video">首尾帧视频</option>
            <option value="inpaint">局部重绘</option>
          </select>
        </label>
        <label>Workflow JSON <textarea name="workflowJson">{"1":{"class_type":"Node","inputs":{}}}</textarea></label>
        <button class="ghost" type="submit">上传并解析 Workflow</button>
      </form>
      <div id="ai-config-result" class="surface"></div>
    `,
    `<span class="pill">Mock adapters enabled</span>`,
  );
  document.getElementById("provider-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/teams/${state.teamId}/ai-providers`, {
      method: "POST",
      body: JSON.stringify({
        name: form.get("name"),
        provider_type: form.get("providerType"),
        capabilities: String(form.get("capabilities") || "")
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        config: { base_url: form.get("baseUrl"), api_key: form.get("apiKey"), model: form.get("model") },
      }),
    });
    localStorage.setItem("md_models_ready", "1");
    document.getElementById("setup-banner").hidden = true;
    document.getElementById("ai-config-result").textContent = `AI Provider 已保存：${result.id}`;
    setStatus("AI Provider 已保存");
  });
  document.getElementById("comfyui-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/teams/${state.teamId}/comfyui/instances`, {
      method: "POST",
      body: JSON.stringify({
        name: form.get("name"),
        base_url: form.get("baseUrl"),
        auth_type: form.get("authType"),
        token: form.get("token"),
        custom_header_name: form.get("customHeaderName"),
        max_concurrency: Number(form.get("maxConcurrency") || 1),
      }),
    });
    localStorage.setItem("md_models_ready", "1");
    document.getElementById("setup-banner").hidden = true;
    document.getElementById("ai-config-result").textContent = `ComfyUI 已保存：${result.id}`;
    setStatus("ComfyUI 已保存");
  });
  document.getElementById("workflow-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/projects/${state.projectId}/workflows`, {
      method: "POST",
      body: JSON.stringify({
        name: form.get("name"),
        workflow_type: form.get("workflowType"),
        workflow_json: JSON.parse(form.get("workflowJson")),
        published_parameters: { prompt: { node_id: "1", input: "text" } },
      }),
    });
    document.getElementById("ai-config-result").textContent = `Workflow 已解析：${result.id}`;
    setStatus("Workflow 已解析");
  });
  document.getElementById("mock-provider")?.addEventListener("click", () =>
    api(`/teams/${state.teamId}/ai-providers`, {
      method: "POST",
      body: JSON.stringify({ name: "Mock Provider", provider_type: "third_party_api", capabilities: ["video"] }),
    }).then(() => setStatus("Mock Provider 已创建")),
  );
  document.getElementById("mock-comfy")?.addEventListener("click", () =>
    api(`/teams/${state.teamId}/comfyui/instances`, {
      method: "POST",
      body: JSON.stringify({ name: "Local ComfyUI", base_url: "http://127.0.0.1:8188", auth_type: "none" }),
    }).then(() => setStatus("ComfyUI 配置已创建")),
  );
  document.getElementById("mock-workflow")?.addEventListener("click", () =>
    api(`/projects/${state.projectId}/workflows`, {
      method: "POST",
      body: JSON.stringify({ name: "Mock Workflow", workflow_type: "image_to_video", workflow_json: { "1": { class_type: "Node" } } }),
    }).then(() => setStatus("Workflow 已创建")),
  );
}

async function renderReview() {
  setShell("review");
  await ensureProject();
  view.innerHTML = page(
    "QC",
    "审核导出",
    "先出 QC，再创建导出包。客户审片和冻结交付在「质量交付 / 合规下载」。",
    `
      <section class="surface">
        <div class="page-actions">
          <button class="primary" id="qc">创建 QC</button>
          <button class="ghost" id="export">创建导出</button>
        </div>
      </section>
    `,
  );
  document.getElementById("qc").addEventListener("click", () =>
    api(`/projects/${state.projectId}/qc-reports`, { method: "POST", body: JSON.stringify({ data: { checks: { video_playable: true } } }) }).then(() =>
      setStatus("QC 已创建"),
    ),
  );
  document.getElementById("export").addEventListener("click", () =>
    api(`/projects/${state.projectId}/exports`, { method: "POST", body: JSON.stringify({ data: { resolution: "1920x1080" } }) }).then(() =>
      setStatus("导出已创建"),
    ),
  );
}

async function renderDelivery() {
  setShell("delivery");
  await ensureProject();
  view.innerHTML = page(
    "Delivery",
    "质量交付",
    "审片包给客户看，高级格式给成片库。真正冻结下载走合规页。",
    `
      <div class="split">
        <form id="review-package-form" class="surface" data-testid="review-package-form">
          <h3>审片包</h3>
          <label>包类型 <input name="packageType" value="client_review" /></label>
          <button class="primary" type="submit">创建审片包</button>
        </form>
        <form id="advanced-export-form" class="surface" data-testid="advanced-export-form">
          <h3>高级格式</h3>
          <label>Export ID <input name="exportId" type="number" min="1" /></label>
          <label>格式 <input name="format" value="prores" /></label>
          <button class="ghost" type="submit">生成高级格式</button>
        </form>
      </div>
      <div id="delivery-result" class="surface"></div>
    `,
  );
  document.getElementById("review-package-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/projects/${state.projectId}/review-packages`, {
      method: "POST",
      body: JSON.stringify({ data: { package_type: form.get("packageType") } }),
    });
    document.getElementById("delivery-result").textContent = `审片包已创建：${result.id}`;
  });
  document.getElementById("advanced-export-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/exports/${form.get("exportId")}/advanced-format`, {
      method: "POST",
      body: JSON.stringify({ data: { format: form.get("format") } }),
    });
    document.getElementById("delivery-result").textContent = `高级导出已创建：${result.id}`;
  });
}

async function renderReports() {
  setShell("reports");
  await ensureProject();
  const [workItems, gates, jobs, errors] = await Promise.all([
    api(`/projects/${state.projectId}/work-items`),
    api(`/projects/${state.projectId}/production-gates`),
    api(`/projects/${state.projectId}/ai-jobs`),
    api(`/projects/${state.projectId}/error-logs`),
  ]);
  const succeededJobs = jobs.filter((job) => job.status === "succeeded").length;
  view.innerHTML = page(
    "Pulse",
    "报表看板",
    "生产计数和失败面。数字来自当前项目，不是演示数据。",
    `
      <section class="surface">
        <table class="data-table">
          <thead><tr><th>指标</th><th>数量</th><th>备注</th></tr></thead>
          <tbody>
            <tr><td>Work Items</td><td>${workItems.length}</td><td>开放生产任务</td></tr>
            <tr><td>Production Gates</td><td>${gates.length}</td><td>关卡</td></tr>
            <tr><td>AI Jobs</td><td>${jobs.length}</td><td>${succeededJobs} succeeded</td></tr>
            <tr><td>Error Logs</td><td>${errors.length}</td><td>需要处理的失败</td></tr>
          </tbody>
        </table>
      </section>
    `,
  );
  setStatus("报表已加载");
}

async function renderCompliance() {
  setShell("compliance");
  await ensureProject();
  view.innerHTML = page(
    "Release",
    "合规下载",
    "下载链接带短时 token。冻结前会跑 preflight，包打进本地存储。",
    `
      <div class="split">
        <form id="download-token-form" class="surface" data-testid="download-token-form">
          <h3>素材下载</h3>
          <label>Asset ID <input name="assetId" type="number" min="1" /></label>
          <button class="primary" type="submit">生成下载 Token</button>
        </form>
        <form id="freeze-export-form" class="surface" data-testid="freeze-export-form">
          <h3>冻结交付</h3>
          <label>Export ID <input name="exportId" type="number" min="1" /></label>
          <button class="ghost" type="submit">Preflight + Freeze</button>
        </form>
      </div>
      <div id="compliance-result" class="surface"></div>
    `,
  );
  document.getElementById("download-token-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/assets/${form.get("assetId")}/download-token`, { method: "POST" });
    document.getElementById("compliance-result").innerHTML = `下载链接：<a href="/downloads/${result.id}">/downloads/${result.id}</a>`;
  });
  document.getElementById("freeze-export-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const exportId = form.get("exportId");
    await api(`/exports/${exportId}/preflight`, { method: "POST" });
    const result = await api(`/exports/${exportId}/freeze`, { method: "POST" });
    document.getElementById("compliance-result").textContent = `交付包已冻结：${result.data.package_uri}`;
  });
}

async function renderP2() {
  setShell("p2");
  await ensureProject();
  view.innerHTML = page(
    "Private",
    "P2 管理",
    "私有化部署和角色 LoRA 训练入口。V1 只落配置对象，不真正连训练集群。",
    `
      <section class="surface">
        <div class="page-actions">
          <button class="primary" id="private-deployment">私有化配置</button>
          <button class="ghost" id="training">模型训练任务</button>
        </div>
      </section>
    `,
  );
  document.getElementById("private-deployment").addEventListener("click", () =>
    api(`/teams/${state.teamId}/private-deployments`, { method: "POST", body: JSON.stringify({ data: { deployment_mode: "single_tenant" } }) }).then(() =>
      setStatus("私有化配置已创建"),
    ),
  );
  document.getElementById("training").addEventListener("click", () =>
    api(`/projects/${state.projectId}/model-training-jobs`, { method: "POST", body: JSON.stringify({ data: { training_type: "character_lora" } }) }).then(() =>
      setStatus("训练任务已创建"),
    ),
  );
}

async function renderOps() {
  setShell("ops");
  await ensureProject();
  const jobs = await api(`/projects/${state.projectId}/ai-jobs`);
  view.innerHTML = page(
    "Runtime",
    "运维 / Worker",
    "本地同步 Worker。点一次就把当前项目 pending 任务跑完。",
    `
      <section class="surface">
        <div class="metric-row">
          <div class="metric"><b>${jobs.length}</b><span>AI Jobs</span></div>
        </div>
        <p></p>
        <button class="primary" id="run-pending">运行 pending jobs</button>
      </section>
    `,
  );
  document.getElementById("run-pending").addEventListener("click", () =>
    api(`/projects/${state.projectId}/ai-jobs/run-pending`, { method: "POST" }).then((jobs) => setStatus(`已处理 ${jobs.length} 个任务`)),
  );
}

async function renderNotifications() {
  setShell("notifications");
  await ensureProject();
  const [jobs, errors] = await Promise.all([
    api(`/projects/${state.projectId}/ai-jobs`),
    api(`/projects/${state.projectId}/error-logs`),
  ]);
  const failedJobs = jobs.filter((job) => ["failed", "cancelled"].includes(job.status));
  view.innerHTML = page(
    "Inbox",
    "通知中心",
    "失败任务和错误日志堆在这里，不另做消息总线。",
    `
      <section class="surface">
        <table class="data-table">
          <thead><tr><th>类型</th><th>计数</th></tr></thead>
          <tbody>
            <tr><td>任务通知</td><td><span class="pill">${jobs.length} jobs</span> <span class="pill">${failedJobs.length} attention</span></td></tr>
            <tr><td>错误通知</td><td><span class="pill">${errors.length} logs</span></td></tr>
          </tbody>
        </table>
        <h3>最近状态</h3>
        <ul>${state.statusHistory.map((entry) => `<li>${entry.at} - ${entry.message}</li>`).join("") || "<li class='muted'>还没有状态</li>"}</ul>
      </section>
    `,
  );
  setStatus("通知中心已加载");
}

function renderHelp() {
  setShell("help");
  view.innerHTML = page(
    "Manual",
    "帮助与快捷键",
    "键盘在空白处生效。输入框里打字不会被抢走。",
    `
      <div class="split">
        <article class="surface">
          <h3>快捷键</h3>
          <p><span class="kbd">d</span> Dashboard</p>
          <p><span class="kbd">p</span> 链路向导</p>
          <p><span class="kbd">i</span> 导入</p>
          <p><span class="kbd">c</span> 上色</p>
          <p><span class="kbd">t</span> 时间线</p>
          <p><span class="kbd">a</span> 音频</p>
          <p><span class="kbd">r</span> 报表</p>
          <p><span class="kbd">o</span> 运维</p>
          <p><span class="kbd">m</span> AI / ComfyUI</p>
          <p><span class="kbd">Ctrl</span> <span class="kbd">K</span> 命令盘</p>
        </article>
        <article class="surface">
          <h3>推荐流程</h3>
          <ol>
            <li>登录后立刻打开「AI / ComfyUI」，填 API Key 和 ComfyUI 地址。</li>
            <li>回到 Dashboard 创建或选中项目。</li>
            <li>用链路向导生成默认生产任务。</li>
            <li>导入漫画，再走上色和 Shot / Timeline。</li>
            <li>音频字幕完成后进入审核导出和合规下载。</li>
          </ol>
        </article>
      </div>
    `,
  );
  setStatus("帮助已加载");
}

function renderSettings() {
  setShell("settings");
  view.innerHTML = page(
    "Session",
    "设置",
    "这里只保存登录 token 和当前团队 / 项目。模型 Key 不在这里，去「AI / ComfyUI」。",
    `
      <form id="context-form" class="surface" data-testid="context-form">
        <label>Token <textarea name="token">${state.token}</textarea></label>
        <label>Team ID <input name="teamId" type="number" value="${state.teamId || ""}" /></label>
        <label>Project ID <input name="projectId" type="number" value="${state.projectId || ""}" /></label>
        <button class="primary" type="submit">保存上下文</button>
      </form>
    `,
  );
  document.getElementById("context-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    state.token = String(form.get("token") || "");
    state.teamId = Number(form.get("teamId") || 0);
    state.projectId = Number(form.get("projectId") || 0);
    localStorage.setItem("md_token", state.token);
    localStorage.setItem("md_team_id", state.teamId);
    localStorage.setItem("md_project_id", state.projectId);
    setShell("settings");
    setStatus("上下文已保存");
  });
}

renderRoute(state.token ? "dashboard" : "auth");
