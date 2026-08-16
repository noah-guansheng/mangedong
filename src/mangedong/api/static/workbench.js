const state = {
  token: localStorage.getItem("md_token") || "",
  teamId: Number(localStorage.getItem("md_team_id") || 0),
  projectId: Number(localStorage.getItem("md_project_id") || 0),
};

const view = document.getElementById("view");
const statusBox = document.getElementById("status");

document.querySelectorAll("[data-route]").forEach((button) => {
  button.addEventListener("click", () => renderRoute(button.dataset.route));
});

function setStatus(message) {
  statusBox.textContent = message;
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
  const routes = {
    auth: renderAuth,
    dashboard: renderDashboard,
    production: renderProduction,
    import: renderImport,
    color: renderColor,
    timeline: renderTimeline,
    audio: renderAudio,
    ai: renderAI,
    review: renderReview,
    p2: renderP2,
    ops: renderOps,
  };
  return (routes[route] || renderDashboard)();
}

function renderAuth() {
  view.innerHTML = `
    <h2>登录 / 注册</h2>
    <form id="auth-form">
      <label>Email <input name="email" type="email" value="owner@example.com" /></label>
      <label>Password <input name="password" type="password" value="password123" /></label>
      <label>Display name <input name="displayName" value="Owner" /></label>
      <button class="primary" type="submit">注册并登录</button>
    </form>
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
  view.innerHTML = `<h2>Dashboard</h2><div id="dashboard-cards" class="grid"></div>`;
  const teams = await api("/teams");
  if (teams.length === 0) {
    const team = await api("/teams", { method: "POST", body: JSON.stringify({ name: "Default Studio" }) });
    state.teamId = team.id;
  } else {
    state.teamId = teams[0].id;
  }
  localStorage.setItem("md_team_id", state.teamId);
  const projects = await api(`/projects?team_id=${state.teamId}`);
  document.getElementById("dashboard-cards").innerHTML = `
    <article class="card"><h3>团队</h3><p>${state.teamId}</p></article>
    <article class="card"><h3>项目数</h3><p>${projects.length}</p></article>
    <article class="card"><button class="primary" id="create-project">创建默认项目</button></article>
  `;
  document.getElementById("create-project").addEventListener("click", createDefaultProject);
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
  await ensureProject();
  const [assets, chapters, workItems, gates, jobs] = await Promise.all([
    api(`/projects/${state.projectId}/assets`),
    api(`/projects/${state.projectId}/chapters`),
    api(`/projects/${state.projectId}/work-items`),
    api(`/projects/${state.projectId}/production-gates`),
    api(`/projects/${state.projectId}/ai-jobs`),
  ]);
  view.innerHTML = `
    <h2>生产工作台</h2>
    <section class="grid">
      <div class="card"><h3>素材</h3><p>${assets.length}</p></div>
      <div class="card"><h3>章节</h3><p>${chapters.length}</p></div>
      <div class="card"><h3>Work Items</h3><p>${workItems.length}</p></div>
      <div class="card"><h3>Gates</h3><p>${gates.length}</p></div>
      <div class="card"><h3>AI Jobs</h3><p>${jobs.length}</p></div>
    </section>
  `;
  setStatus("生产工作台已加载");
}

async function renderImport() {
  await ensureProject();
  view.innerHTML = `
    <h2>漫画导入</h2>
    <form id="manga-import-form" data-testid="manga-import-form">
      <label>章节名称 <input name="chapterTitle" value="Chapter 1" /></label>
      <label>漫画图片/CBZ/ZIP <input name="file" type="file" /></label>
      <button class="primary" type="submit">导入漫画</button>
    </form>
    <form id="pdf-import-form" data-testid="pdf-import-form">
      <label>PDF 章节名称 <input name="chapterTitle" value="PDF Chapter" /></label>
      <label>页数 <input name="pageCount" type="number" min="1" value="1" /></label>
      <label>PDF 文件 <input name="file" type="file" /></label>
      <button class="primary" type="submit">导入 PDF</button>
    </form>
    <div id="import-result" class="card"></div>
  `;
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
  await ensureProject();
  view.innerHTML = `
    <h2>上色生产</h2>
    <form id="colorize-form" data-testid="colorize-form">
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
    <form id="batch-color-form" data-testid="batch-color-form">
      <label>范围 <input name="scope" value="project" /></label>
      <button class="primary" type="submit">批量上色</button>
    </form>
    <div id="color-result" class="card"></div>
  `;
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
  await ensureProject();
  view.innerHTML = `
    <h2>Shot / Timeline</h2>
    <form id="shot-form" data-testid="shot-form">
      <label>Shot 标题 <input name="title" value="Shot 001" /></label>
      <label>时长 <input name="duration" type="number" value="3" /></label>
      <button class="primary" type="submit">创建 Shot</button>
    </form>
    <form id="timeline-form" data-testid="timeline-form">
      <label>Timeline 名称 <input name="name" value="Main Timeline" /></label>
      <button class="primary" type="submit">创建 Timeline</button>
    </form>
    <div id="timeline-result" class="card"></div>
  `;
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
  await ensureProject();
  view.innerHTML = `
    <h2>音频字幕</h2>
    <form id="dialogue-form" data-testid="dialogue-form">
      <label>Shot ID <input name="shotId" type="number" min="1" /></label>
      <label>台词 <input name="text" value="开始吧" /></label>
      <button class="primary" type="submit">创建台词</button>
    </form>
    <form id="music-form" data-testid="music-form">
      <label>BGM URI <input name="assetUri" value="local://bgm.wav" /></label>
      <button class="primary" type="submit">添加 BGM</button>
    </form>
    <div id="audio-result" class="card"></div>
  `;
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

async function renderAI() {
  await ensureProject();
  view.innerHTML = `
    <h2>AI / ComfyUI</h2>
    <section class="grid">
      <button class="primary" id="mock-provider">创建 Mock Provider</button>
      <button class="primary" id="mock-comfy">配置本地 ComfyUI</button>
      <button class="primary" id="mock-workflow">创建 Workflow</button>
    </section>
  `;
  document.getElementById("mock-provider").addEventListener("click", () =>
    api(`/teams/${state.teamId}/ai-providers`, {
      method: "POST",
      body: JSON.stringify({ name: "Mock Provider", provider_type: "third_party_api", capabilities: ["video"] }),
    }).then(() => setStatus("Mock Provider 已创建")),
  );
  document.getElementById("mock-comfy").addEventListener("click", () =>
    api(`/teams/${state.teamId}/comfyui/instances`, {
      method: "POST",
      body: JSON.stringify({ name: "Local ComfyUI", base_url: "http://127.0.0.1:8188", auth_type: "none" }),
    }).then(() => setStatus("ComfyUI 配置已创建")),
  );
  document.getElementById("mock-workflow").addEventListener("click", () =>
    api(`/projects/${state.projectId}/workflows`, {
      method: "POST",
      body: JSON.stringify({ name: "Mock Workflow", workflow_type: "image_to_video", workflow_json: { "1": { class_type: "Node" } } }),
    }).then(() => setStatus("Workflow 已创建")),
  );
}

async function renderReview() {
  await ensureProject();
  view.innerHTML = `
    <h2>审核导出</h2>
    <section class="grid">
      <button class="primary" id="qc">创建 QC</button>
      <button class="primary" id="export">创建导出</button>
    </section>
  `;
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

async function renderP2() {
  await ensureProject();
  view.innerHTML = `
    <h2>P2 管理</h2>
    <section class="grid">
      <button class="primary" id="private-deployment">私有化配置</button>
      <button class="primary" id="training">模型训练任务</button>
    </section>
  `;
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
  await ensureProject();
  const jobs = await api(`/projects/${state.projectId}/ai-jobs`);
  view.innerHTML = `
    <h2>运维 / Worker</h2>
    <section class="grid">
      <div class="card"><h3>AI Jobs</h3><p>${jobs.length}</p></div>
      <button class="primary" id="run-pending">运行 pending jobs</button>
    </section>
  `;
  document.getElementById("run-pending").addEventListener("click", () =>
    api(`/projects/${state.projectId}/ai-jobs/run-pending`, { method: "POST" }).then((jobs) => setStatus(`已处理 ${jobs.length} 个任务`)),
  );
}

renderRoute(state.token ? "dashboard" : "auth");
