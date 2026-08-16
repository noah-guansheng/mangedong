const state = {
  token: localStorage.getItem("md_token") || "",
  teamId: Number(localStorage.getItem("md_team_id") || 0),
  projectId: Number(localStorage.getItem("md_project_id") || 0),
  statusHistory: [],
  activeRoute: "",
  selectedPanelId: 0,
};

const ROUTES = [
  { id: "dashboard", label: "总览", group: "生产" },
  { id: "pipeline", label: "链路向导", group: "生产" },
  { id: "import", label: "导入", group: "生产" },
  { id: "panels", label: "分格", group: "生产" },
  { id: "color", label: "上色", group: "生产" },
  { id: "timeline", label: "镜头", group: "生产" },
  { id: "audio", label: "音频", group: "生产" },
  { id: "review", label: "审片", group: "交付" },
  { id: "delivery", label: "导出", group: "交付" },
  { id: "compliance", label: "合规下载", group: "交付" },
  { id: "resources", label: "资源浏览", group: "交付" },
  { id: "ai", label: "模型配置", group: "系统" },
  { id: "members", label: "成员", group: "系统" },
  { id: "ops", label: "任务", group: "系统" },
  { id: "reports", label: "报表", group: "系统" },
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

function persistSession() {
  localStorage.setItem("md_token", state.token);
  localStorage.setItem("md_team_id", String(state.teamId || ""));
  localStorage.setItem("md_project_id", String(state.projectId || ""));
  document.cookie = `md_session=${state.token}; path=/; SameSite=Lax`;
}

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
  if (response.status === 204) return {};
  const text = await response.text();
  return text ? JSON.parse(text) : {};
}

function renderRoute(route) {
  if (palette?.open) palette.close();
  const routes = {
    auth: renderAuth,
    dashboard: renderDashboard,
    pipeline: renderPipeline,
    production: renderProduction,
    import: renderImport,
    panels: renderPanels,
    color: renderColor,
    timeline: renderTimeline,
    audio: renderAudio,
    resources: renderResources,
    ai: renderAI,
    members: renderMembers,
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
  if (event.key === "Escape" && palette?.open) palette.close();
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement) return;
  const shortcuts = { d: "dashboard", p: "pipeline", i: "import", c: "color", t: "timeline", a: "audio", r: "reports", o: "ops", h: "help", m: "ai" };
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
          <p class="kicker">mangedong / studio</p>
          <h1>把漫画做成能交货的番剧。</h1>
          <p>登录后先配模型，再走导入、上色、镜头、配音、审片和导出。</p>
        </div>
        <p class="muted">团队工作室 Web SaaS</p>
      </div>
      <div class="auth-panel">
        <p class="kicker">Account</p>
        <h2>登录工作室</h2>
        <form id="auth-form" class="surface">
          <label>邮箱 <input name="email" type="email" value="owner@example.com" /></label>
          <label>密码 <input name="password" type="password" value="password123" /></label>
          <label>Display name <input name="displayName" value="Owner" /></label>
          <button class="primary" type="submit">进入工作台</button>
        </form>
        <form id="reset-form" class="surface">
          <h3>忘记密码</h3>
          <label>邮箱 <input name="email" type="email" value="owner@example.com" /></label>
          <label>新密码 <input name="password" type="password" value="password123" /></label>
          <button class="ghost" type="submit">发送重置并改密</button>
          <p id="reset-result" class="muted"></p>
        </form>
        <form id="invite-form" class="surface">
          <h3>接受邀请</h3>
          <label>邀请令牌 <input name="token" /></label>
          <label>Display name <input name="displayName" value="Artist" /></label>
          <label>设置密码 <input name="password" type="password" value="password123" /></label>
          <button class="ghost" type="submit">加入团队</button>
          <p id="invite-result" class="muted"></p>
        </form>
      </div>
    </section>
  `;
  document.getElementById("auth-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = { email: form.get("email"), password: form.get("password"), display_name: form.get("displayName") };
    try {
      await api("/auth/register", { method: "POST", body: JSON.stringify(payload) });
    } catch (_) {
      // Existing users continue to login.
    }
    const login = await api("/auth/login", { method: "POST", body: JSON.stringify({ email: payload.email, password: payload.password }) });
    state.token = login.access_token;
    persistSession();
    setStatus("登录成功");
    await renderDashboard();
  });
  document.getElementById("reset-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const forgot = await api("/auth/forgot-password", { method: "POST", body: JSON.stringify({ email: form.get("email") }) });
    if (!forgot.reset_token) {
      document.getElementById("reset-result").textContent = "如果邮箱存在，会发出重置令牌。";
      return;
    }
    await api("/auth/reset-password", { method: "POST", body: JSON.stringify({ token: forgot.reset_token, password: form.get("password") }) });
    document.getElementById("reset-result").textContent = "密码已重置，请用新密码登录。";
  });
  document.getElementById("invite-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const accepted = await api("/auth/accept-invite", {
      method: "POST",
      body: JSON.stringify({ token: form.get("token"), password: form.get("password"), display_name: form.get("displayName") }),
    });
    state.token = accepted.access_token;
    persistSession();
    document.getElementById("invite-result").textContent = "邀请已接受，正在进入工作台。";
    await renderDashboard();
  });
}

async function ensureTeam() {
  const teams = await api("/teams");
  if (teams.length === 0) {
    const team = await api("/teams", { method: "POST", body: JSON.stringify({ name: "Default Studio" }) });
    state.teamId = team.id;
  } else if (!state.teamId || !teams.some((team) => team.id === state.teamId)) {
    state.teamId = teams[0].id;
  }
  persistSession();
  return teams;
}

async function createDefaultProject() {
  await ensureTeam();
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
  persistSession();
  setStatus("项目已创建");
  return project;
}

async function ensureProject() {
  await ensureTeam();
  if (!state.projectId) await createDefaultProject();
}

async function renderDashboard() {
  setShell("dashboard");
  await ensureTeam();
  const [projects, members, workItems] = await Promise.all([
    api(`/projects?team_id=${state.teamId}`),
    api(`/teams/${state.teamId}/members`),
    state.projectId ? api(`/projects/${state.projectId}/work-items`) : Promise.resolve([]),
  ]);
  view.innerHTML = page(
    "Overview",
    "项目总览",
    "查看剧集状态和进度，选中后进入导入、分格和镜头。",
    `<section class="surface" id="dashboard-cards"></section>
     <form id="brief-form" class="surface">
       <h3>立项向导</h3>
       <label>剧集名 <input name="name" value="Episode 1" /></label>
       <label>客户 <input name="customer" value="Demo Client" /></label>
       <label>IP <input name="ip" value="Demo IP" /></label>
       <label>章节范围 <input name="scope" value="Chapter 1" /></label>
       <label>时长（分钟） <input name="runtime" type="number" value="3" /></label>
       <button class="primary" type="submit">创建剧集</button>
     </form>`,
    `<button class="ghost" id="create-project">快速创建默认剧集</button>`,
  );
  const rows = projects
    .map((project) => {
      const current = project.id === state.projectId;
      return `
        <tr class="${current ? "is-current" : ""}">
          <td>${project.name} ${current ? '<span class="pill hot">当前</span>' : ""}</td>
          <td><span class="dot ${project.status === "draft" ? "live" : "done"}"></span>${project.status}</td>
          <td>#${project.id}</td>
          <td><button class="ghost" data-project-id="${project.id}">设为当前项目</button></td>
        </tr>`;
    })
    .join("");
  document.getElementById("dashboard-cards").innerHTML = `
    <div class="metric-row">
      <div class="metric"><b>${state.teamId}</b><span>团队</span></div>
      <div class="metric"><b>${projects.length}</b><span>项目数</span></div>
      <div class="metric"><b>${members.length}</b><span>成员</span></div>
    </div>
    ${
      rows
        ? `<table class="data-table"><thead><tr><th>剧集</th><th>状态</th><th>ID</th><th></th></tr></thead><tbody>${rows}</tbody></table>`
        : `<div class="empty">还没有项目。先新建剧集，再去模型配置填 Key。</div>`
    }
    ${
      workItems.length
        ? `<h3>当前项目任务</h3><table class="data-table"><thead><tr><th>任务</th><th>阶段</th><th>状态</th><th></th></tr></thead><tbody>${workItems
            .map(
              (item) => `<tr><td>${item.title}</td><td>${item.stage}</td><td>${item.status}</td><td>
                <button class="ghost" data-item-id="${item.id}" data-status="in_progress">开始</button>
                <button class="ghost" data-item-id="${item.id}" data-status="done">完成</button>
              </td></tr>`,
            )
            .join("")}</tbody></table>`
        : ""
    }
  `;
  document.getElementById("create-project").addEventListener("click", async () => {
    await createDefaultProject();
    await renderDashboard();
  });
  document.getElementById("brief-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await ensureTeam();
    const project = await api("/projects", {
      method: "POST",
      body: JSON.stringify({
        team_id: state.teamId,
        name: form.get("name"),
        brief: {
          customer_name: form.get("customer"),
          ip_name: form.get("ip"),
          chapter_scope: form.get("scope"),
          estimated_runtime_minutes: Number(form.get("runtime") || 3),
          target_languages: ["zh", "ja", "en"],
          aspect_ratio: "16:9",
          resolution: "1920x1080",
          fps: 24,
          authorization_status: "licensed",
        },
      }),
    });
    state.projectId = project.id;
    persistSession();
    setStatus("立项完成");
    await renderDashboard();
  });
  document.querySelectorAll("[data-project-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.projectId = Number(button.dataset.projectId);
      persistSession();
      setStatus(`当前项目：${state.projectId}`);
      renderDashboard();
    });
  });
  document.querySelectorAll("[data-item-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      await api(`/work-items/${button.dataset.itemId}`, { method: "PATCH", body: JSON.stringify({ status: button.dataset.status }) });
      setStatus("任务状态已更新");
      await renderDashboard();
    });
  });
  setStatus("Dashboard 已加载");
}

async function renderProduction() {
  setShell("dashboard");
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
    "当前剧集计数。具体操作走导入、分格、上色和镜头。",
    `<section class="surface"><div class="metric-row">
      <div class="metric"><b>${assets.length}</b><span>素材</span></div>
      <div class="metric"><b>${chapters.length}</b><span>章节</span></div>
      <div class="metric"><b>${workItems.length}</b><span>Work Items</span></div>
      <div class="metric"><b>${gates.length}</b><span>Gates</span></div>
      <div class="metric"><b>${jobs.length}</b><span>AI Jobs</span></div>
    </div></section>`,
  );
  setStatus("生产工作台已加载");
}

async function renderPipeline() {
  setShell("pipeline");
  await ensureProject();
  view.innerHTML = page(
    "Sequence",
    "端到端链路向导",
    "按交货顺序走完一条剧集。",
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
    await Promise.all(stages.map((stage) => api(`/projects/${state.projectId}/work-items`, { method: "POST", body: JSON.stringify({ title: `${stage} task`, stage, priority: "normal" }) })));
    document.getElementById("pipeline-result").textContent = "默认生产任务已创建";
    setStatus("链路任务已创建");
  });
}

function pipelineStep(index, title, description) {
  return `<li class="step"><span class="step-index">${index}</span><div><h3>${title}</h3><p class="muted">${description}</p></div></li>`;
}

async function renderImport() {
  setShell("import");
  await ensureProject();
  view.innerHTML = page(
    "Ingest",
    "漫画导入",
    "上传原作后会生成章节、页面和分格，随后到「分格」页做 OCR、上色和视频。",
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

async function renderPanels() {
  setShell("panels");
  await ensureProject();
  const tree = await api(`/projects/${state.projectId}/structure`);
  const firstPanel = tree.chapters.flatMap((chapter) => chapter.pages.flatMap((page) => page.panels))[0];
  if (!state.selectedPanelId && firstPanel) state.selectedPanelId = firstPanel.id;
  const selectedPage = tree.chapters.flatMap((chapter) => chapter.pages).find((page) => page.panels.some((panel) => panel.id === state.selectedPanelId));
  view.innerHTML = page(
    "Panel",
    "分格工作台",
    "左侧选页和格，中间看原图，右侧跑 OCR、分析、上色和视频。这是单分格生产的主界面。",
    tree.chapters.length === 0
      ? `<div class="empty">还没有导入内容。先到「导入」上传漫画页。</div>`
      : `
        <section class="workbench">
          <aside class="surface tree" id="panel-tree"></aside>
          <div class="preview-frame" id="panel-preview">${selectedPage ? `<img alt="page preview" src="${selectedPage.preview_url}" />` : `<p class="muted">选择一个分格</p>`}</div>
          <form class="surface" id="panel-actions">
            <h3>分格 #${state.selectedPanelId || "—"}</h3>
            <button class="primary" type="button" data-action="ocr">OCR</button>
            <p></p>
            <button class="ghost" type="button" data-action="analyze">内容分析</button>
            <p></p>
            <button class="ghost" type="button" data-action="colorize">参考上色</button>
            <p></p>
            <button class="ghost" type="button" data-action="video">生成视频</button>
            <div id="panel-result" class="muted"></div>
          </form>
        </section>
      `,
  );
  if (!tree.chapters.length) return;
  document.getElementById("panel-tree").innerHTML = tree.chapters
    .map(
      (chapter) => `
        <p class="kicker">${chapter.title}</p>
        ${chapter.pages
          .map(
            (page) => `
              <p class="muted">第 ${page.page_number} 页</p>
              ${page.panels
                .map(
                  (panel) => `<button type="button" data-panel-id="${panel.id}" class="${panel.id === state.selectedPanelId ? "is-active" : ""}">分格 ${panel.panel_index}</button>`,
                )
                .join("")}
            `,
          )
          .join("")}
      `,
    )
    .join("");
  document.querySelectorAll("[data-panel-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedPanelId = Number(button.dataset.panelId);
      renderPanels();
    });
  });
  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!state.selectedPanelId) return;
      const action = button.dataset.action;
      const paths = {
        ocr: `/panels/${state.selectedPanelId}/ocr`,
        analyze: `/panels/${state.selectedPanelId}/analyze`,
        colorize: `/panels/${state.selectedPanelId}/colorize`,
        video: `/panels/${state.selectedPanelId}/generate-video`,
      };
      const body = action === "colorize" ? { data: { palette: "cel" } } : action === "video" ? { data: { provider: "comfyui", duration_seconds: 3 } } : undefined;
      const result = await api(paths[action], { method: "POST", body: body ? JSON.stringify(body) : undefined });
      document.getElementById("panel-result").textContent = `${action} → ${result.resource_type || result.status} #${result.id} ${result.data?.execution_mode || result.data?.mode || ""}`;
      const preview = document.getElementById("panel-preview");
      if (preview && result.data?.output_asset_uri) {
        preview.innerHTML =
          action === "video"
            ? `<video class="player" controls src="/resources/${result.id}/file"></video>`
            : `<img alt="${action} preview" src="/resources/${result.id}/file" />`;
      }
      setStatus(`${action} 完成`);
    });
  });
  setStatus("分格工作台已加载");
}

async function renderColor() {
  setShell("color");
  await ensureProject();
  view.innerHTML = page(
    "Paint",
    "上色生产",
    "单格出 PNG，或按项目批量跑。参考图和角色档案也在这里维护。",
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
      <div class="split">
        <form id="reference-form" class="surface">
          <h3>上色参考</h3>
          <label>名称 <input name="name" value="colored-page" /></label>
          <label>URI <input name="uri" value="local://refs/colored.png" /></label>
          <button class="ghost" type="submit">保存参考</button>
        </form>
        <form id="character-form" class="surface">
          <h3>角色设定</h3>
          <label>名称 <input name="name" value="Hero" /></label>
          <label>发色 <input name="hair" value="#111827" /></label>
          <button class="ghost" type="submit">保存角色</button>
        </form>
      </div>
      <div id="color-result" class="surface"></div>
    `,
  );
  document.getElementById("colorize-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/panels/${form.get("panelId")}/colorize`, { method: "POST", body: JSON.stringify({ data: { palette: form.get("palette") } }) });
    document.getElementById("color-result").textContent = `上色输出：${result.data.output_asset_uri}`;
  });
  document.getElementById("batch-color-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/projects/${state.projectId}/batch-colorize`, { method: "POST", body: JSON.stringify({ data: { scope: form.get("scope") } }) });
    document.getElementById("color-result").textContent = `批量任务：${result.status}`;
  });
  document.getElementById("reference-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/projects/${state.projectId}/references`, { method: "POST", body: JSON.stringify({ data: { name: form.get("name"), uri: form.get("uri") } }) });
    document.getElementById("color-result").textContent = `参考已保存：${result.id}`;
  });
  document.getElementById("character-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/projects/${state.projectId}/characters`, { method: "POST", body: JSON.stringify({ data: { name: form.get("name"), hair_color: form.get("hair") } }) });
    document.getElementById("color-result").textContent = `角色已保存：${result.id}`;
  });
}

async function renderTimeline() {
  setShell("timeline");
  await ensureProject();
  const [shots, timelines, clips] = await Promise.all([
    api(`/projects/${state.projectId}/resources?resource_type=shot`),
    api(`/projects/${state.projectId}/resources?resource_type=timeline`),
    api(`/projects/${state.projectId}/resources?resource_type=video_clip`),
  ]);
  const timeline = timelines[0];
  const items = timeline?.data?.items || [];
  const total = Math.max(12, ...items.map((item) => Number(item.end_seconds || 0)), ...shots.map((shot) => Number(shot.data.duration_seconds || 0)));
  view.innerHTML = page(
    "Editorial",
    "Shot / Timeline",
    "先建镜头，再出 Animatic，最后挂到时间线。",
    `
      <section class="surface">
        <h3>装配时间线</h3>
        ${
          items.length
            ? items
                .map((item) => {
                  const start = (Number(item.start_seconds || 0) / total) * 100;
                  const width = Math.max(8, ((Number(item.end_seconds || 0) - Number(item.start_seconds || 0)) / total) * 100);
                  return `<div class="track-row"><span>${item.item_type}</span><div class="track"><b style="left:${start}%;width:${width}%"></b></div></div>`;
                })
                .join("")
            : `<div class="empty">还没有时间线片段。先创建 Shot，再创建 Timeline。</div>`
        }
      </section>
      <section class="surface">
        <h3>Shot List</h3>
        ${
          shots.length
            ? `<table class="data-table"><thead><tr><th>ID</th><th>标题</th><th>时长</th></tr></thead><tbody>${shots
                .map((shot) => `<tr><td>#${shot.id}</td><td>${shot.data.title || "Shot"}</td><td>${shot.data.duration_seconds || "—"}s</td></tr>`)
                .join("")}</tbody></table>`
            : `<div class="empty">还没有镜头。</div>`
        }
      </section>
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
      <div class="split">
        <form id="animatic-form" class="surface">
          <h3>Animatic</h3>
          <label>Shot ID <input name="shotId" type="number" min="1" value="${shots[0]?.id || ""}" /></label>
          <button class="ghost" type="submit">生成 Animatic MP4</button>
        </form>
        <form id="timeline-item-form" class="surface">
          <h3>挂到时间线</h3>
          <label>Timeline ID <input name="timelineId" type="number" min="1" value="${timeline?.id || ""}" /></label>
          <label>Clip ID <input name="clipId" type="number" min="1" value="${clips[0]?.id || ""}" /></label>
          <button class="ghost" type="submit">添加片段</button>
        </form>
      </div>
      <div id="timeline-result" class="surface"></div>
    `,
  );
  document.getElementById("shot-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/projects/${state.projectId}/shots`, { method: "POST", body: JSON.stringify({ title: form.get("title"), duration_seconds: Number(form.get("duration")) }) });
    document.getElementById("timeline-result").textContent = `Shot 已创建：${result.id}`;
    setStatus("Shot 已创建");
  });
  document.getElementById("timeline-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/projects/${state.projectId}/timelines`, { method: "POST", body: JSON.stringify({ name: form.get("name") }) });
    document.getElementById("timeline-result").textContent = `Timeline 已创建：${result.id}`;
  });
  document.getElementById("animatic-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/shots/${form.get("shotId")}/generate-animatic`, { method: "POST" });
    document.getElementById("timeline-result").innerHTML = `Animatic 已生成：#${result.id}<br><video class="player" controls src="/resources/${result.id}/file"></video>`;
  });
  document.getElementById("timeline-item-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/timelines/${form.get("timelineId")}/items`, {
      method: "POST",
      body: JSON.stringify({ item_type: "video", resource_id: Number(form.get("clipId")), start_seconds: 0, end_seconds: 3 }),
    });
    document.getElementById("timeline-result").textContent = `已挂到时间线，共 ${result.data.items.length} 段`;
    setStatus("时间线已更新");
  });
}

async function renderAudio() {
  setShell("audio");
  await ensureProject();
  view.innerHTML = page(
    "Sound",
    "音频字幕",
    "台词挂在 Shot 上，配音写出 WAV，字幕写出 SRT。",
    `
      <div class="split">
        <form id="dialogue-form" class="surface" data-testid="dialogue-form">
          <h3>台词</h3>
          <label>Shot ID <input name="shotId" type="number" min="1" /></label>
          <label>台词 <input name="text" value="开始吧" /></label>
          <button class="primary" type="submit">创建台词</button>
          <p></p>
          <label>台词 ID <input name="dialogueId" type="number" min="1" /></label>
          <button class="ghost" type="button" id="make-voice">生成配音 WAV</button>
          <button class="ghost" type="button" id="make-subtitle">生成字幕 SRT</button>
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
    const result = await api(`/shots/${form.get("shotId")}/dialogue-lines`, { method: "POST", body: JSON.stringify({ edited_text: form.get("text"), source_language: "zh" }) });
    document.getElementById("audio-result").textContent = `DialogueLine 已创建：${result.id}`;
  });
  document.getElementById("music-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/projects/${state.projectId}/music-cues`, { method: "POST", body: JSON.stringify({ data: { asset_uri: form.get("assetUri") } }) });
    document.getElementById("audio-result").textContent = `MusicCue 已创建：${result.id}`;
  });
  document.getElementById("make-voice").addEventListener("click", async () => {
    const dialogueId = document.querySelector('#dialogue-form [name="dialogueId"]').value;
    const result = await api(`/dialogue-lines/${dialogueId}/voice`, { method: "POST", body: JSON.stringify({ data: { voice: "hero-zh" } }) });
    document.getElementById("audio-result").textContent = `配音已生成：${result.data.audio_uri}`;
  });
  document.getElementById("make-subtitle").addEventListener("click", async () => {
    const dialogueId = document.querySelector('#dialogue-form [name="dialogueId"]').value;
    const result = await api(`/dialogue-lines/${dialogueId}/subtitle`, { method: "POST", body: JSON.stringify({ data: {} }) });
    document.getElementById("audio-result").textContent = `字幕已生成：${result.data.srt_uri || result.id}`;
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
    "当前项目已经落地的对象。",
    `<section class="stack">${resourceCard("Assets", assets)}${resourceCard("Chapters", chapters)}${resourceCard("Work Items", workItems)}${resourceCard("Production Gates", gates)}${resourceCard("AI Jobs", jobs)}</section>`,
  );
  setStatus("资源浏览已加载");
}

function resourceCard(title, items) {
  const rows = items
    .slice(0, 8)
    .map((item) => `<tr><td>#${item.id}</td><td>${item.name || item.title || item.job_type || item.gate_type || item.status}</td></tr>`)
    .join("");
  return `<article class="surface"><h3>${title}</h3><p class="muted">${items.length} items</p>${rows ? `<table class="data-table"><tbody>${rows}</tbody></table>` : `<div class="empty">暂无记录</div>`}</article>`;
}

async function renderAI() {
  setShell("ai");
  await ensureTeam();
  await ensureProject();
  const [providers, instances, workflows] = await Promise.all([
    api(`/teams/${state.teamId}/ai-providers`),
    api(`/teams/${state.teamId}/resources?resource_type=comfyui_instance`),
    api(`/projects/${state.projectId}/workflows`),
  ]);
  view.innerHTML = page(
    "Models",
    "AI / ComfyUI 配置",
    "API Key 填上面这块，ComfyUI 地址填下面这块。保存后整个团队都能用。",
    `
      <div class="callout"><strong>就在这一页。</strong> 第三方模型的 Base URL / API Key / 模型名，以及 ComfyUI 的 http://127.0.0.1:8188 和 Token，全部写在下面两个表单里。</div>
      <section class="surface">
        <h3>已保存</h3>
        <p class="muted">${providers.length} providers · ${instances.length} ComfyUI · ${workflows.length} workflows</p>
      </section>
      <form id="provider-form" class="surface" data-testid="provider-form">
        <h3>第三方 AI Provider</h3>
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
        <p class="muted">局域网地址填 8188；内网穿透后把公网 URL 填到「内网穿透 URL」，健康检查会先探穿透地址。</p>
        <label>名称 <input name="name" value="Local ComfyUI" /></label>
        <label>地址 <input name="baseUrl" value="http://127.0.0.1:8188" /></label>
        <label>内网穿透 URL <input name="tunnelUrl" placeholder="https://comfy.xxx.ngrok-free.app" /></label>
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
        <button class="ghost" type="button" id="check-comfy">健康检查</button>
      </form>
      <form id="workflow-form" class="surface" data-testid="workflow-form">
        <h3>Workflow 模板</h3>
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
  );
  document.getElementById("provider-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/teams/${state.teamId}/ai-providers`, {
      method: "POST",
      body: JSON.stringify({
        name: form.get("name"),
        provider_type: form.get("providerType"),
        capabilities: String(form.get("capabilities") || "").split(",").map((item) => item.trim()).filter(Boolean),
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
        tunnel_url: form.get("tunnelUrl") || null,
        auth_type: form.get("authType"),
        token: form.get("token"),
        custom_header_name: form.get("customHeaderName"),
        max_concurrency: Number(form.get("maxConcurrency") || 1),
      }),
    });
    localStorage.setItem("md_models_ready", "1");
    document.getElementById("setup-banner").hidden = true;
    const health = await api(`/comfyui/instances/${result.id}/health-check`, { method: "POST" });
    document.getElementById("ai-config-result").textContent = `ComfyUI 已保存：${result.id} · ${health.status}`;
    setStatus(health.status === "healthy" ? "ComfyUI 可达" : "ComfyUI 已保存，当前走本地回退");
  });
  document.getElementById("check-comfy").addEventListener("click", async () => {
    const list = await api(`/teams/${state.teamId}/resources?resource_type=comfyui_instance`);
    if (!list.length) {
      setStatus("先保存一个 ComfyUI 实例");
      return;
    }
    const health = await api(`/comfyui/instances/${list[0].id}/health-check`, { method: "POST" });
    document.getElementById("ai-config-result").textContent = `健康检查：${health.status} · ${health.data.health?.mode || ""}`;
    setStatus(health.status === "healthy" ? "ComfyUI 可达" : "ComfyUI 不可达，执行时回退本地");
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
    const tested = await api(`/workflows/${result.id}/test-run`, { method: "POST" });
    document.getElementById("ai-config-result").textContent = `Workflow 已解析并试跑：${tested.status} / ${tested.data.test_run?.mode || "fallback"}`;
    setStatus("Workflow 已试跑");
  });
}

async function renderMembers() {
  setShell("members");
  await ensureTeam();
  const members = await api(`/teams/${state.teamId}/members`);
  view.innerHTML = page(
    "Team",
    "成员与权限",
    "Owner / Admin 可以邀请已注册或未注册邮箱。未注册用户会拿到邀请令牌，到登录页接受邀请。",
    `
      <section class="surface">
        <table class="data-table">
          <thead><tr><th>成员</th><th>邮箱</th><th>角色</th></tr></thead>
          <tbody>
            ${members.map((member) => `<tr><td>${member.display_name}</td><td>${member.email}</td><td>${member.role}</td></tr>`).join("")}
          </tbody>
        </table>
      </section>
      <form id="member-form" class="surface">
        <h3>邀请成员</h3>
        <label>Email <input name="email" type="email" /></label>
        <label>角色
          <select name="role">
            <option value="producer">producer</option>
            <option value="artist">artist</option>
            <option value="animator">animator</option>
            <option value="reviewer">reviewer</option>
            <option value="viewer">viewer</option>
            <option value="admin">admin</option>
          </select>
        </label>
        <button class="primary" type="submit">邀请</button>
      </form>
      <div id="member-result" class="surface"></div>
    `,
  );
  document.getElementById("member-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/teams/${state.teamId}/members`, { method: "POST", body: JSON.stringify({ email: form.get("email"), role: form.get("role") }) });
    document.getElementById("member-result").textContent = result.invite_token
      ? `已邀请未注册用户 ${result.email}。邀请令牌：${result.invite_token}`
      : `已加入：${result.email} / ${result.role}`;
    setStatus("成员已邀请");
  });
}

async function renderReview() {
  setShell("review");
  await ensureProject();
  const [clips, comments] = await Promise.all([
    api(`/projects/${state.projectId}/resources?resource_type=video_clip`),
    api(`/projects/${state.projectId}/resources?resource_type=review_comment`),
  ]);
  const current = clips[0];
  view.innerHTML = page(
    "QC",
    "审核导出",
    "先看片段，打时间码批注，再出 QC 和导出包。",
    `
      <section class="surface">
        ${current ? `<video class="player" controls src="/resources/${current.id}/file"></video>` : `<div class="empty">还没有视频片段。先到分格页生成。</div>`}
        <form id="comment-form">
          <label>时间码（秒） <input name="timecode" type="number" value="0" /></label>
          <label>批注 <input name="content" value="检查口型" /></label>
          <button class="primary" type="submit">添加批注</button>
        </form>
        <ul>${comments.map((comment) => `<li>#${comment.id} ${comment.data.content || ""}</li>`).join("")}</ul>
      </section>
      <section class="surface"><div class="page-actions"><button class="primary" id="qc">创建 QC</button><button class="ghost" id="export">创建导出</button></div></section>
    `,
  );
  document.getElementById("qc").addEventListener("click", () =>
    api(`/projects/${state.projectId}/qc-reports`, { method: "POST", body: JSON.stringify({ data: { checks: { video_playable: true } } }) }).then(() => setStatus("QC 已创建")),
  );
  document.getElementById("export").addEventListener("click", () =>
    api(`/projects/${state.projectId}/exports`, { method: "POST", body: JSON.stringify({ data: { resolution: "1920x1080" } }) }).then(() => setStatus("导出已创建")),
  );
  document.getElementById("comment-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!current) return;
    const form = new FormData(event.currentTarget);
    await api("/review-comments", {
      method: "POST",
      body: JSON.stringify({
        object_type: "video_clip",
        object_id: current.id,
        category: "picture",
        content: `${form.get("timecode")}s ${form.get("content")}`,
        severity: "medium",
      }),
    });
    setStatus("批注已添加");
    await renderReview();
  });
}

async function renderDelivery() {
  setShell("delivery");
  await ensureProject();
  view.innerHTML = page(
    "Delivery",
    "质量交付",
    "审片包给客户看，冻结前会跑 preflight。",
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
    const result = await api(`/projects/${state.projectId}/review-packages`, { method: "POST", body: JSON.stringify({ data: { package_type: form.get("packageType") } }) });
    document.getElementById("delivery-result").textContent = `审片包已创建：${result.id}`;
  });
  document.getElementById("advanced-export-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api(`/exports/${form.get("exportId")}/advanced-format`, { method: "POST", body: JSON.stringify({ data: { format: form.get("format") } }) });
    document.getElementById("delivery-result").textContent = `高级导出已创建：${result.id}`;
  });
}

async function renderReports() {
  setShell("reports");
  await ensureProject();
  const [workItems, gates, jobs, errors, costs] = await Promise.all([
    api(`/projects/${state.projectId}/work-items`),
    api(`/projects/${state.projectId}/production-gates`),
    api(`/projects/${state.projectId}/ai-jobs`),
    api(`/projects/${state.projectId}/error-logs`),
    api(`/projects/${state.projectId}/costs`),
  ]);
  const succeededJobs = jobs.filter((job) => job.status === "succeeded").length;
  view.innerHTML = page(
    "Pulse",
    "报表看板",
    "生产计数、失败面和项目级成本。",
    `<section class="surface"><table class="data-table">
      <thead><tr><th>指标</th><th>数量</th><th>备注</th></tr></thead>
      <tbody>
        <tr><td>Work Items</td><td>${workItems.length}</td><td>开放生产任务</td></tr>
        <tr><td>Production Gates</td><td>${gates.length}</td><td>关卡</td></tr>
        <tr><td>AI Jobs</td><td>${jobs.length}</td><td>${succeededJobs} succeeded</td></tr>
        <tr><td>Error Logs</td><td>${errors.length}</td><td>需要处理的失败</td></tr>
        <tr><td>Estimated cost</td><td>${costs.estimated_cost} ${costs.currency}</td><td>${costs.job_count} jobs</td></tr>
      </tbody>
    </table></section>`,
  );
  setStatus("报表已加载");
}

async function renderCompliance() {
  setShell("compliance");
  await ensureProject();
  view.innerHTML = page(
    "Release",
    "合规下载",
    "下载链接带短时 token。冻结前会跑 preflight。",
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
    "私有化和训练入口。V1 只落配置对象。",
    `<section class="surface"><div class="page-actions"><button class="primary" id="private-deployment">私有化配置</button><button class="ghost" id="training">模型训练任务</button></div></section>`,
  );
  document.getElementById("private-deployment").addEventListener("click", () =>
    api(`/teams/${state.teamId}/private-deployments`, { method: "POST", body: JSON.stringify({ data: { deployment_mode: "single_tenant" } }) }).then(() => setStatus("私有化配置已创建")),
  );
  document.getElementById("training").addEventListener("click", () =>
    api(`/projects/${state.projectId}/model-training-jobs`, { method: "POST", body: JSON.stringify({ data: { training_type: "character_lora" } }) }).then(() => setStatus("训练任务已创建")),
  );
}

async function renderOps() {
  setShell("ops");
  await ensureProject();
  const [jobs, health, queue] = await Promise.all([
    api(`/projects/${state.projectId}/ai-jobs`),
    api("/health"),
    api("/ops/queue"),
  ]);
  view.innerHTML = page(
    "Runtime",
    "运维 / Worker",
    "多机 Worker 抢同一条数据库队列。本机可跑后台线程，其他机器执行 mangedong worker。",
    `
      <section class="surface">
        <div class="metric-row">
          <div class="metric"><b>${jobs.length}</b><span>AI Jobs</span></div>
          <div class="metric"><b>${health.worker}</b><span>Worker</span></div>
          <div class="metric"><b>${health.queue || "database"}</b><span>队列</span></div>
          <div class="metric"><b>${(queue.workers || []).length}</b><span>在跑机器</span></div>
        </div>
        <p class="muted">worker_id: ${health.worker_id || "—"} · lease ${health.lease_ttl_seconds || 45}s</p>
        <p></p>
        <button class="primary" id="run-pending">运行 pending jobs</button>
        <button class="ghost" id="worker-tick">立即领取队列</button>
        ${
          jobs.length
            ? `<table class="data-table"><thead><tr><th>ID</th><th>类型</th><th>状态</th><th></th></tr></thead><tbody>${jobs
                .map(
                  (job) => `<tr><td>#${job.id}</td><td>${job.job_type}</td><td>${job.status}</td><td>
                    <button class="ghost" data-run="${job.id}">运行</button>
                    <button class="ghost" data-retry="${job.id}">重试</button>
                    <button class="ghost" data-cancel="${job.id}">取消</button>
                  </td></tr>`,
                )
                .join("")}</tbody></table>`
            : `<div class="empty">还没有任务。</div>`
        }
      </section>
    `,
  );
  document.getElementById("run-pending").addEventListener("click", () =>
    api(`/projects/${state.projectId}/ai-jobs/run-pending`, { method: "POST" }).then((items) => setStatus(`已处理 ${items.length} 个任务`)),
  );
  document.getElementById("worker-tick").addEventListener("click", () =>
    api("/ops/worker/tick", { method: "POST" }).then((items) => {
      setStatus(`领取并处理 ${items.length} 个 queued 任务`);
      renderOps();
    }),
  );
  document.querySelectorAll("[data-run]").forEach((button) => button.addEventListener("click", () => api(`/ai-jobs/${button.dataset.run}/run`, { method: "POST" }).then(() => setStatus("任务已运行"))));
  document.querySelectorAll("[data-retry]").forEach((button) => button.addEventListener("click", () => api(`/ai-jobs/${button.dataset.retry}/retry`, { method: "POST" }).then(() => setStatus("任务已重试"))));
  document.querySelectorAll("[data-cancel]").forEach((button) => button.addEventListener("click", () => api(`/ai-jobs/${button.dataset.cancel}/cancel`, { method: "POST" }).then(() => setStatus("任务已取消"))));
}

async function renderNotifications() {
  setShell("notifications");
  await ensureProject();
  const [jobs, errors] = await Promise.all([api(`/projects/${state.projectId}/ai-jobs`), api(`/projects/${state.projectId}/error-logs`)]);
  const failedJobs = jobs.filter((job) => ["failed", "cancelled"].includes(job.status));
  view.innerHTML = page(
    "Inbox",
    "通知中心",
    "失败任务和错误日志堆在这里。",
    `<section class="surface"><table class="data-table"><thead><tr><th>类型</th><th>计数</th></tr></thead>
      <tbody>
        <tr><td>任务通知</td><td><span class="pill">${jobs.length} jobs</span> <span class="pill hot">${failedJobs.length} attention</span></td></tr>
        <tr><td>错误通知</td><td><span class="pill">${errors.length} logs</span></td></tr>
      </tbody></table>
      <h3>最近状态</h3>
      <ul>${state.statusHistory.map((entry) => `<li>${entry.at} - ${entry.message}</li>`).join("") || "<li class='muted'>还没有状态</li>"}</ul>
    </section>`,
  );
  setStatus("通知中心已加载");
}

function renderHelp() {
  setShell("help");
  view.innerHTML = page(
    "Manual",
    "帮助与快捷键",
    "键盘在空白处生效。输入框里打字不会被抢走。",
    `<div class="split">
      <article class="surface">
        <h3>快捷键</h3>
        <p><span class="kbd">d</span> 总览</p>
        <p><span class="kbd">i</span> 导入</p>
        <p><span class="kbd">c</span> 上色</p>
        <p><span class="kbd">t</span> 镜头</p>
        <p><span class="kbd">m</span> 模型配置</p>
        <p><span class="kbd">Ctrl</span> <span class="kbd">K</span> 命令盘</p>
      </article>
      <article class="surface">
        <h3>推荐流程</h3>
        <ol>
          <li>登录后打开模型配置，填 API Key 和 ComfyUI 地址。</li>
          <li>总览里创建或选中剧集。</li>
          <li>导入漫画，进入分格工作台跑 OCR / 上色 / 视频。</li>
          <li>镜头和音频完成后，审片、导出、冻结。</li>
        </ol>
      </article>
    </div>`,
  );
  setStatus("帮助已加载");
}

function renderSettings() {
  setShell("settings");
  view.innerHTML = page(
    "Session",
    "设置",
    "团队 SMTP、S3 和队列在这里配。模型 Key 仍在「模型配置」。",
    `<form id="smtp-form" class="surface">
      <h3>SMTP</h3>
      <p class="muted">每个团队自己的发信配置。邀请和重置密码会先走这里，失败则回退显示令牌。</p>
      <label>Host <input name="host" placeholder="smtp.example.com" /></label>
      <label>Port <input name="port" type="number" value="587" /></label>
      <label>Username <input name="username" /></label>
      <label>Password <input name="password" type="password" autocomplete="off" /></label>
      <label>From <input name="fromAddress" placeholder="studio@example.com" /></label>
      <label>Public URL <input name="publicBaseUrl" placeholder="https://studio.example.com" /></label>
      <label><input name="useTls" type="checkbox" checked /> STARTTLS</label>
      <label><input name="useSsl" type="checkbox" /> SMTPS (465)</label>
      <button class="primary" type="submit">保存 SMTP</button>
      <button class="ghost" type="button" id="test-smtp">测试连接</button>
    </form>
    <form id="s3-form" class="surface">
      <h3>对象存储 S3</h3>
      <p class="muted">兼容 AWS / MinIO / R2。对象键按 teams/{team_id}/projects/{project_id}/ 隔离。</p>
      <label>Backend
        <select name="backend">
          <option value="s3">s3</option>
          <option value="local">local</option>
          <option value="memory">memory</option>
        </select>
      </label>
      <label>Endpoint <input name="endpoint" placeholder="https://s3.example.com" /></label>
      <label>Bucket <input name="bucket" /></label>
      <label>Region <input name="region" value="us-east-1" /></label>
      <label>Access Key <input name="accessKey" /></label>
      <label>Secret Key <input name="secretKey" type="password" autocomplete="off" /></label>
      <label>Prefix <input name="prefix" placeholder="mangedong" /></label>
      <label><input name="pathStyle" type="checkbox" checked /> Path-style（MinIO / 内网）</label>
      <button class="primary" type="submit">保存 S3</button>
      <button class="ghost" type="button" id="test-s3">测试写入</button>
    </form>
    <form id="queue-form" class="surface">
      <h3>多机队列</h3>
      <label>团队最大并行 <input name="maxRunning" type="number" min="1" value="8" /></label>
      <label>Lease 秒 <input name="leaseTtl" type="number" min="5" value="45" /></label>
      <button class="ghost" type="submit">保存队列限额</button>
    </form>
    <form id="context-form" class="surface" data-testid="context-form">
      <label>Token <textarea name="token">${state.token}</textarea></label>
      <label>Team ID <input name="teamId" type="number" value="${state.teamId || ""}" /></label>
      <label>Project ID <input name="projectId" type="number" value="${state.projectId || ""}" /></label>
      <button class="primary" type="submit">保存上下文</button>
    </form>
    <div id="settings-result" class="surface muted"></div>`,
  );
  document.getElementById("smtp-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await ensureTeam();
    const form = new FormData(event.currentTarget);
    const result = await api(`/teams/${state.teamId}/smtp`, {
      method: "PUT",
      body: JSON.stringify({
        host: form.get("host"),
        port: Number(form.get("port") || 587),
        username: form.get("username"),
        password: form.get("password"),
        from_address: form.get("fromAddress"),
        public_base_url: form.get("publicBaseUrl"),
        use_tls: form.get("useTls") === "on",
        use_ssl: form.get("useSsl") === "on",
      }),
    });
    document.getElementById("settings-result").textContent = `SMTP 已保存：${result.data.host}`;
  });
  document.getElementById("test-smtp").addEventListener("click", async () => {
    await ensureTeam();
    const result = await api(`/teams/${state.teamId}/smtp/test`, { method: "POST" });
    document.getElementById("settings-result").textContent = `SMTP ${result.mode}: ${result.error || "ok"}`;
  });
  document.getElementById("s3-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await ensureTeam();
    const form = new FormData(event.currentTarget);
    const result = await api(`/teams/${state.teamId}/storage`, {
      method: "PUT",
      body: JSON.stringify({
        backend: form.get("backend"),
        endpoint: form.get("endpoint"),
        bucket: form.get("bucket"),
        region: form.get("region"),
        access_key: form.get("accessKey"),
        secret_key: form.get("secretKey"),
        prefix: form.get("prefix"),
        use_path_style: form.get("pathStyle") === "on",
      }),
    });
    document.getElementById("settings-result").textContent = `存储已保存：${result.data.backend} ${result.data.bucket || ""}`;
  });
  document.getElementById("test-s3").addEventListener("click", async () => {
    await ensureTeam();
    const result = await api(`/teams/${state.teamId}/storage/test`, { method: "POST" });
    document.getElementById("settings-result").textContent = `S3 ${result.mode}: ${result.error || result.backend}`;
  });
  document.getElementById("queue-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await ensureTeam();
    const form = new FormData(event.currentTarget);
    const result = await api(`/teams/${state.teamId}/queue`, {
      method: "PUT",
      body: JSON.stringify({ max_running: Number(form.get("maxRunning") || 8), lease_ttl_seconds: Number(form.get("leaseTtl") || 45) }),
    });
    document.getElementById("settings-result").textContent = `队列限额：${result.data.max_running}`;
  });
  if (state.teamId) {
    Promise.all([
      api(`/teams/${state.teamId}/smtp`).catch(() => null),
      api(`/teams/${state.teamId}/storage`).catch(() => null),
      api(`/teams/${state.teamId}/queue`).catch(() => null),
    ]).then(([smtp, storage, queue]) => {
      const smtpForm = document.getElementById("smtp-form");
      const s3Form = document.getElementById("s3-form");
      const queueForm = document.getElementById("queue-form");
      if (smtp?.data && smtpForm) {
        smtpForm.host.value = smtp.data.host || "";
        smtpForm.port.value = smtp.data.port || 587;
        smtpForm.username.value = smtp.data.username || "";
        smtpForm.fromAddress.value = smtp.data.from_address || "";
        smtpForm.publicBaseUrl.value = smtp.data.public_base_url || "";
        smtpForm.useTls.checked = smtp.data.use_tls !== false;
        smtpForm.useSsl.checked = Boolean(smtp.data.use_ssl);
      }
      if (storage?.data && s3Form) {
        s3Form.backend.value = storage.data.backend || "s3";
        s3Form.endpoint.value = storage.data.endpoint || "";
        s3Form.bucket.value = storage.data.bucket || "";
        s3Form.region.value = storage.data.region || "us-east-1";
        s3Form.accessKey.value = storage.data.access_key || "";
        s3Form.prefix.value = storage.data.prefix || "";
        s3Form.pathStyle.checked = storage.data.use_path_style !== false;
      }
      if (queue?.data && queueForm) {
        queueForm.maxRunning.value = queue.data.max_running || 8;
        queueForm.leaseTtl.value = queue.data.lease_ttl_seconds || 45;
      }
    });
  }
  document.getElementById("context-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    state.token = String(form.get("token") || "");
    state.teamId = Number(form.get("teamId") || 0);
    state.projectId = Number(form.get("projectId") || 0);
    persistSession();
    setShell("settings");
    setStatus("上下文已保存");
  });
}

if (state.token) persistSession();
renderRoute(state.token ? "dashboard" : "auth");
