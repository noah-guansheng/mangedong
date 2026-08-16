# mangedong

`mangedong` 是一个从黑白漫画生成动漫风格视频的最小可运行项目骨架。当前版本先打通主链路：

1. 导入漫画页：支持单张图片、图片目录、CBZ/ZIP 漫画包。
2. 上色：内置确定性的动漫风格算法上色器，后续可替换为本地模型或 API。
3. 动画：用 Ken Burns 镜头运动和轻微明暗变化生成帧序列。
4. 导出：将帧序列编码为 H.264 MP4，并输出 manifest 记录产物。

## 一键启动工作台

```bash
chmod +x start.sh
./start.sh
```

浏览器打开 http://127.0.0.1:8000/app 。脚本会创建 `.venv`、安装依赖并启动 API（文件库 SQLite 下自动带内嵌 Worker）。Windows 用 `start.cmd`。已安装过的环境也可以：

```bash
python3 -m mangedong.cli serve --host 0.0.0.0 --port 8000
```

可选把 `.env.example` 复制为 `.env`，填入 Token Plan 席位 Key 等变量。

## 安装

```bash
python3 -m pip install -e ".[dev]"
```

## 快速运行

```bash
python3 -m mangedong.cli run \
  --input path/to/page.png \
  --output runs/demo/out.mp4 \
  --workdir runs/demo \
  --duration 4 \
  --fps 24 \
  --palette sunset
```

常用参数：

- `--input`：图片、图片目录或 `.cbz` / `.zip` 漫画包。
- `--output`：导出的 MP4 路径。
- `--workdir`：上色图、帧序列和 `manifest.json` 的输出目录。
- `--palette`：`sunset`、`cel`、`pastel`。
- `--no-keep-frames`：导出后删除中间帧。

## 批量链路

将一个目录里的每张漫画页分别转换成一个 MP4：

```bash
python3 -m mangedong.cli batch path/to/pages runs/batch-videos --duration 3 --fps 24
```

## 依赖诊断

```bash
python3 -m mangedong.cli doctor
```

## 测试

```bash
python3 -m pytest
```

## Web SaaS API

启动后端 API：

```bash
python3 -m uvicorn "mangedong.api.app:create_app" --factory --reload
```

默认使用本地 SQLite 数据库 `mangedong.db`。可通过环境变量覆盖：

```bash
MANGEDONG_DATABASE_URL="sqlite:///./mangedong.db"
MANGEDONG_SECRET_KEY="change-me"
MANGEDONG_STORAGE_DIR="./mangedong_storage"
```

完整前端工作台入口：

```bash
http://localhost:8000/app
```

工作台是浅色朱红的生产界面：顶栏项目上下文、左侧生产/交付/系统分组。

第三方 **API Key** 和 **ComfyUI 地址** 只在顶栏「配置模型」或「模型配置」页填写。ComfyUI 支持局域网 `8188` 加上内网穿透公网 URL。

千问 **Token Plan 团队版** 按官方要求只给 AI 编程/智能体工具交互使用。工作台「制片助手」模拟 Cursor / Qwen Code / Claude Code / Cline / OpenClaw 的协议和 User-Agent：

- OpenAI 兼容：`https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`
- Anthropic 兼容（Claude Code）：`https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic`
- API Key 必须以 `sk-sp-` 开头，不可与 `sk-ws-` / dashscope 按量地址混用
- 图像 Skill：`/api/v1/services/aigc/multimodal-generation/generation`
- 视频 Skill：异步 `video-synthesis`（HappyHorse）
- 不会把席位 Key 接到 OCR/上色/出片等后台批量任务上

环境变量（可被团队配置覆盖）：

```bash
MANGEDONG_TOKENPLAN_API_KEY=sk-sp-...
MANGEDONG_TOKENPLAN_TOOL=qwen-code
MANGEDONG_TOKENPLAN_TEXT_MODEL=qwen3.6-plus
MANGEDONG_TOKENPLAN_IMAGE_MODEL=qwen-image-2.0
MANGEDONG_TOKENPLAN_VIDEO_MODEL=happyhorse-1.1-t2v
```

团队基础设施在「设置」页配置：

- SMTP：邀请和重置密码发信（每个团队一份）
- S3 兼容存储：AWS / MinIO / R2，对象键按 `teams/{team_id}/projects/{project_id}/` 隔离
- 多机队列：共享数据库 lease。API 进程可内嵌 worker；其他机器跑 `mangedong worker` 或 `python3 -m mangedong.api.worker_main`

环境变量（全平台默认，可被团队配置覆盖）：

```bash
MANGEDONG_SMTP_HOST=
MANGEDONG_SMTP_PORT=587
MANGEDONG_SMTP_USER=
MANGEDONG_SMTP_PASSWORD=
MANGEDONG_SMTP_FROM=
MANGEDONG_PUBLIC_URL=http://127.0.0.1:8000
MANGEDONG_S3_ENDPOINT=
MANGEDONG_S3_BUCKET=
MANGEDONG_S3_REGION=us-east-1
MANGEDONG_S3_ACCESS_KEY=
MANGEDONG_S3_SECRET_KEY=
MANGEDONG_WORKER_ID=
MANGEDONG_LEASE_TTL=45
```

多机部署时，API 和所有 Worker 必须指向同一数据库。SQLite 只适合单机；跨机器请用 PostgreSQL：

```bash
python3 -m pip install -e ".[postgres]"
export MANGEDONG_DATABASE_URL="postgresql+psycopg://user:pass@db-host/mangedong"
# API 节点可关掉内嵌 worker，改由独立机器消费队列
export MANGEDONG_WORKER=0
python3 -m uvicorn "mangedong.api.app:create_app" --factory --host 0.0.0.0 --port 8000

# 其他机器
mangedong worker --database-url "$MANGEDONG_DATABASE_URL"
# 或
python3 -m mangedong.api.worker_main
```

ComfyUI 先在局域网 `8188` 启动，再做内网穿透；把穿透后的公网 URL 填到「内网穿透 URL」。健康检查会先探穿透地址。

当前 SPA 模块按真人工作流拆分：

- 登录工作室
- 总览
- 导入
- 分格工作台（OCR / 分析 / 上色 / 视频）
- 上色（含参考和角色）
- 镜头
- 音频
- 审片
- 导出
- 模型配置
- 成员
- 任务
- 设置

当前已实现的第一轮 API：

- `GET /health`
- `GET /app`
- `GET /static/workbench.js`
- `GET /static/styles.css`
- `GET /ui/login`
- `GET /ui/dashboard`
- `GET /ui/projects?team_id=...`
- `GET /ui/projects/{project_id}/production`
- `GET /ui/projects/{project_id}/ai-workflows`
- `GET /ui/projects/{project_id}/review-export`
- `GET /ui/projects/{project_id}/color-review`
- `GET /ui/projects/{project_id}/clip-compare`
- `GET /ui/projects/{project_id}/client-review`
- `GET /ui/projects/{project_id}/errors`
- `GET /ui/projects/{project_id}/p2-admin`
- `GET /ui/projects/{project_id}/ops`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /teams`
- `GET /teams`
- `POST /teams/{team_id}/members`
- `GET /teams/{team_id}/members`
- `PUT /teams/{team_id}/smtp`
- `GET /teams/{team_id}/smtp`
- `POST /teams/{team_id}/smtp/test`
- `PUT /teams/{team_id}/storage`
- `GET /teams/{team_id}/storage`
- `POST /teams/{team_id}/storage/test`
- `PUT /teams/{team_id}/queue`
- `GET /teams/{team_id}/queue`
- `GET /ops/queue`
- `POST /projects`
- `GET /projects?team_id=...`
- `GET /projects/{project_id}`
- `POST /projects/{project_id}/assets`
- `GET /projects/{project_id}/assets`
- `POST /projects/{project_id}/uploads`
- `POST /assets/{asset_id}/download-token`
- `GET /downloads/{download_id}`
- `POST /projects/{project_id}/imports/manga`
- `POST /projects/{project_id}/imports/pdf`
- `POST /projects/{project_id}/chapters`
- `GET /projects/{project_id}/chapters`
- `POST /chapters/{chapter_id}/pages`
- `GET /chapters/{chapter_id}/pages`
- `POST /pages/{page_id}/panels`
- `GET /pages/{page_id}/panels`
- `PATCH /panels/{panel_id}/manual-correction`
- `POST /projects/{project_id}/work-items`
- `GET /projects/{project_id}/work-items`
- `POST /projects/{project_id}/production-gates`
- `GET /projects/{project_id}/production-gates`
- `POST /production-gates/{gate_id}/approve`
- `POST /projects/{project_id}/ai-jobs`
- `GET /projects/{project_id}/ai-jobs`
- `POST /ai-jobs/{job_id}/run`
- `POST /ai-jobs/{job_id}/retry`
- `POST /ai-jobs/{job_id}/cancel`
- `POST /projects/{project_id}/ai-jobs/run-pending`
- `POST /teams/{team_id}/ai-providers`
- `GET /token-plan/catalog`
- `PUT /teams/{team_id}/token-plan`
- `GET /teams/{team_id}/token-plan`
- `POST /teams/{team_id}/token-plan/test`
- `POST /projects/{project_id}/studio-agent/turn`
- `POST /projects/{project_id}/studio-agent/skill`
- `GET /teams/{team_id}/ai-providers`
- `POST /teams/{team_id}/comfyui/instances`
- `POST /comfyui/instances/{instance_id}/health-check`
- `POST /projects/{project_id}/workflows`
- `PATCH /workflows/{workflow_id}/parameters`
- `POST /workflows/{workflow_id}/test-run`
- `GET /projects/{project_id}/workflows`
- `POST /projects/{project_id}/storage/presign`
- `POST /projects/{project_id}/references`
- `POST /projects/{project_id}/characters`
- `POST /projects/{project_id}/color-profiles`
- `POST /projects/{project_id}/color-strategies/apply`
- `POST /panels/{panel_id}/ocr`
- `POST /panels/{panel_id}/analyze`
- `POST /panels/{panel_id}/colorize`
- `POST /colorizations/{colorization_id}/local-corrections`
- `POST /colorizations/{colorization_id}/compare`
- `POST /projects/{project_id}/batch-colorize`
- `POST /panels/{panel_id}/generate-video`
- `POST /video-clips/{clip_id}/compare`
- `POST /projects/{project_id}/shots`
- `POST /shots/{shot_id}/generate-animatic`
- `POST /projects/{project_id}/timelines`
- `POST /timelines/{timeline_id}/items`
- `POST /shots/{shot_id}/dialogue-lines`
- `POST /dialogue-lines/{dialogue_line_id}/voice`
- `POST /dialogue-lines/{dialogue_line_id}/subtitle`
- `POST /dialogue-lines/{dialogue_line_id}/translations`
- `POST /projects/{project_id}/music-cues`
- `POST /projects/{project_id}/audio-mixes`
- `POST /projects/{project_id}/collaboration/sessions`
- `POST /projects/{project_id}/model-training-jobs`
- `POST /review-comments`
- `POST /projects/{project_id}/review-packages`
- `POST /review-packages/{review_package_id}/revision-requests`
- `POST /review-packages/{review_package_id}/acceptance-records`
- `POST /projects/{project_id}/qc-reports`
- `POST /projects/{project_id}/error-logs`
- `GET /projects/{project_id}/error-logs`
- `POST /projects/{project_id}/exports`
- `POST /exports/{export_id}/preflight`
- `POST /exports/{export_id}/freeze`
- `POST /exports/{export_id}/advanced-format`
- `POST /teams/{team_id}/private-deployments`
- `POST /teams/{team_id}/comfyui/cloud-pools`
- `PATCH /workflows/{workflow_id}/canvas`
- `POST /timelines/{timeline_id}/tracks`
- `POST /timelines/{timeline_id}/keyframes`

## 后续扩展方向

- 将 `AlgorithmicColorizer` 替换为漫画上色模型或第三方 API 适配器。
- 在动画阶段接入图生视频模型，并保留当前帧导出作为降级方案。
- 为 Web 预览、任务队列、字幕、音轨、角色色板和批量章节处理增加独立模块。

## 产品规划

- [Web SaaS 工作台 PRD 初稿](docs/PRD.md)
- [第一轮开发拆解](docs/DEVELOPMENT_PLAN.md)
