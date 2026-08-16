# mangedong Web SaaS 工作台 PRD 初稿

## 1. 文档信息

- 产品名称：mangedong
- 产品形态：Web SaaS
- 文档状态：PRD 初稿 v0.3
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

### 2.1 产品原则

- 工作台优先：所有关键能力都必须能在 Web 中配置、运行、审核和追溯。
- 人在回路：AI 负责生成草稿和候选结果，团队成员负责确认、修正和批准。
- 可替换模型：第三方 API、远程 ComfyUI 和未来本地模型必须通过统一 Provider 层接入。
- 生产可追溯：商业交付必须保存输入、参数、模型、workflow、版本和操作者。
- 渐进增强：V1 先完成可用生产闭环，番剧级质量通过参考素材、重生成和工作流调优逐步提高。

### 2.2 成功指标

- 从导入漫画到生成可预览视频片段的主链路可在一个项目内完成。
- 一个团队可以完成成员邀请、角色分配和项目协作。
- 用户可以成功配置至少一个第三方 AI Provider 或一个远程 ComfyUI 实例。
- 用户上传的 ComfyUI workflow 可以被解析、绑定参数、测试运行并产生产物。
- 单个分格支持至少一次 AI 分析、一次参考上色、一次视频生成和一次重生成。
- 项目可以导出包含 MP4、字幕和生成记录的商业交付包。

### 2.3 V1 北极星指标

- 首版视频片段生成成功率：生成任务产出可播放视频的比例。
- 分格一次审核通过率：生成结果无需重生成即可通过审核的比例。
- 单分格平均生成成本：按 Provider 费用和平台资源估算。
- 单分格首版可预览耗时：从提交生成到可播放预览的中位耗时。
- 项目导出成功率：商业导出任务成功生成完整交付包的比例。
- Workflow 可用率：上传 workflow 通过解析、绑定和测试运行的比例。

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

### 3.6 关键用户旅程

#### 旅程 A：制片创建商业项目

```text
登录
→ 进入团队空间
→ 创建项目
→ 选择目标语言、比例、分辨率、FPS
→ 导入漫画章节
→ 指派美术、动画和审核成员
→ 查看项目生产进度
→ 审核最终导出
```

#### 旅程 B：美术建立参考上色规范

```text
进入项目素材库
→ 上传已上色漫画页和角色设定图
→ AI 提取色彩和角色候选
→ 手动确认角色色彩档案
→ 对页面或分格执行参考上色
→ 对局部结果重生成或修正
→ 保存可复用版本
```

#### 旅程 C：动画人员生成视频片段

```text
进入分格工作台
→ 查看 OCR 和 AI 分析结果
→ 调整镜头描述、动作描述和提示词
→ 选择第三方视频 API 或 ComfyUI workflow
→ 修改 workflow 参数
→ 提交生成任务
→ 预览视频片段
→ 重生成或提交审核
```

#### 旅程 D：Owner 配置 ComfyUI

```text
进入 AI 工作流中心
→ 新增远程 ComfyUI 实例
→ 完成健康检查
→ 上传 workflow JSON
→ 系统解析节点和参数
→ 绑定输入图片、提示词、seed、输出节点
→ 测试运行
→ 设为项目默认 workflow
```

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

### 4.3 V1 功能优先级

#### P0：没有这些就不能形成 V1 闭环

- 登录、团队、成员角色
- 项目、章节、页面、分格管理
- 漫画图片/CBZ/ZIP 导入
- 素材库
- AI Provider 抽象
- 远程 ComfyUI 实例配置
- ComfyUI workflow 上传、解析、参数绑定、测试运行
- 任务队列和任务状态
- OCR 基础能力
- AI 内容分析基础能力
- 参考上色基础能力
- 单分格视频生成
- 视频片段预览和重生成
- 字幕基础生成
- TTS 配音
- BGM 上传和绑定
- MP4 导出
- 生成参数与 workflow 版本记录

#### P1：V1 应尽量包含，但可以在 P0 稳定后补齐

- PDF 导入
- 分格手动修正
- 角色色彩档案批量应用
- 多语言字幕翻译
- 审核评论
- 项目级成本统计
- 导出交付包
- 错误日志可视化

#### P2：明确进入后续版本

- 私有化部署
- 内置云端 ComfyUI 算力
- 图形化 workflow 画布编辑
- 专业时间轴
- 多人实时协同
- 训练/微调模型管理
- 高级商业格式导出

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

### 5.1 V1 页面清单

| 页面 | 主要用户 | 核心能力 |
| --- | --- | --- |
| 登录页 | 所有用户 | 登录、注册入口、忘记密码入口 |
| 团队选择页 | 所有用户 | 切换团队、创建团队 |
| Dashboard | Owner / Producer | 项目概览、任务概览、异常提醒 |
| 项目列表 | Producer | 创建项目、筛选项目、查看状态 |
| 项目详情 | Producer / Reviewer | 查看章节、进度、成员、导出状态 |
| 章节页面 | Producer / Artist | 导入章节、查看页面、调整顺序 |
| 页面/分格工作台 | Artist / Animator | OCR、分格、上色、视频生成、预览 |
| 参考库 | Artist | 管理上色漫画页、角色设定图、色彩档案 |
| AI Provider 设置 | Owner / Admin | 配置第三方 API、本地模型预留参数 |
| ComfyUI 实例页 | Owner / Admin | 配置远程实例、健康检查、并发限制 |
| Workflow 模板页 | Owner / Animator | 上传、解析、绑定、测试 workflow |
| 任务中心 | Owner / Producer | 查看队列、进度、失败原因、重试 |
| 审核页 | Reviewer / Producer | 评论、打回、批准、选择最终版本 |
| 导出页 | Producer | 配置导出规格、生成交付包、下载 |
| 成员权限页 | Owner / Admin | 邀请成员、设置角色、移除成员 |

### 5.2 页面/分格工作台布局建议

```text
左侧：项目结构树
中间：漫画页 / 分格 / 视频预览
右侧：AI 分析、上色、视频、配音、字幕参数面板
底部：任务状态、版本历史、评论
```

该页面是 V1 的核心生产界面，所有单分格生成、重生成和审核动作都应能从这里完成。

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

### 6.3 V1 权限矩阵

| 功能 | Owner | Admin | Producer | Artist | Animator | Reviewer | Viewer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 管理团队 | 是 | 是 | 否 | 否 | 否 | 否 | 否 |
| 管理成员 | 是 | 是 | 否 | 否 | 否 | 否 | 否 |
| 配置 AI Provider | 是 | 是 | 否 | 否 | 否 | 否 | 否 |
| 配置 ComfyUI | 是 | 是 | 否 | 否 | 否 | 否 | 否 |
| 创建项目 | 是 | 是 | 是 | 否 | 否 | 否 | 否 |
| 导入漫画 | 是 | 是 | 是 | 是 | 否 | 否 | 否 |
| 管理参考图 | 是 | 是 | 是 | 是 | 否 | 否 | 否 |
| 执行上色 | 是 | 是 | 是 | 是 | 否 | 否 | 否 |
| 执行视频生成 | 是 | 是 | 是 | 否 | 是 | 否 | 否 |
| 审核结果 | 是 | 是 | 是 | 否 | 否 | 是 | 否 |
| 发起导出 | 是 | 是 | 是 | 否 | 否 | 否 | 否 |
| 查看项目 | 是 | 是 | 是 | 是 | 是 | 是 | 是 |
| 查看成本 | 是 | 是 | 是 | 否 | 否 | 否 | 否 |

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
- PDF，P1 支持

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

### 13.8 Workflow 解析与绑定验收规则

一个 workflow 只有满足以下条件，才能被标记为“可用于生产”：

- JSON 格式有效
- 能转换为 ComfyUI `/prompt` 可执行格式
- 至少绑定一个输出节点
- 对视频 workflow，必须识别或手动绑定视频输出节点
- 对图生视频 workflow，必须识别或手动绑定输入图片节点
- 正向提示词、负向提示词、seed 至少有一个可编辑入口
- 参数 schema 保存成功
- 测试运行成功
- 输出文件成功回传到 SaaS 素材库

### 13.9 Workflow 参数分层

为了降低使用门槛，参数编辑分为三层：

- 基础参数：提示词、seed、宽高、帧数、FPS
- 高级参数：steps、cfg、sampler、scheduler、运动强度
- 专家参数：节点级 JSON、LoRA、ControlNet、IP-Adapter、自定义输入

默认只展示基础参数，高级和专家参数需要用户主动展开。

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

### 14.4 视频质量标准

V1 不承诺一次生成即可达到最终番剧质量，但需要支持团队通过多次生成和审核接近商业可交付质量。

基础质量要求：

- 视频可播放
- 分辨率符合项目设置
- 时长符合镜头设置
- 画面主体没有明显崩坏
- 角色外观与参考图大体一致
- 动作与镜头描述大体一致
- 无黑屏、花屏、严重闪烁
- 生成参数完整记录

审核时可标记的问题类型：

- 角色不一致
- 脸部崩坏
- 肢体异常
- 动作不符合
- 镜头不符合
- 色彩不一致
- 字幕错误
- 音频错误
- 时长错误
- 需要重生成

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

### 18.3 通用任务状态机

```text
created
→ queued
→ running
→ succeeded
```

异常分支：

```text
queued/running
→ failed
→ retrying
→ queued
```

用户操作分支：

```text
queued/running
→ cancelling
→ cancelled
```

### 18.4 任务重试规则

- 用户可手动重试失败任务
- 系统可对网络错误自动重试
- 参数错误不自动重试
- Provider 鉴权失败不自动重试
- 每次重试必须生成新的 attempt 记录
- 每个 attempt 保存输入参数、错误信息和输出文件

### 18.5 任务进度展示

前端至少展示：

- 当前阶段
- 百分比进度
- 已耗时
- 预计剩余时间，可为空
- 当前 Provider
- 当前模型或 workflow
- 失败原因
- 重试入口

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
- shots
- timelines
- timeline_items
- video_clips
- voice_lines
- voice_tracks
- subtitle_cues
- exports
- export_manifests
- review_comments
- audit_logs

### 19.1 生产对象关系

```text
Team
└── Project
    └── Chapter
        └── Page
            └── Panel
                ├── Shot
                │   ├── VideoClip
                │   ├── VoiceLine
                │   └── SubtitleCue
                └── ReviewComment

Project
└── Timeline
    └── TimelineItem
        ├── VideoClip
        ├── VoiceLine
        ├── SubtitleCue
        └── BGM Asset

Export
└── ExportManifest
```

### 19.2 新增关键对象说明

- Shot：动画镜头，是从 Panel 派生的可生成单元，包含镜头描述、动作描述、时长、提示词。
- Timeline：项目最终成片时间线，聚合多个视频片段、字幕、配音和 BGM。
- TimelineItem：时间线上的一个片段，记录起止时间、轨道类型、关联素材。
- VoiceLine：单句配音，记录角色、语言、文本、声线、音频文件和时间。
- SubtitleCue：字幕条目，记录语言、文本、起止时间、样式和来源。
- ExportManifest：商业导出清单，记录最终交付文件、素材来源、参数、模型和审核记录。

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

### Assets

- `GET /projects/{project_id}/assets`
- `POST /projects/{project_id}/assets`
- `GET /assets/{asset_id}`
- `DELETE /assets/{asset_id}`

### References

- `POST /projects/{project_id}/reference-images`
- `GET /projects/{project_id}/characters`
- `POST /projects/{project_id}/characters`
- `PATCH /characters/{character_id}/color-profile`

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

### Jobs

- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/retry`
- `POST /jobs/{job_id}/cancel`

### Review

- `POST /review-comments`
- `PATCH /review-comments/{comment_id}`
- `POST /video-clips/{clip_id}/approve`
- `POST /video-clips/{clip_id}/reject`

### Export

- `POST /projects/{project_id}/exports`
- `GET /exports/{export_id}`

### Costs

- `GET /teams/{team_id}/costs`
- `GET /projects/{project_id}/costs`
- `PATCH /teams/{team_id}/budget`
- `PATCH /projects/{project_id}/budget`

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

### 24.1 Milestone 1：SaaS 基础与团队空间

- Web 应用框架
- 登录注册
- 团队创建
- 成员邀请
- RBAC 权限
- Dashboard 雏形

交付标准：用户可以进入团队空间，并以不同角色看到不同操作权限。

### 24.2 Milestone 2：项目、导入和素材库

- 项目管理
- 章节管理
- 图片/CBZ/ZIP 导入
- 页面预览
- 素材库
- 基础任务队列

交付标准：团队可以创建项目、导入漫画章节，并在页面工作台查看素材。

### 24.3 Milestone 3：ComfyUI Workflow Center

- ComfyUI 实例配置
- 健康检查
- Workflow 上传
- Workflow 解析
- 参数 schema 生成
- 节点输入编辑
- 测试运行

交付标准：用户可以上传 workflow，绑定输入输出节点，修改参数，并完成一次测试运行。

### 24.4 Milestone 4：AI 分析与参考上色

- OCR Provider 接入
- AI 内容分析
- 参考图上传
- 调色板提取
- 角色色彩档案
- 单页/单分格参考上色

交付标准：系统可以从漫画页生成 OCR、内容分析结果和参考上色图。

### 24.5 Milestone 5：视频生成与审核

- Video Provider 接入
- ComfyUI 视频 workflow 执行
- 单分格视频生成
- 片段预览
- 重生成
- 审核状态
- 评论和打回

交付标准：用户可以从一个上色分格生成视频片段，并完成审核或重生成。

### 24.6 Milestone 6：配音、字幕、BGM 和商业导出

- TTS Provider 接入
- 字幕生成和编辑
- BGM 上传和绑定
- MP4 合成
- SRT/VTT 导出
- 生成记录打包
- 商业导出包

交付标准：项目可以导出包含视频、字幕、音频和生成记录的交付包。

## 25. 成本、额度与风控

### 25.1 成本对象

- 团队月预算
- 项目预算
- Provider 预算
- 单任务预估成本
- 单任务实际成本
- 失败任务成本
- 重试任务成本

### 25.2 成本控制规则

- Owner 可以设置团队月预算。
- Producer 可以设置项目预算。
- 每个生成任务提交前展示预估成本。
- 预估成本超过阈值时需要二次确认。
- 团队预算耗尽后阻止新生成任务。
- 失败任务是否计费需要按 Provider 规则记录。
- 所有成本记录必须关联任务、Provider、模型、操作者。

### 25.3 并发和限流

- 团队级并发限制
- Provider 级并发限制
- ComfyUI 实例级并发限制
- 用户级提交频率限制
- 大批量任务需进入低优先级队列

## 26. 商业版权与合规

### 26.1 素材授权记录

需要记录来源和授权状态：

- 原始漫画
- 已上色参考图
- 角色设定图
- BGM
- 音效
- 字体
- TTS 声音
- AI Provider
- ComfyUI workflow
- 模型权重

### 26.2 商业导出前置检查

导出商业交付包前必须检查：

- 所有视频片段已 approved
- 所有字幕已 approved
- 所有配音已 approved
- 所有 BGM 有来源记录
- 所有参考图有授权记录
- Provider 商用授权状态已记录
- workflow 版本已冻结
- 生成参数记录完整
- 审核记录完整

### 26.3 授权状态

- unknown
- internal_owned
- licensed
- public_domain
- user_provided
- restricted
- blocked

状态为 `blocked` 的素材不得进入商业导出。

## 27. 质量分级与导出门槛

### 27.1 质量等级

- A：可商业交付。
- B：需要轻微修正，不能直接交付。
- C：必须重生成。
- D：生成失败或不可用。

### 27.2 自动拦截项

命中以下任一项时不得进入商业导出：

- 视频不可播放
- 黑屏
- 花屏
- 分辨率错误
- 时长错误
- 音频缺失
- 字幕缺失
- 未通过审核
- 使用 blocked 授权素材
- 缺少生成参数记录

### 27.3 人工审核维度

- 角色一致性
- 色彩一致性
- 动作合理性
- 镜头符合度
- 台词准确性
- 字幕准确性
- 配音匹配度
- BGM 情绪匹配度
- 商业交付完整性

## 28. 失败恢复与生产连续性

### 28.1 失败恢复能力

- 单任务手动重试
- 批量失败任务重试
- 复制参数重跑
- 切换 Provider 重跑
- 切换 ComfyUI workflow 重跑
- 从上一步成功产物继续执行
- ComfyUI 输出拉取失败后的补拉

### 28.2 依赖任务处理

任务之间存在依赖：

```text
import → preprocess → ocr → analyze → colorize → video_generate → voice/subtitle/bgm → export
```

如果上游任务失败：

- 下游任务不得自动执行
- 用户可以修复上游结果后继续
- 重新执行上游任务时，需要提示是否覆盖下游结果

### 28.3 失败原因分类

- user_input_error
- provider_auth_error
- provider_rate_limited
- provider_timeout
- provider_internal_error
- comfyui_connection_error
- workflow_parse_error
- workflow_execution_error
- output_download_error
- storage_error
- unknown_error

## 29. 数据生命周期与安全边界

### 29.1 数据保留

- 原始素材默认长期保留，直到用户删除项目。
- 中间帧可设置自动清理周期。
- 失败任务临时文件默认保留 7 天。
- 导出包可设置过期时间。
- 删除项目时进入软删除状态，保留恢复窗口。

### 29.2 多租户隔离

- 所有业务表必须包含 team_id。
- 所有文件路径必须按 team/project 隔离。
- 后端 API 必须校验用户团队权限。
- Worker 执行任务时必须校验任务所属团队。
- Provider 凭证只能被同团队任务读取。

### 29.3 密钥与凭证

- API Key 加密存储。
- ComfyUI Token 加密存储。
- 支持手动轮换。
- 凭证不返回前端明文。
- 审计日志记录凭证创建、更新、删除操作。

### 29.4 SaaS 调用远程 ComfyUI 安全策略

- 仅允许 HTTPS。
- 禁止私有 IP。
- 禁止 localhost。
- 禁止 link-local 地址。
- 禁止云 metadata 地址。
- 限制请求超时。
- 限制响应体大小。
- 限制可下载文件类型。
- 对上传文件做格式和大小校验。

## 30. 可观测性与运营指标

### 30.1 技术监控

- API 错误率
- Worker 队列长度
- 任务平均等待时间
- 任务平均执行时间
- Provider 成功率
- ComfyUI 连接成功率
- ComfyUI workflow 测试通过率
- 导出成功率
- 存储用量

### 30.2 产品指标

- 新建团队数
- 新建项目数
- 导入章节数
- 生成视频片段数
- 审核通过率
- 重生成率
- 商业导出次数
- 人均项目协作人数

### 30.3 运营看板

Owner / Admin 需要看到：

- 本月任务数
- 本月成本
- Provider 成本分布
- 失败任务排行
- 最常用 workflow
- 存储占用

## 31. QA 测试计划

### 31.1 功能测试

- 登录、退出、权限隔离
- 团队成员邀请和角色变更
- 项目创建和章节导入
- 页面和分格展示
- OCR、分析、上色、视频生成任务
- ComfyUI 实例健康检查
- workflow 上传、解析、参数编辑、测试运行
- 配音、字幕、BGM 绑定
- 审核、重生成、导出

### 31.2 集成测试

- 第三方 AI Provider mock
- ComfyUI mock server
- 对象存储 mock
- 任务队列和 Worker
- 导出合成链路

### 31.3 安全测试

- 越权访问
- 跨团队数据读取
- 文件上传类型绕过
- ComfyUI SSRF
- API Key 泄露
- 大文件滥用

### 31.4 验收样例

V1 至少准备三组样例：

- 中文黑白漫画页
- 日文黑白漫画页
- 英文黑白漫画页

每组样例需要覆盖：

- OCR
- 参考上色
- 视频生成
- 字幕生成
- 配音生成
- 商业导出

## 32. 商业模式、套餐与采购路径

V1 不实现完整计费系统，但 PRD 需要明确商业边界，避免架构无法支持后续收费。

### 32.1 ICP

- 漫画工作室：关注批量章节生产、角色一致性、交付效率。
- 动画外包团队：关注分镜、视频生成、审核和商业交付包。
- MCN / 短视频团队：关注竖屏导出、字幕、配音、BGM 和批量产能。
- IP 方：关注授权记录、审片流程、品牌一致性和交付审计。
- 译制团队：关注中日英 OCR、翻译字幕、多语言配音。

### 32.2 套餐维度预留

- 席位数
- 项目数
- 存储空间
- 每月导出分钟数
- 并发任务数
- BYO Provider
- ComfyUI 实例数量
- 高级审计包
- 企业 SLA
- 私有化部署，V2

### 32.3 采购路径

- 试用团队
- POC 项目
- 正式团队空间
- 企业合同
- 发票和付款信息
- 续费和超额用量

V1 可以先实现套餐字段和用量记录，不实现自动扣费。

## 33. 工作室生产流程、RACI 与交接门禁

### 33.1 RACI

| 阶段 | Responsible | Accountable | Consulted | Informed |
| --- | --- | --- | --- | --- |
| 项目创建 | Producer | Owner | Admin | Team |
| 漫画导入 | Producer / Artist | Producer | Reviewer | Team |
| OCR 校对 | Artist | Producer | Reviewer | Animator |
| 角色色彩档案 | Artist | Producer | Owner | Animator |
| 分镜脚本 | Animator | Producer | Reviewer | Artist |
| 视频生成 | Animator | Producer | Artist | Reviewer |
| 配音字幕 BGM | Animator | Producer | Reviewer | Owner |
| 内部审核 | Reviewer | Producer | Artist / Animator | Owner |
| 客户交付 | Producer | Owner | Reviewer | Team |

### 33.2 交接门禁

- 角色色彩档案 approved 后，才能批量参考上色。
- 分格顺序 locked 后，才能批量生成镜头脚本。
- 镜头脚本 locked 后，才能批量生成视频。
- 视频片段 approved 后，才能进入时间线。
- 字幕和配音 approved 后，才能执行商业导出。
- ExportManifest 生成后，交付包进入 frozen 状态。

### 33.3 锁定与解锁

- locked 状态的对象不可被普通成员覆盖。
- Producer 可以发起解锁。
- Owner/Admin 可以强制解锁。
- 解锁、修改、重新锁定必须进入审计日志。

## 34. 项目制作规范：Style Bible / Character Bible / Shot Bible

### 34.1 Style Bible

- 画风参考
- 色彩风格
- 光影规则
- 线稿处理规则
- 禁用风格
- 负面示例

### 34.2 Character Bible

- 角色设定图
- 角色色彩档案
- 正面/侧面/背面参考
- 表情参考
- 服装变化
- 禁用改动

### 34.3 Shot Bible

- 镜头语言
- 常用运镜
- 动作强度
- 分格转镜头规则
- 视频提示词模板
- 负向提示词模板

这些制作规范必须支持版本化、审批、冻结，并被 AI 任务引用。

## 35. 客户审片、返修与验收

### 35.1 审片包

- 内部预览包
- 客户审片包
- 最终交付包
- 归档包

### 35.2 客户审片能力

- 只读审片链接
- 链接有效期
- 密码保护
- 时间码批注
- 片段级批注
- 版本对比
- 返修记录
- 客户确认状态

### 35.3 状态扩展

- internal_approved
- client_reviewing
- client_changes_requested
- client_approved
- delivered

内部审核通过不等于客户验收通过。

## 36. 商业导出 Manifest 与合规审计

### 36.1 Manifest 必填字段

```json
{
  "project_id": "project_001",
  "export_id": "export_001",
  "exported_at": "2026-08-16T00:00:00Z",
  "exported_by": "user_001",
  "files": [
    {
      "path": "deliverables/final.mp4",
      "type": "video",
      "sha256": "..."
    }
  ],
  "workflow_versions": [],
  "model_snapshots": [],
  "provider_authorizations": [],
  "source_assets": [],
  "review_records": [],
  "export_settings": {}
}
```

### 36.2 合规审计包

- 文件清单和 hash
- 素材授权证明
- Provider 商用条款快照
- 模型和 workflow 版本
- 生成参数 hash
- 审核人和审核时间
- 字幕、配音、BGM 授权状态
- 导出配置

## 37. 多租户隔离与对象存储安全

### 37.1 强制租户边界

- 所有 API 根据 token 解析 team scope。
- 所有全局 ID 查询必须二次校验 team_id。
- 缓存 key 必须包含 team_id。
- 搜索索引必须包含 team_id。
- 日志不得泄露其他租户资源 ID。
- 签名 URL 必须绑定 team_id 和资源 ID。

### 37.2 对象存储规范

```text
teams/{team_id}/projects/{project_id}/assets/{asset_id}/{version}/file
teams/{team_id}/projects/{project_id}/exports/{export_id}/package
```

要求：

- bucket 默认私有。
- 访问通过短期签名 URL。
- 上传文件做魔数校验。
- 大文件上传做分片完整性校验。
- 文件名防路径穿越。
- 导出包设置过期时间。
- 软删除期间禁止新任务引用。

## 38. AI Provider 密钥、授权与数据处理

### 38.1 密钥治理

- BYOK 密钥使用 KMS 加密。
- 支持密钥版本。
- 支持密钥轮换。
- 支持密钥吊销。
- 前端永不回显密钥明文。
- 日志必须脱敏。
- 密钥测试调用进入审计日志。

### 38.2 Provider 合规字段

- 商用授权状态
- 数据是否用于训练
- 数据保留期
- 数据处理区域
- DPA / 条款链接
- 内容安全策略
- 失败是否计费

### 38.3 Provider 降级策略

- 单 Provider 失败时可切换备用 Provider。
- 切换 Provider 会生成新的任务 attempt。
- 新 attempt 必须保留原始输入和参数快照。
- 不同 Provider 生成结果不得覆盖原结果。

## 39. 任务队列可靠性、幂等与公平调度

### 39.1 可靠性要求

- 每个任务有 idempotency_key。
- Worker 需要 lease 和 heartbeat。
- 超时任务自动回收。
- 失败任务进入 dead letter queue。
- 重试使用指数退避和 jitter。
- 取消任务必须定义是否清理部分产物。

### 39.2 租户公平调度

- 队列按团队维度限流。
- 单团队不能耗尽全部 worker。
- 高优先级任务需要权限。
- 批量任务默认低优先级。
- Owner 可以查看团队队列占用。

### 39.3 任务 DAG 一致性

- 下游任务必须引用上游产物版本。
- 上游产物被替换时，下游任务标记为 stale。
- 用户重新生成上游产物时，系统提示是否使下游结果失效。

## 40. 可观测性、SLO 与告警

### 40.1 Trace 贯穿

以下字段需要贯穿 API、Worker、Provider、Storage：

- request_id
- job_id
- team_id
- project_id
- provider_id
- workflow_version_id

### 40.2 SLO 初稿

- API 可用性：99.5%
- 任务状态更新延迟：P95 小于 5 秒
- 导出任务成功率：大于 95%
- Provider 调用日志完整率：大于 99%
- ComfyUI 健康检查误报率：小于 1%

### 40.3 告警

- API 错误率异常
- Worker 队列积压
- Provider 成功率下降
- ComfyUI 连接失败率上升
- 成本异常增长
- 存储容量异常
- 跨租户访问拦截
- 导出失败率异常

## 41. 安全、可靠性与合规测试验收标准

### 41.1 安全测试门槛

- 跨团队 API 越权测试通过
- 签名 URL 越权测试通过
- ComfyUI SSRF 绕过测试通过
- 文件上传类型绕过测试通过
- API Key 泄露检查通过
- 权限变更审计检查通过

### 41.2 可靠性测试门槛

- 任务重复提交不会生成重复产物
- Worker 中断后任务可恢复或失败可重试
- Provider 超时会进入可解释失败状态
- ComfyUI 输出拉取失败可补拉
- 批量任务不会阻塞高优先级任务

### 41.3 合规测试门槛

- 商业导出缺少授权记录时被拦截
- blocked 授权素材无法导出
- ExportManifest 字段完整
- 审核记录完整
- 删除项目后素材不可被新任务引用
