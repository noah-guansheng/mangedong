# mangedong Web SaaS 工作台 PRD 初稿

## 1. 文档信息

- 产品名称：mangedong
- 产品形态：Web SaaS
- 文档状态：PRD 初稿
- 目标版本：V1
- V2 方向：私有化部署、本地网络模型、深度工作流编排、企业级交付

## 2. 产品定位

mangedong 是一个面向团队和工作室的漫画转番剧动画生产工作台。用户可以导入黑白漫画，系统通过 AI 完成内容理解、参考上色、分镜规划、视频生成、配音、字幕、BGM 和商业导出。

V1 的目标不是做一个单点 AI 工具，而是建立一条可审核、可追溯、可团队协作的商业生产链路。

核心链路：

```text
漫画导入
→ 页面/分格预处理
→ 中日英 OCR 与内容分析
→ 参考上色与角色色彩一致性
→ 分镜和镜头脚本生成
→ AI 视频生成
→ 配音、字幕、BGM
→ 审核、重生成、版本管理
→ 商业交付导出
```

## 3. 目标用户

### 3.1 工作室 Owner

- 创建团队
- 管理成员
- 配置 AI 服务
- 查看成本和任务
- 管理商业交付

### 3.2 制片 / 项目负责人

- 创建项目
- 导入漫画章节
- 分配任务
- 审核生成结果
- 发起最终导出

### 3.3 美术 / 上色人员

- 上传上色参考
- 维护角色设定图
- 修正 AI 上色
- 管理角色色彩档案

### 3.4 动画 / 后期人员

- 查看 AI 分镜
- 调整镜头参数
- 调用视频生成
- 重生成失败或低质量片段
- 调整字幕、音频和 BGM

### 3.5 审核人员

- 预览结果
- 标注问题
- 打回重做
- 确认可交付版本

## 4. V1 产品目标

### 4.1 必须达成

- 支持团队/工作室使用
- 支持登录和团队权限
- 支持项目、章节、页面、分格管理
- 支持黑白漫画导入
- 支持中日英 OCR 和字幕基础处理
- 支持上传已上色漫画页作为参考
- 支持上传角色设定图作为参考
- 支持 AI 内容分析
- 支持第三方 AI API
- 支持用户配置远程 ComfyUI
- 支持上传、解析、执行 ComfyUI workflow
- 支持修改 workflow 节点输入内容
- 支持 AI 视频生成
- 支持配音、字幕、BGM
- 支持商业 MP4 导出
- 支持任务队列、状态跟踪、错误日志
- 支持生成记录和参数追溯

### 4.2 不在 V1 范围

- 私有化部署
- 内置平台自营 ComfyUI 算力
- 在线图形化编辑 ComfyUI 节点连线
- 完整专业 NLE 时间轴
- 多人实时协同编辑
- 自训练模型平台
- 完整计费系统
- ProRes / DCP 等高级交付格式

## 5. 核心信息架构

```text
登录
团队空间
├── Dashboard
├── 项目
│   ├── 章节
│   ├── 页面
│   ├── 分格
│   ├── 分镜
│   ├── 视频片段
│   └── 导出
├── 素材库
│   ├── 原始漫画
│   ├── 上色参考
│   ├── 角色设定
│   ├── 音频
│   └── 导出包
├── AI 工作流
│   ├── Provider 配置
│   ├── ComfyUI 实例
│   ├── Workflow 模板
│   └── 生成任务
├── 成员与权限
└── 系统设置
```

## 6. 权限设计

### 6.1 角色

- Owner：团队所有权限
- Admin：团队成员、项目、AI 配置管理
- Producer：项目管理、任务分配、导出审批
- Artist：上色、参考图、角色档案管理
- Animator：分镜、视频生成、重生成
- Reviewer：审核、评论、打回
- Viewer：只读查看

### 6.2 权限范围

- 团队级权限
- 项目级权限
- AI 配置权限
- 导出权限
- 成本查看权限

V1 采用团队级 RBAC + 项目成员授权，不做复杂到单个文件的 ACL。

## 7. 项目与内容管理

### 7.1 项目

项目字段：

- 项目名称
- 项目描述
- 目标语言
- 输出比例
- 默认 FPS
- 默认分辨率
- 默认 AI Provider
- 默认 ComfyUI workflow
- 项目状态
- 创建人
- 所属团队

项目状态：

- draft
- importing
- analyzing
- coloring
- animating
- reviewing
- exporting
- completed
- archived

### 7.2 章节

- 章节名称
- 页数
- 语言
- 导入状态
- 分析状态
- 上色状态
- 视频状态

### 7.3 页面

- 原图
- 预处理图
- OCR 结果
- 分格结果
- 上色结果
- 审核状态

### 7.4 分格

- 所属页面
- 分格坐标
- 分格顺序
- 识别文本
- 角色列表
- 场景描述
- 动作描述
- 镜头脚本
- 生成视频片段

## 8. 漫画导入与预处理

### 8.1 支持格式

- PNG
- JPG/JPEG
- WEBP
- ZIP
- CBZ
- PDF

### 8.2 导入能力

- 单文件导入
- 多文件导入
- 章节批量导入
- 自动排序
- 缩略图生成
- 导入失败重试
- 导入日志

### 8.3 预处理能力

- 图片格式标准化
- EXIF 修正
- 去噪
- 线稿增强
- 页面裁剪
- 自动分格
- 分格手动修正
- 气泡检测

## 9. 多语言 OCR 与字幕基础

### 9.1 语言范围

V1 支持：

- 中文
- 日文
- 英文

### 9.2 OCR 功能

- 页面 OCR
- 分格 OCR
- 气泡文本识别
- 文本区域坐标
- 置信度
- 手动修正
- 说话角色归属

### 9.3 字幕功能

- OCR 文本转字幕草稿
- 中日英翻译
- SRT 导出
- VTT 导出
- 字幕烧录
- 字幕样式配置

## 10. 参考上色系统

### 10.1 参考来源

- 已上色漫画页
- 角色设定图
- 场景设定图
- 色卡

### 10.2 色彩参考库

每个项目维护独立参考库：

- 参考图名称
- 类型
- 关联角色
- 关联场景
- 主色提取结果
- 上传人
- 版本

### 10.3 角色色彩档案

角色档案字段：

- 角色 ID
- 角色名称
- 参考图
- 发色
- 瞳色
- 肤色
- 服装主色
- 服装辅色
- 常见配饰
- 备注

### 10.4 上色流程

```text
上传参考图
→ AI 提取调色板
→ AI 识别角色
→ 用户确认角色色彩档案
→ 应用到漫画分格
→ 生成上色结果
→ 人工修正
→ 保存为版本
```

### 10.5 上色要求

- 保留线稿
- 角色色彩一致
- 场景风格一致
- 支持局部重上色
- 支持参考图权重调整
- 支持版本对比

## 11. AI 内容分析

### 11.1 分析对象

- 页面
- 分格
- 角色
- 台词
- 场景
- 动作
- 情绪

### 11.2 输出内容

- 页面摘要
- 分格摘要
- 角色列表
- 情绪标签
- 动作标签
- 场景标签
- 台词归属
- 镜头建议
- 视频提示词
- 负向提示词

### 11.3 结构化输出示例

```json
{
  "panel_id": "panel_001",
  "scene": "night street",
  "characters": ["hero"],
  "emotion": "tense",
  "action": "hero turns back",
  "camera": "slow zoom in",
  "duration_seconds": 4,
  "positive_prompt": "anime cinematic shot, hero turns back, dramatic lighting",
  "negative_prompt": "low quality, distorted face, extra limbs"
}
```

## 12. AI Provider Center

### 12.1 Provider 类型

- 第三方 API
- 远程 ComfyUI
- 本地模型预留
- 自定义 HTTP Provider

### 12.2 能力类型

- OCR
- 漫画分析
- 上色
- 图生图
- 图生视频
- 配音
- BGM
- 翻译

### 12.3 统一抽象

```text
Provider
├── AnalysisProvider
├── OCRProvider
├── ColorizeProvider
├── ImageProvider
├── VideoProvider
├── VoiceProvider
├── MusicProvider
└── SubtitleProvider
```

### 12.4 Provider 配置

- 名称
- 类型
- API Key
- Base URL
- 模型名称
- 默认参数
- 并发限制
- 超时
- 费用配置
- 是否启用

## 13. ComfyUI Workflow Center

### 13.1 ComfyUI 实例配置

字段：

- 实例名称
- Base URL
- 鉴权方式
- Token/Header
- 最大并发数
- 超时时间
- WebSocket 开关
- 健康检查状态
- 所属团队
- 创建人

SaaS 安全要求：

- V1 仅允许公网 HTTPS 地址
- 禁止 localhost
- 禁止内网 IP
- 禁止云 metadata 地址
- 请求和下载必须有大小限制
- API 密钥加密存储
- 调用日志可追溯

### 13.2 Workflow 上传

支持：

- ComfyUI API workflow JSON
- ComfyUI UI workflow JSON

上传后系统执行：

- JSON 校验
- workflow 类型识别
- 节点解析
- 输入字段解析
- 输出字段解析
- 连接关系解析
- 参数 schema 生成
- 可编辑字段推断

### 13.3 节点自动识别

系统尝试识别：

- 正向提示词节点
- 负向提示词节点
- 输入图片节点
- 参考图节点
- Seed 节点
- Steps 节点
- CFG 节点
- Sampler 节点
- Checkpoint 节点
- LoRA 节点
- ControlNet 节点
- 视频输出节点
- 图片输出节点

识别结果必须允许用户手动修正。

### 13.4 节点输入编辑

用户可以在工作台中修改 workflow 节点输入。

控件类型：

- 文本
- 数字
- 下拉
- 文件
- 开关
- JSON
- 只读连接字段

系统将可编辑节点输入转换成参数 schema：

```json
{
  "positive_prompt": {
    "node_id": "6",
    "input": "text",
    "type": "text",
    "label": "正向提示词",
    "editable": true
  },
  "seed": {
    "node_id": "9",
    "input": "seed",
    "type": "number",
    "label": "Seed",
    "editable": true
  }
}
```

### 13.5 Workflow 版本

每次上传或修改都生成版本。

记录：

- 原始 JSON
- API JSON
- 参数 schema
- 节点映射
- 版本号
- 创建人
- 创建时间
- 是否默认
- 是否测试通过

### 13.6 ComfyUI 执行流程

```text
用户选择分格
→ 选择 ComfyUI 实例
→ 选择 workflow 模板
→ 系统注入图片、提示词和参数
→ 上传输入文件到 ComfyUI
→ 调用 /prompt
→ 记录 prompt_id
→ WebSocket 或轮询获取进度
→ 调用 /history 获取结果
→ 下载图片/视频
→ 存入素材库
→ 更新 AI Job
```

### 13.7 ComfyUI 任务状态

- queued
- preparing
- submitted
- running
- uploading_outputs
- succeeded
- failed
- cancelled
- timeout

## 14. 视频生成系统

### 14.1 生成模式

#### 快速预览模式

- 使用上色分格
- 添加镜头运动
- 快速生成预览视频

#### AI 图生视频模式

- 使用上色图作为首帧
- 输入动作和镜头提示词
- 调用第三方视频 API 或 ComfyUI

#### 番剧增强模式

- 首帧
- 尾帧
- 角色设定图
- 上色参考图
- 风格参考图
- 动作描述
- 镜头描述
- ControlNet / IP-Adapter / LoRA 参数

### 14.2 视频片段字段

- 分格 ID
- 首帧
- 尾帧
- 提示词
- 负向提示词
- Provider
- 模型
- workflow 版本
- seed
- 时长
- FPS
- 分辨率
- 输出视频
- 状态
- 评分

### 14.3 重生成

用户可以针对单个片段：

- 修改提示词
- 修改 seed
- 修改参考图
- 修改 workflow 参数
- 重新生成
- 对比历史版本
- 选择最终版本

## 15. 配音、字幕、BGM

### 15.1 配音

- 角色声线绑定
- 中日英 TTS
- 单句重生成
- 旁白
- 外部音频上传
- 音量调整

### 15.2 字幕

- OCR 文本生成字幕
- 翻译字幕
- 时间轴编辑
- 样式编辑
- SRT/VTT 导出
- 字幕烧录

### 15.3 BGM

- 上传 BGM
- AI 推荐 BGM
- 场景情绪匹配
- 音量 ducking
- 版权来源记录

## 16. 审核与版本管理

### 16.1 审核状态

- pending
- approved
- rejected
- needs_regeneration

### 16.2 审核能力

- 对页面评论
- 对分格评论
- 对视频片段评论
- 打回重生成
- 标记最终版本
- 查看历史版本

## 17. 商业导出

### 17.1 导出内容

- MP4
- SRT
- VTT
- 音频文件
- 分镜表
- 生成参数记录
- workflow 版本记录
- 素材来源记录

### 17.2 导出规格

- 16:9
- 9:16
- 1:1
- 1080p
- 指定 FPS
- 指定码率
- 字幕烧录
- 水印开关
- 片头片尾模板

## 18. 任务系统

### 18.1 任务类型

- import
- preprocess
- ocr
- analyze
- colorize
- image_generate
- video_generate
- voice_generate
- music_generate
- subtitle_generate
- export

### 18.2 任务字段

- 任务 ID
- 类型
- 状态
- 进度
- 所属团队
- 所属项目
- 输入参数
- 输出文件
- 错误日志
- Provider
- 模型
- 成本
- 创建人

## 19. 数据模型初稿

核心表：

- users
- teams
- team_members
- projects
- chapters
- pages
- panels
- assets
- reference_images
- characters
- character_color_profiles
- ai_providers
- comfyui_instances
- workflow_templates
- workflow_versions
- ai_jobs
- video_clips
- voice_tracks
- subtitles
- exports
- review_comments
- audit_logs

## 20. API 初稿

### Auth

- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

### Teams

- `GET /teams`
- `POST /teams`
- `POST /teams/{team_id}/members`
- `PATCH /teams/{team_id}/members/{member_id}`

### Projects

- `GET /projects`
- `POST /projects`
- `GET /projects/{project_id}`
- `PATCH /projects/{project_id}`

### Import

- `POST /projects/{project_id}/imports`
- `GET /imports/{import_id}`

### ComfyUI

- `POST /ai/comfyui/instances`
- `POST /ai/comfyui/instances/{id}/health-check`
- `POST /ai/comfyui/workflows`
- `GET /ai/comfyui/workflows/{id}`
- `POST /ai/comfyui/workflows/{id}/parse`
- `PATCH /ai/comfyui/workflows/{id}/parameters`
- `POST /ai/comfyui/workflows/{id}/test-run`

### Generation

- `POST /panels/{panel_id}/analyze`
- `POST /panels/{panel_id}/colorize`
- `POST /panels/{panel_id}/generate-video`
- `POST /video-clips/{clip_id}/regenerate`

### Export

- `POST /projects/{project_id}/exports`
- `GET /exports/{export_id}`

## 21. 非功能需求

### 安全

- 多租户隔离
- RBAC 权限
- API Key 加密
- ComfyUI URL SSRF 防护
- 文件上传校验
- 审计日志

### 性能

- 大文件分片上传
- 视频生成异步化
- 任务队列
- 缩略图缓存
- 预览低清优先

### 可追溯

- 保存模型名称
- 保存模型版本
- 保存 workflow 版本
- 保存 seed
- 保存提示词
- 保存输入输出文件

### 国际化

- UI 支持中文、英文
- OCR 支持中文、日文、英文
- 字幕支持中文、日文、英文

## 22. V1 验收标准

- 用户可以注册、登录并创建团队
- Owner 可以邀请成员并设置角色
- 用户可以创建项目并导入漫画章节
- 系统可以展示页面和分格
- 系统可以执行中日英 OCR
- 用户可以上传上色参考图和角色设定图
- 系统可以生成角色色彩档案草稿
- 用户可以配置远程 ComfyUI 实例
- 系统可以上传并解析 ComfyUI workflow
- 用户可以修改 workflow 节点输入参数
- 用户可以用 ComfyUI 生成视频片段
- 用户可以用第三方 AI API 生成视频片段
- 用户可以生成配音、字幕和添加 BGM
- 用户可以审核、重生成并选择最终片段
- 用户可以导出商业 MP4 和字幕文件
- 所有 AI 任务有状态、日志和参数记录

## 23. 风险与待确认事项

- 第三方视频 API 的商用授权差异较大，需要逐个确认
- 番剧级质量高度依赖模型能力和参考素材质量
- ComfyUI workflow 格式复杂，自动识别需要允许人工修正
- SaaS 直连用户 ComfyUI 存在安全风险，V1 必须限制公网 HTTPS
- 中日英 OCR 对竖排日文、手写字和艺术字可能效果不稳定
- 角色一致性可能需要后续引入 LoRA / IP-Adapter / 角色库增强
- 专业时间轴和复杂剪辑建议放在 V2 或 V3

## 24. 建议开发顺序

1. Web SaaS 基础框架
2. 登录、团队、权限
3. 项目/章节/页面管理
4. 文件导入和素材库
5. 任务队列
6. ComfyUI 实例配置
7. Workflow 上传、解析和参数编辑
8. AI Provider 抽象
9. OCR 和 AI 分析
10. 参考上色
11. 视频生成
12. 配音、字幕、BGM
13. 审核和版本管理
14. 商业导出
