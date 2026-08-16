# mangedong

`mangedong` 是一个从黑白漫画生成动漫风格视频的最小可运行项目骨架。当前版本先打通主链路：

1. 导入漫画页：支持单张图片、图片目录、CBZ/ZIP 漫画包。
2. 上色：内置确定性的动漫风格算法上色器，后续可替换为本地模型或 API。
3. 动画：用 Ken Burns 镜头运动和轻微明暗变化生成帧序列。
4. 导出：将帧序列编码为 H.264 MP4，并输出 manifest 记录产物。

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

## 后续扩展方向

- 将 `AlgorithmicColorizer` 替换为漫画上色模型或第三方 API 适配器。
- 在动画阶段接入图生视频模型，并保留当前帧导出作为降级方案。
- 为 Web 预览、任务队列、字幕、音轨、角色色板和批量章节处理增加独立模块。
