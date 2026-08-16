# 测试报告

## 测试时间

- 运行命令：`python3 -m pytest`
- 测试范围：CLI 管道、Web SaaS API、Web 工作台页面
- 测试结果：26 passed

## 自动化测试覆盖

### 1. CLI / 管道测试

文件：`tests/test_pipeline.py`

覆盖内容：

- 单张漫画页端到端导出 MP4
- 生成 manifest
- 生成上色图
- 生成动画帧
- 验证首尾帧存在差异，避免退化为静态视频
- 图片目录导入排序
- CBZ 漫画包导入排序

### 2. Web SaaS API 测试

文件：`tests/test_api.py`

覆盖内容：

- 用户注册
- 用户登录
- Bearer token 鉴权
- `/auth/me`
- 团队创建
- 团队成员邀请
- 非管理角色禁止邀请成员
- Project Brief 项目创建
- viewer 禁止创建项目
- owner 可以创建项目
- 项目列表
- 素材库元数据创建/list
- 章节创建/list
- 页面创建/list
- 分格创建/list
- WorkItem 创建/list
- ProductionGate 创建/审批/list
- AIJob 创建/list

### 3. Web 工作台页面自动化测试

文件：`tests/test_pages.py`

覆盖页面：

- `GET /ui/login`
- `GET /ui/dashboard`
- `GET /ui/projects?team_id=...`
- `GET /ui/projects/{project_id}/production`

验证内容：

- 登录页渲染工作台入口和登录表单
- Dashboard 渲染团队空间
- 项目列表页渲染项目和生产工作台入口
- 项目生产页渲染 Project Brief 信息
- 项目生产页渲染素材库区域
- 项目生产页渲染章节区域
- 项目生产页渲染 Work Items 区域
- 项目生产页渲染 Production Gates 区域
- 项目生产页渲染 AI Jobs 区域
- `/app` SPA 壳渲染：顶栏、分组导航、命令盘、模型配置入口
- 前端脚本包含分格工作台、成员页、项目结构树
- 真人闭环测试：导入、预览、成员改角色、成本、artist/animator 上色
- `/static/styles.css` 不为 Inter / indigo 默认皮肤
- 前端脚本包含 AI Provider API Key 与 ComfyUI 地址表单，并标明「就在这一页」
- 前端脚本包含 Dashboard、AI、P2 路由
- 前端脚本包含漫画导入、上色生产、Shot / Timeline、音频字幕路由
- 前端脚本包含对应生产表单：导入、上色、Shot、Dialogue
- 前端脚本包含资源浏览、质量交付、设置/上下文切换路由
- Dashboard 支持项目选择入口
- 前端脚本包含端到端链路向导和默认生产任务创建入口
- 前端脚本包含报表看板和合规下载入口
- 前端脚本包含下载 token 与 export preflight/freeze 表单
- 前端脚本包含通知中心、帮助/快捷键页面和状态历史
- 前端脚本包含键盘快捷键路由
- 前端脚本包含 AI Provider API Key 配置表单
- 前端脚本包含 ComfyUI 地址、Token、Header、并发配置表单
- 前端脚本包含 Workflow JSON 上传解析表单
- 前端脚本包含忘记密码、接受邀请、立项向导、ComfyUI 健康检查、Worker tick、审片播放器
- 前端脚本包含 SMTP / S3 / 多机队列表单，以及 ComfyUI 内网穿透 URL

### 8. V1 收口测试

文件：`tests/test_completion.py`

覆盖内容：

- 邀请未注册用户并返回 invite_token
- 接受邀请后用新密码登录
- 忘记密码 / 重置密码
- PATCH 项目名称和状态
- `/ops/worker/tick` 领取 queued 任务并成功
- 内存 SQLite 下 worker 为 disabled
- API Key 加密 roundtrip
- ComfyUI 健康检查在不可达时标记 fallback
- 上色 PNG 和视频 MP4 可通过 `/resources/{id}/file` 读取
- Animatic 写出真实本地 MP4

### 4. PRD P0 完整链路测试

文件：`tests/test_prd_flow.py`

覆盖内容：

- AI Provider 创建
- 远程 ComfyUI 实例配置
- ComfyUI 健康检查
- workflow 上传和解析
- workflow test-run
- 参考图创建
- 角色资源创建
- 漫画图片上传和导入
- 章节、页面、分格自动创建
- OCR 占位任务
- AI 分析占位任务
- 参考上色任务，并生成本地 PNG 文件
- 批量上色任务
- 单分格视频生成，并生成本地 MP4 文件
- Shot 创建
- Animatic 生成
- Timeline 创建
- TimelineItem 添加
- DialogueLine 创建
- VoiceLine 生成，并生成本地 WAV 文件
- SubtitleCue 创建，并生成本地 SRT 文件
- MusicCue 创建
- AudioMix 创建，并生成本地 WAV 文件
- ReviewComment 创建
- QCReport 创建
- Export 创建
- Export preflight
- Export freeze，并生成本地 ZIP 交付包
- AI Workflow Center 页面渲染
- Review / Export 页面渲染

### 5. 增强项测试

文件：`tests/test_enhancements.py`

覆盖内容：

- 本地存储意图
- Workflow Published Parameters 编辑
- 局部修正，并生成本地 PNG
- 上色版本对比
- 视频片段 A/B 对比
- ReviewPackage 创建
- RevisionRequest 创建
- AcceptanceRecord 创建
- 上色审核页面渲染
- 片段对比页面渲染
- 客户审片页面渲染

### 6. P1/P2 全量 scaffold 测试

文件：`tests/test_p1_p2.py`

覆盖内容：

- PDF mock 导入，并生成本地页面 PNG
- 分格手动修正
- 高级角色色彩档案
- 色彩策略应用
- 多语言字幕翻译
- 错误日志创建
- 错误日志页面渲染
- 私有化部署配置
- 云 ComfyUI 池
- workflow 画布编辑
- 专业时间线 track
- 专业时间线 keyframe
- 协作会话
- 模型训练任务
- 高级导出格式，并生成本地 ZIP
- P2 管理页面渲染

### 7. Worker 测试

文件：`tests/test_worker.py`

覆盖内容：

- 创建待处理 AIJob
- 批量运行 pending jobs
- Worker 更新任务状态为 succeeded
- voice_generate job 生成本地 WAV
- export job 生成本地 ZIP
- AIJob retry
- AIJob cancel
- Audit Events 页面渲染
- 本地下载 token
- 本地下载文件读取

### 9. 团队基础设施测试

文件：`tests/test_infra.py`

覆盖内容：

- 团队 SMTP 保存、密码脱敏、测试连接失败回退
- 邀请和忘记密码在 SMTP 不可达时仍返回令牌
- 团队 memory/S3 配置保存、secret 脱敏
- 上色产物写入 memory 对象存储并可通过 `/resources/{id}/file` 读取
- 多机 lease：同一 job 只能被一台 worker 抢走，过期后回收为 queued
- S3 SigV4 签名头
- ComfyUI `tunnel_url` 保存，穿透不可达时 health 为 fallback

### 10. Token Plan 编程工具接入测试

文件：`tests/test_tokenplan.py`

覆盖内容：

- 模型 ID 精确白名单，拒绝 qwen3-coder-next
- Cursor 模型别名 glm-5 → glm-5-0
- Cursor / Claude Code 请求头（User-Agent、Bearer / x-api-key）
- 团队 Token Plan 保存并脱敏
- 探活走 Qwen Code User-Agent
- 制片助手一轮对话会调 read_project_brief 工具
- 图像 Skill 解析 image URL 并落盘
- 视频 Skill 提交异步 task_id

## 最近一次测试输出

```text
..........................                                               [100%]
26 passed in 8.38s
```

现场 API（重启后的 `uvicorn :8000`）额外验证：

```text
health={"status": "ok", "worker": "running", "worker_id": "cursor:18629", "queue": "database", "lease_ttl_seconds": 45}
smtp_save=200 password=********
smtp_probe fallback Connection refused
invite token=True
forgot delivery=local_fallback
storage_save secret=******** backend=memory
colorize backend=memory uri=memory://teams/3/projects/4/colorized/panel-2.png
color_file=200 image/png
comfy tunnel=https://comfy.example.ngrok-free.app health=fallback
LIVE_INFRA_E2E_OK
```

Token Plan 现场（假 Key 打真实网关，确认编程工具握手）：

```text
GET /token-plan/catalog openai+anthropic bases ok, 17/5/3 models
PUT /teams/{id}/token-plan api_key=******** tool_profile=cursor
POST test → fallback Unauthorized · User-Agent Cursor/1.7.0 · OpenAI compatible-mode/v1
studio-agent/turn → local_fallback Unauthorized
direct Cursor POST chat/completions → HTTP 401 invalid_api_key
direct Claude Code POST /apps/anthropic/v1/messages → HTTP 401 InvalidApiKey
LIVE_TOKENPLAN_E2E_OK
```

## 当前测试结论

- 本轮新增后端生产对象通过 API 自动化测试。
- 本轮新增 Web 工作台页面通过页面自动化测试。
- PRD P0 主链路通过端到端 API + 页面自动化测试。
- 增强项通过 API + 页面自动化测试。
- P1/P2 scaffold 通过 API + 页面自动化测试。
- SPA 前端入口和 worker 通过自动化测试。
- 外部接入使用 mock，但内部功能会生成真实本地产物文件。
- 既有漫画转动漫 CLI 管道未出现回归。
- 当前测试不只是接口测试，已包含对应 Web 页面渲染自动化测试。
- 邀请、重置密码、worker tick、密钥加密、ComfyUI fallback、资源文件播放通过 `tests/test_completion.py`。
- 团队 SMTP / S3 / 多机 lease 队列通过 `tests/test_infra.py`。
- 千问 Token Plan 按编程工具接入通过 `tests/test_tokenplan.py`；现场用 Cursor User-Agent 打到真实网关返回 401 invalid_api_key。

## 后续测试建议

- 引入浏览器级端到端测试，覆盖真实表单提交和页面跳转。
- 在对象存储和文件上传接入后，增加上传、预览和导入任务测试。
- 在 ComfyUI 接入后，增加 mock ComfyUI server 合约测试。
- 在 worker 接入后，增加任务重试、取消、失败恢复和并发测试。
