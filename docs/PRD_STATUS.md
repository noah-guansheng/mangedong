# PRD 完成度审查（真人视角）

审查对象：PRD v0.4 V1 闭环。审查方式：以工作室制片打开 `/app` 后，能否不读源码走完全程。

## 结论

**可以形成一条可演示的本地生产闭环，并已把多团队基础设施做成可配置：SMTP、S3、多机数据库队列。**

它仍然不是可上线的商业 SaaS。真实第三方模型和远程 ComfyUI 会先尝试连接；连不上时回退本地占位文本 / Ken Burns MP4。视频也不是 TV 番剧级成片。

## 功能拆分（按新 UI）

| 导航 | 对应 PRD | 真人能不能用 |
| --- | --- | --- |
| 登录工作室 | 登录/注册 | 能。忘记密码返回 reset_token 并当场改密。未注册邀请可在登录页用令牌加入。 |
| 总览 | Dashboard / 项目列表 | 能用立项向导建剧集，切当前项目，更新 WorkItem 状态。 |
| 导入 | 漫画/PDF 导入 | 能上传并生成章节页格。 |
| 分格 | 页面/分格工作台 | 能看树、看原图、OCR、分析、上色、出视频，并在预览区播放 MP4。 |
| 上色 | 参考上色 / 角色 | 能单格、批量、存参考和角色。没有遮罩画笔。 |
| 镜头 | Shot / Animatic / 时间线 | 能建 Shot、出真实 Animatic MP4、可视化时间线轨道并挂片段。不是专业 NLE。 |
| 音频 | 台词 / BGM | 能建台词、出 WAV/SRT、加 BGM。 |
| 审片 | QC / 时间码批注 | 能播 MP4、按秒数批注、建 QC 和导出记录。 |
| 导出 | 审片包 / 冻结 | 能建审片包、preflight、freeze ZIP。 |
| 模型配置 | Provider / ComfyUI / Workflow / Token Plan | 能填千问 Token Plan 席位 Key，按 Cursor/Qwen Code/Claude Code 画像接入；ComfyUI 地址照旧。 |
| 制片助手 | Token Plan 交互 Agent | 按编程工具协议对话，可调 Brief/分格工具和图像/视频 Skill。不是后台批量任务。 |
| 成员 | RBAC | 能邀请已注册或未注册邮箱、改角色。配置 SMTP 后会尝试发信，失败仍返回令牌。 |
| 任务 | Job 队列 | 能看任务、运行、重试、取消；数据库 lease 队列，可多机 `mangedong worker`。 |
| 设置 | SMTP / S3 / 会话 | 每个团队可配 SMTP 和 S3；密钥脱敏。 |

命令盘可打开次要页：链路向导、报表、合规下载、通知、帮助、P2。

## P0 逐项

| P0 | 状态 | 真人视角 |
| --- | --- | --- |
| 登录、团队、成员角色 | 完成 | 可用 |
| Project Brief | 完成 | 总览立项向导写入 Brief |
| WorkItem / ProductionGate | 完成 | API + 链路向导 + 总览改状态 |
| 章节/页面/分格 | 完成 | 导入后可在分格页看到 |
| 漫画导入 | 完成 | 可用 |
| 素材库 | 完成 | 资源页可看 |
| AI Provider / ComfyUI / Workflow | 完成（适配 + 回退） | 能配、能探活、能试跑；无密钥则本地回退 |
| 任务队列 | 完成 | 共享数据库 lease；API 可内嵌 worker，其他机器跑 `mangedong worker` |
| OCR / 分析 | 完成（live 或占位） | 有 Key 先打 chat completions，否则占位 |
| 参考上色 / 批量 | 完成（本地算法） | 产出真实 PNG |
| 单分格视频 | 完成（Ken Burns，可试 ComfyUI） | 先写本地 MP4，再尝试 `/prompt` |
| Shot / Animatic / 时间线 | 完成（对象 + 简易轨道） | Animatic 写出真实 MP4 |
| 片段预览/重生成/A/B | 完成 | 审片/分格可播；A/B 仍是 API |
| 台词 / 字幕 / TTS / BGM | 完成（本地 WAV/SRT） | 音频页可点生成 |
| 审核评论 | 完成 | 审片页按时间码批注 |
| 项目成本 | 完成（估算） | 报表页可见 |
| 导出包 / 交付前检查 / MP4 | 完成 | freeze 出本地 ZIP |

## 明确做不到（不要假装）

| 能力 | 现状 | 缺口 |
| --- | --- | --- |
| 任务队列 | 共享数据库 lease + heartbeat；可多机跑 `mangedong worker` | 不是 Redis/SQS |
| 对象存储 | 团队可配 S3 兼容（AWS/MinIO/R2）；未配则本地盘 | 需填 bucket/密钥才上云 |
| 邮件 | 团队可配 SMTP；邀请/重置会尝试发信 | 发信失败仍返回令牌 |
| ComfyUI | 局域网 URL + 内网穿透 URL；健康检查先探穿透地址 | 穿透未开则 fallback |
| 上色 | 本地 OpenCV LUT + PNG | 不是 ComfyUI 出图 |
| 视频 | 先写 Ken Burns MP4，再尝试 ComfyUI | 不是 TV 番剧级成片 |
| 邀请/重置 | 未注册邮箱可邀请并返回 token；配置 SMTP 后会发信 | 发信失败仍返回令牌 |
| 审片播放 | 审片页可播 MP4 并按时间码批注 | 不是专业 NLE |
| API Key 加密 | XOR+HMAC `enc:` 存库 | 不是 KMS/vault |

## P1 / P2

PDF 导入、分格手动修正、色彩策略、字幕翻译、错误日志：API 在，工作台覆盖了 PDF 导入、报表错误计数和分格生产。

私有化、云 ComfyUI 池、画布编辑、专业时间轴、实时协同、训练平台、ProRes/DCP：只有配置占位，不算完成。

## 验收口径

如果问「PRD V1 工作台能不能给工作室演示本地闭环」：可以。

如果问「是不是已经做完、可以卖」：没有。缺真实成片质量。SMTP/S3/多机队列已经可配置，但要填真实账号和共享数据库才能在多机上跑。
