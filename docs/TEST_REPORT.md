# 测试报告

## 测试时间

- 运行命令：`python3 -m pytest`
- 测试范围：CLI 管道、Web SaaS API、Web 工作台页面
- 测试结果：10 passed

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
- 章节、页面、分格创建
- OCR 占位任务
- AI 分析占位任务
- 参考上色占位任务
- 批量上色任务
- 单分格视频生成
- Shot 创建
- Animatic 生成
- Timeline 创建
- TimelineItem 添加
- DialogueLine 创建
- VoiceLine 生成
- SubtitleCue 创建
- MusicCue 创建
- AudioMix 创建
- ReviewComment 创建
- QCReport 创建
- Export 创建
- Export preflight
- Export freeze
- AI Workflow Center 页面渲染
- Review / Export 页面渲染

## 最近一次测试输出

```text
collected 10 items

tests/test_api.py ....                                                   [ 44%]
tests/test_pages.py ..                                                   [ 60%]
tests/test_pipeline.py ...                                               [ 90%]
tests/test_prd_flow.py .                                                 [100%]

10 passed
```

## 当前测试结论

- 本轮新增后端生产对象通过 API 自动化测试。
- 本轮新增 Web 工作台页面通过页面自动化测试。
- PRD P0 主链路通过端到端 API + 页面自动化测试。
- 既有漫画转动漫 CLI 管道未出现回归。
- 当前测试不只是接口测试，已包含对应 Web 页面渲染自动化测试。

## 后续测试建议

- 引入浏览器级端到端测试，覆盖真实表单提交和页面跳转。
- 在对象存储和文件上传接入后，增加上传、预览和导入任务测试。
- 在 ComfyUI 接入后，增加 mock ComfyUI server 合约测试。
- 在 worker 接入后，增加任务重试、取消、失败恢复和并发测试。
