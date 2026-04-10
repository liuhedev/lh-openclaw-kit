---
name: lh-video-gen
description: |
  从 Markdown 脚本一键生成竖版短视频（9:16）。当用户提到"生成短视频"、"脚本转视频"、"重新渲染视频"、"适配微信视频号"、"视频号竖版"、"横版截图变形"、"图片拼配音生成 MP4"时，必须使用本 skill。
  本 skill 是脚本转视频的主流程入口，可内部调用 lh-edge-tts 和 lh-html-to-image 配合使用。
metadata:
  openclaw:
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
python3 {baseDir}/scripts/generate.py script.md -o content/articles/YYYY-MM-DD/resources/video/output.mp4
```

### 使用预制图片（跳过 Chrome 截图）

```bash
python3 {baseDir}/scripts/generate.py script.md --images-dir content/articles/YYYY-MM-DD/resources/images -o content/articles/YYYY-MM-DD/resources/video/output.mp4
```

图片命名规则：`slide_01.png`, `slide_02.png`...，与脚本分段一一对应。

### 使用前端幻灯片画面（推荐用于视频号）

```bash
python3 {baseDir}/scripts/generate.py script.md \
  --visual-mode frontend \
  --platform wechat-channel \
  -o content/articles/YYYY-MM-DD/resources/video/output-wechat.mp4
```

行为：
- 先按 `frontend-slides` 思路把每段脚本组织成多页 HTML 幻灯片
- 再按 `frontend-design` 风格生成高质感页面
- 最后自动截图为 `slide_01.png`... 并继续合成视频

### 适配微信视频号（处理横版截图，避免变形）

```bash
python3 {baseDir}/scripts/generate.py script.md \
  --images-dir content/articles/YYYY-MM-DD/resources/images \
  --platform wechat-channel \
  -o content/articles/YYYY-MM-DD/resources/video/output-wechat.mp4
```

规则：
- 成片保持 `1080x1920`（9:16）
- 已经是竖版素材时直接复用
- 横版截图自动包进竖版容器：背景模糊铺满，前景按比例缩放并居中
- 禁止直接拉伸横图

### 自定义 TTS 命令

```bash
python3 {baseDir}/scripts/generate.py script.md --tts-command "my-tts {text} -o {output} -v {voice} -r {rate}"
```

占位符：`{text}` 口播文案、`{output}` 输出路径、`{voice}` 音色、`{rate}` 语速。

## 参数说明

```
python3 {baseDir}/scripts/generate.py <脚本路径> [选项]

选项：
  -o, --output        输出 MP4 路径（默认：`tmp/video-output.mp4`；文章归属任务建议显式传 `content/articles/YYYY-MM-DD/resources/video/output.mp4`）
  -v, --voice         TTS 音色（默认：zh-CN-YunxiNeural）
  -r, --rate          语速（默认：+0%，如 +10%、-10%）
  -w, --width         视频宽度（默认：1080）
  --height            视频高度（默认：1920，9:16）
  --images-dir        使用已有图片目录，跳过 Chrome 截图
  --platform          输出平台：generic | wechat-channel（视频号适配）
  --tts-command       自定义 TTS 命令模板（占位符：{text} {output} {voice} {rate}）
  --visual-mode       画面模式：basic | frontend | auto
  --frontend-dir      frontend 模式输出目录（HTML 幻灯片 + render 图片）
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
- **frontend-slides**：用于把视频脚本拆成多页前端幻灯片结构，适合讲解型视频
- **frontend-design**：用于提升多页幻灯片的视觉质感，适合对外发布和视频号风格内容

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

完整模板：`{baseDir}/templates/script-template.md`

## 工作流程

1. 解析脚本 Markdown，提取各分段
2. 选择画面模式：`basic` / `frontend` / `auto`
3. `basic` 模式：每段字幕 -> HTML 模板截图生成 9:16 图片
4. `frontend` 模式：先生成前端幻灯片页面，再自动截图为 `slide_01.png...`
5. 每段口播 -> TTS 生成 mp3
6. 如果 `platform=wechat-channel` 且发现横版截图，先包进 1080×1920 竖版容器，避免拉伸变形
7. 每张图 + 对应音频 -> FFmpeg 合成视频片段
8. 拼接所有片段 -> 输出 MP4
