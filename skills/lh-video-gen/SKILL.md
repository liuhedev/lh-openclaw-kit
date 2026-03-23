---
name: lh-video-gen
description: Generate vertical short videos (9:16) from a Markdown script. This is the main workflow skill for script-to-video tasks; it may internally use TTS or image-generation helpers.
homepage: https://github.com/liuhedev/lh-openclaw-kit
---

# Video-Gen Skill

从视频脚本 Markdown 文件一键生成竖版短视频（9:16）。

## 边界

- 本 skill 是“脚本转视频”主流程入口。
- 如果用户只要单独音频，不做视频，优先使用 `lh-edge-tts`。
- 如果用户只要单张封面、海报、信息卡片，不做视频，优先使用 `lh-html-to-image`。
- 当任务目标是完整视频产出时，优先使用本 skill，再按需调用配套 skill。

**核心思路：以图定音**
- 每段脚本的画面说明 -> 字幕卡片图
- 每段口播文案 -> TTS 配音
- 每张图展示时长 = 对应音频时长，音画天然同步

## 快速开始

```bash
python3 generate.py script.md -o content/articles/YYYY-MM-DD/resources/video/output.mp4
```

### 使用预制图片（跳过 Chrome 截图）

```bash
python3 generate.py script.md --images-dir content/articles/YYYY-MM-DD/resources/images -o content/articles/YYYY-MM-DD/resources/video/output.mp4
```

图片命名规则：`slide_01.png`, `slide_02.png`...，与脚本分段一一对应。

### 自定义 TTS 命令

```bash
python3 generate.py script.md --tts-command "my-tts {text} -o {output} -v {voice} -r {rate}"
```

占位符：`{text}` 口播文案、`{output}` 输出路径、`{voice}` 音色、`{rate}` 语速。

## 参数说明

```
python3 generate.py <脚本路径> [选项]

选项：
  -o, --output        输出 MP4 路径（必须显式传入；文章归属任务用 `content/articles/YYYY-MM-DD/resources/video/output.mp4`）
  -v, --voice         TTS 音色（默认：zh-CN-YunxiNeural）
  -r, --rate          语速（默认：+0%，如 +10%、-10%）
  -w, --width         视频宽度（默认：1080）
  --height            视频高度（默认：1920，9:16）
  --images-dir        使用已有图片目录，跳过 Chrome 截图
  --tts-command       自定义 TTS 命令模板（占位符：{text} {output} {voice} {rate}）
  --keep-temp         保留临时文件（图片、音频、片段）
  --no-subs           不烧录字幕
```

## 依赖

### 系统依赖

- **FFmpeg**：视频合成（`brew install ffmpeg`）
- **Chrome**：HTML 截图（仅在未使用 `--images-dir` 时需要）
  - 自动检测 macOS/Linux 常见路径，或通过 `CHROME_PATH` 环境变量指定

### 推荐搭配的 Skill

以下 Skill 非必需，但搭配使用效果更佳：

- **lh-edge-tts**：配套音频能力，不是视频任务主入口。自动检测同级目录 `../lh-edge-tts/scripts/tts_converter.py`，或通过 `EDGE_TTS_PATH` 环境变量指定，或用 `--tts-command` 替换为任意 TTS 工具
- **lh-html-to-image**：配套出图能力，不是视频任务主入口。如需自定义更复杂的字幕卡片，可用此 Skill 生成图片后通过 `--images-dir` 传入

## 脚本格式

用 `---` 分隔各段，每段包含 `**口播**`、`**字幕**`、`**画面**` 字段：

```markdown
# 视频标题

---

## 开场
**画面**：场景描述
**口播**：TTS 配音文案
**字幕**：屏幕显示文字\n支持换行

---

## 结尾
**画面**：场景描述
**口播**：TTS 配音文案
**字幕**：屏幕显示文字
```

完整模板：`templates/script-template.md`

## 工作流程

1. 解析脚本 Markdown，提取各分段
2. 每段口播 -> TTS 生成 mp3
3. 每段字幕 -> HTML 模板截图生成 9:16 图片（或从 `--images-dir` 加载）
4. 每张图 + 对应音频 -> FFmpeg 合成视频片段
5. 拼接所有片段 -> 输出 MP4
