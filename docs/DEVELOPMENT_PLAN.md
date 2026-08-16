# 第一轮开发拆解

本轮开发从 PRD 的 P0 基础链路开始，优先建立 Web SaaS 后端骨架和团队协作基础，避免直接跳到 AI 生成导致后续权限、任务和商业交付难以补齐。

## Milestone 1：SaaS 基础与团队空间

### 已完成

- FastAPI 后端应用工厂
- SQLite/SQLAlchemy 持久化基础
- 用户注册
- 用户登录
- Bearer token 鉴权
- `/auth/me`
- 团队创建
- 团队列表
- 团队成员列表
- 团队成员添加
- 基础 RBAC
- Project Brief schema
- 项目创建
- 项目列表
- 项目详情
- WorkItem 制片任务模型和接口
- ProductionGate 阶段门禁模型和接口
- 素材库元数据模型和接口
- 章节、页面、分格模型和接口
- AIJob 队列基础模型和接口
- 轻量 Web 工作台页面
- 页面自动化测试
- API 自动化测试

### 当前 RBAC

- `owner`、`admin` 可以管理团队成员。
- `owner`、`admin`、`producer` 可以创建项目。
- 团队成员可以查看团队项目。
- 非团队成员不能访问团队项目。

### 下一步建议

1. 增加真实文件上传和对象存储抽象。
2. 将 CBZ/ZIP 导入接入后端导入任务。
3. 增加 ComfyUI 实例配置和健康检查。
4. 增加 workflow 上传、解析和 Published Parameters。
5. 增加任务执行 worker。

## Milestone 2：项目、导入和素材库

当前进度：

- 章节模型
- 页面模型
- 分格模型
- 素材库元数据模型
- AIJob 队列基础

待开发内容：

- 原始素材上传
- 缩略图生成
- CBZ/ZIP 导入接入后端
- 导入任务执行
- 对象存储抽象

## Milestone 3：ComfyUI Workflow Center

建议开发内容：

- ComfyUI 实例配置
- 健康检查
- Workflow JSON 上传
- API/UI workflow 解析
- Published Parameters
- 节点输入编辑
- workflow 兼容性检查
- 测试运行

## Milestone 4：参考上色与批量任务

建议开发内容：

- 参考图上传
- 角色档案
- 色彩档案
- 批量参考上色任务
- 局部修正任务
- 上色版本对比

## Milestone 5：Shot List、Animatic 和轻量时间线

建议开发内容：

- Shot List
- 一个 Panel 拆多个 Shot
- 多个 Panel 合并一个 Shot
- Animatic Preview
- Timeline
- TimelineItem
- 片段 A/B 对比

## Milestone 6：音频、审核和商业导出

建议开发内容：

- DialogueLine
- Voice Bible
- VoiceLine
- SubtitleCue
- MusicCue
- AudioMix
- QCReport
- ReviewPackage
- RevisionRequest
- AcceptanceRecord
- ExportManifest
