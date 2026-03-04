---
name: lh-video-gen
description: 从视频脚本 md 文件一键生成视频号短视频（30-60秒竖版 9:16）。解析脚本分段，用 Edge-TTS 生成配音，用 HTML 截图或 AI 图片生成字幕卡片，用 FFmpeg 合成音画同步的 MP4。支持 --ai-images 模式（baoyu-image-gen 生成背景图，字幕叠加）。
---

# Video-Gen Skill

## 概述

从视频脚本 Markdown 文件一键生成视频号竖版短视频（9:16）。

**核心思路：以图定音**
- 从每个脚本的画面说明出发生成字幕卡片图
- 从脚本的口播文案生成 TTS 配音
- 每张图展示时长 = 对应音频时长，音画天然同步

## 画面生成模式

| 模式 | 工具链 | 风格 | 成本 | 适用场景 |
|------|--------|------|------|---------|
| **默认** | HTML 模板截图 | 深蓝渐变 + 白字 | 零 | 快速出片 |
| **AI 背景** (`--ai-images`) | baoyu-image-gen 直出 | 由提示词决定 | API | 需要丰富画面 |
| **Notion 简约**（推荐） | `baoyu-xhs-images --style notion --layout flow` → baoyu-image-gen | 白底简约信息图 | API | 日常打工日记 |

**推荐流程**：用 `baoyu-xhs-images` 生成高质量提示词再出图，比 `--ai-images` 直接用画面描述做提示词质量更高。

## 视频号内容规范

详见脚本模板 `templates/script-template.md`（SSoT），核心要求在设计脚本阶段落地：
- 开场带热词、结尾引导关注"刘贺同学"、时长/字幕限制

## 工作流程

1. **解析脚本**：从 md 文件提取分段（开场/核心/结尾等）
2. **生成配音**：每段文案用 `lh-edge-tts` 生成 mp3
3. **生成图片**：每段字幕用 `lh-html-to-image` 生成 9:16 字幕卡
4. **合成片段**：每张图 + 对应音频 = 独立视频片段
5. **拼接视频**：拼接所有片段，烧录字幕，输出 MP4

## 快速开始

### 准备脚本文件

创建符合格式的 Markdown 脚本，参考 `templates/script-template.md`：

```markdown
# 视频标题

---

## 开场
**画面**：龙虾哥头像 + 大标题"AI发图发成了路径字符串？"
**口播**：用 OpenClaw 发飞书图片，结果发出去一串文件路径字符串...当场石化。
**字幕**：用 OpenClaw 发飞书图片\n结果发出去一串文件路径字符串\n当场石化

---

## 核心坑
**画面**：代码片段 + 红色叉号标记
**口播**：原来 message 工具发图片会当文本发，得自己写脚本调飞书 API 才能传图片。
**字幕**：message 工具发图片会当文本发
得自己写脚本调飞书 API 才能传图片

---

## 结尾
**画面**：GitHub Issue 截图 + 大拇指
**口播**：顺手给 OpenClaw 提了个 Issue，开源社区嘛，踩坑就得反馈。
**字幕**：顺手给 OpenClaw 提了个 Issue
开源社区嘛，踩坑就得反馈
```

注意：字幕中的换行用 `\n` 表示。

### 执行生成

```bash
cd ~/.openclaw/skills/lh-video-gen/scripts
python3 generate.py /path/to/your/script.md -o output.mp4
```

### AI 图片生成模式（更有视觉冲击力）

启用后，每个分段的  字段会作为提示词，由  生成 9:16 背景图，字幕叠加其上：

```bash
python3 generate.py script.md -o output.mp4 --ai-images
# 指定服务商
python3 generate.py script.md -o output.mp4 --ai-images --image-provider dashscope
```

> ⚠️ AI 图片生成较慢（每张约 10-30 秒），且消耗 API 额度。

### 参数说明

```bash
python3 generate.py <脚本路径> [选项]

选项：
  -o, --output        输出 MP4 路径（默认：tmp/video-output.mp4）
  -v, --voice         TTS 音色（默认：zh-CN-YunxiNeural）
  -r, --rate          语速（默认：+0%，如 +10%、-10%）
  -w, --width         视频宽度（默认：1080）
  -h, --height        视频高度（默认：1920，9:16）
  --keep-temp         保留临时文件（图片、音频、片段）
  --no-subs           不烧录字幕
  --ai-images         启用 AI 图片生成模式（用 baoyu-image-gen 生成背景图，再叠加字幕）
  --image-provider    AI 图片服务商：openai / google / dashscope（默认读 EXTEND.md 配置）
  --help              显示帮助信息
```

## 输出文件

执行后生成：

- `output.mp4`：最终视频
- `tmp/video-gen-temp/`：临时文件（如未清理）
  - `audio_01.mp3`, `audio_02.mp3`, ...
  - `slide_01.png`, `slide_02.png`, ...
  - `seg_01.mp4`, `seg_02.mp4`, ...
  - `concat_list.txt`

## 脚本格式规范

### 必需字段

每个分段必须包含：
- `**口播**`：TTS 配音文案（中文）
- `**字幕**`：字幕卡片文案（支持 `\n` 换行）
- `**画面**`：画面说明（用于 HTML 模板中的装饰元素，可选）

### 分段分隔

使用 `---` 分隔不同分段（开场/核心/结尾等）

### 示例完整脚本

```markdown
# Day10 视频号脚本：飞书发图踩坑记

---

## 开场
**画面**：龙虾哥头像 + 大标题"AI发图发成了路径字符串？"
**口播**：用 OpenClaw 发飞书图片，结果发出去一串文件路径字符串...当场石化。
**字幕**：用 OpenClaw 发飞书图片\n结果发出去一串文件路径字符串\n当场石化

---

## 核心坑
**画面**：代码片段 + 红色叉号标记
**口播**：原来 message 工具发图片会当文本发，得自己写脚本调飞书 API 才能传图片。
**字幕**：message 工具发图片会当文本发
得自己写脚本调飞书 API 才能传图片

---

## 结尾
**画面**：GitHub Issue 截图 + 大拇指
**口播**：顺手给 OpenClaw 提了个 Issue，开源社区嘛，踩坑就得反馈。
**字幕**：顺手给 OpenClaw 提了个 Issue
开源社区嘛，踩坑就得反馈
```

## 技术依赖

### 依赖的 Skill

- **lh-edge-tts**：TTS 配音生成
  - 路径：`~/.openclaw/skills/lh-edge-tts/scripts/tts_converter.py`

- **lh-html-to-image**：HTML 截图生成字幕卡
  - 使用 `templates/slide.html` 模板

### 系统依赖

- **FFmpeg**：视频合成
  - 安装：`brew install ffmpeg`
  - 验证：`ffmpeg -version`

- **Chrome**：HTML 截图（headless 模式）
  - 路径：`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` (macOS)

### Python 依赖

```bash
pip install edge-tts
```

## 核心实现

### 脚本解析

用正则表达式从 md 文件提取：
- 段落标题（`## 标题`）
- 口播文案（`**口播**：` 后的内容）
- 字幕文案（`**字幕**：` 后的内容）
- 画面说明（`**画面**：` 后的内容）

### TTS 生成

调用 `lh-edge-tts/scripts/tts_converter.py`：
```python
tts_script = "~/.openclaw/skills/lh-edge-tts/scripts/tts_converter.py"
cmd = f"python3 {tts_script} '{dialogue}' -v {voice} -r {rate} -o {audio_output}"
```

### 图片生成

1. 读取 `templates/slide.html` 模板
2. 填充字幕文案、画面说明
3. 用 Chrome headless 截图：
```bash
chrome --headless=new --screenshot="{output}.png" --window-size={width},{height} "{html_file}"
```

### 视频合成

#### 步骤1：图 + 音频合成片段
```bash
ffmpeg -loop 1 -i slide.png -i audio.mp3 \
  -c:v libx264 -tune stillimage -c:a aac -pix_fmt yuv420p -shortest segment.mp4
```

#### 步骤2：拼接片段
创建 `concat_list.txt`：
```
file 'seg_01.mp4'
file 'seg_02.mp4'
...
```

```bash
ffmpeg -f concat -safe 0 -i concat_list.txt -c copy combined.mp4
```

#### 步骤3：烧录字幕（可选）
将字幕渲染为图片叠加到视频上（字幕卡已包含字幕，此步骤主要用于增强）

## 常用音色

| 音色 | 风格 | 适用场景 |
|------|------|---------|
| `zh-CN-YunxiNeural` | 男，自然 | 默认推荐 |
| `zh-CN-XiaoxiaoNeural` | 女，亲切 | 轻松内容 |
| `zh-CN-YunyangNeural` | 男，新闻 | 专业解说 |

查看完整音色列表：
```bash
python3 ~/.openclaw/skills/lh-edge-tts/scripts/tts_converter.py --list-voices --lang-filter zh
```

## 常见问题

### Q: 音画不同步
**A:** 确保使用 `-shortest` 参数，视频时长以音频为准

### Q: 视频在手机上无法播放
**A:** 添加 `-pix_fmt yuv420p` 参数确保兼容性

### Q: 字幕字体模糊
**A:** 使用 `--force-device-scale-factor=2` 提高截图清晰度

### Q: Chrome 截图报错 GPU 问题
**A:** 添加 `--disable-gpu` 参数，可忽略 GPU 错误日志

## 示例输出

```bash
$ python3 generate.py video-script.md -o demo.mp4

[1/3] 解析脚本... 3 个分段
[2/3] 生成素材...
  - 分段 1（开场）：生成配音 mp3... 3.2s，生成字幕卡... ✓
  - 分段 2（核心坑）：生成配音 mp3... 4.1s，生成字幕卡... ✓
  - 分段 3（结尾）：生成配音 mp3... 2.8s，生成字幕卡... ✓
[3/3] 合成视频...
  - 合成片段：seg_01.mp4... ✓
  - 合成片段：seg_02.mp4... ✓
  - 合成片段：seg_03.mp4... ✓
  - 拼接视频：demo.mp4... ✓

✅ 完成！输出：demo.mp4（总时长：10.1秒）
```

## 脚本模板

完整脚本模板：`templates/script-template.md`

复制模板：
```bash
cp ~/.openclaw/skills/lh-video-gen/templates/script-template.md my-video.md
```

## 注意事项

- 字幕文案中的换行使用 `\n`（Markdown 不会渲染换行）
- 每段口播建议 5-15 秒（10-30 字），太长画面撑不住
- 临时文件默认清理，需要调试时加 `--keep-temp`
- 视频尺寸固定为 9:16（1080×1920），适配视频号/抖音
