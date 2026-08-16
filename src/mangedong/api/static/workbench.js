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
