#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video-Gen: 从脚本 Markdown 生成视频号竖版短视频

依赖：
- lh-edge-tts/scripts/tts_converter.py
- templates/slide.html
- FFmpeg
- Chrome headless
"""

import os
import re
import sys
import json
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# 配置常量
SKILL_DIR = Path(os.path.expanduser("~/.openclaw/skills/lh-video-gen"))
TEMPLATES_DIR = SKILL_DIR / "templates"
SCRIPTS_DIR = SKILL_DIR / "scripts"

# 依赖工具路径
TTS_CONVERTER = Path(os.path.expanduser("~/.openclaw/skills/lh-edge-tts/scripts/tts_converter.py"))
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TEMPLATE_HTML = TEMPLATES_DIR / "slide.html"
TEMPLATE_AI_BG_HTML = TEMPLATES_DIR / "slide-ai-bg.html"
IMAGE_GEN_SKILL_DIR = Path(os.path.expanduser("~/.openclaw/skills/baoyu-image-gen"))

# 默认配置
DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1920  # 9:16 竖版
DEFAULT_VOICE = "zh-CN-YunxiNeural"
DEFAULT_RATE = "+0%"
DEFAULT_OUTPUT = "tmp/video-output.mp4"
TEMP_DIR = "tmp/video-gen-temp"


def parse_args():
    parser = argparse.ArgumentParser(
        description="从脚本 Markdown 生成视频号竖版短视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python3 generate.py script.md -o output.mp4
  python3 generate.py script.md -v zh-CN-XiaoxiaoNeural -r +10%
  python3 generate.py script.md --keep-temp --no-subs
        """
    )
    parser.add_argument("script", help="脚本 Markdown 文件路径")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT, help=f"输出 MP4 路径（默认：{DEFAULT_OUTPUT}）")
    parser.add_argument("-v", "--voice", default=DEFAULT_VOICE, help=f"TTS 音色（默认：{DEFAULT_VOICE}）")
    parser.add_argument("-r", "--rate", default=DEFAULT_RATE, help=f"语速（默认：{DEFAULT_RATE}，如 +10%、-10%）")
    parser.add_argument("-w", "--width", type=int, default=DEFAULT_WIDTH, help=f"视频宽度（默认：{DEFAULT_WIDTH}）")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help=f"视频高度（默认：{DEFAULT_HEIGHT}）")
    parser.add_argument("--keep-temp", action="store_true", help="保留临时文件")
    parser.add_argument("--no-subs", action="store_true", help="不烧录字幕（字幕已渲染在图片中）")
    parser.add_argument("--ai-images", action="store_true", help="启用 AI 图片生成模式（用 baoyu-image-gen 生成背景图）")
    parser.add_argument("--image-provider", default=None, choices=["openai", "google", "dashscope"], help="AI 图片生成服务商（默认读 EXTEND.md 配置）")
    return parser.parse_args()


def check_dependencies():
    """检查依赖工具是否可用"""
    deps = {
        "FFmpeg": "ffmpeg",
        "Chrome": CHROME_PATH,
        "TTS Converter": str(TTS_CONVERTER),
    }

    missing = []
    for name, path in deps.items():
        if name == "FFmpeg":
            try:
                subprocess.run([path, "-version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing.append(f"{name}（需安装：brew install ffmpeg）")
        elif name == "Chrome":
            if not os.path.exists(path):
                missing.append(f"{name}（路径：{path}）")
        elif name == "TTS Converter":
            if not os.path.exists(path):
                missing.append(f"{name}（路径：{path}）")

    if missing:
        print(f"❌ 缺少依赖：\n  " + "\n  ".join(missing))
        sys.exit(1)

    # 检查模板
    if not os.path.exists(TEMPLATE_HTML):
        print(f"❌ 模板文件不存在：{TEMPLATE_HTML}")
        sys.exit(1)


def parse_script(script_path):
    """解析脚本 Markdown 文件"""
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 按分段分割（--- 分隔符）
    sections_raw = re.split(r"^---+$", content, flags=re.MULTILINE)
    sections = []

    for section in sections_raw:
        section = section.strip()
        if not section:
            continue

        # 提取标题
        title_match = re.search(r"^#+\s*(.+)$", section, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else "未命名"

        # 提取口播
        dialogue_match = re.search(r"\*\*口播\*\*[:：]\s*(.+?)(?=\\n\\n|\*\*|$)", section, re.DOTALL)
        dialogue = dialogue_match.group(1).strip() if dialogue_match else ""

        # 提取字幕
        subtitle_match = re.search(r"\*\*字幕\*\*[:：]\s*(.+?)(?=\\n\\n|\*\*|$)", section, re.DOTALL)
        subtitle = subtitle_match.group(1).strip() if subtitle_match else ""

        # 提取画面说明
        visual_match = re.search(r"\*\*画面\*\*[:：]\s*(.+?)(?=\\n\\n|\*\*|$)", section, re.DOTALL)
        visual = visual_match.group(1).strip() if visual_match else ""

        if dialogue or subtitle:  # 只要有口播或字幕就算有效分段
            sections.append({
                "title": title,
                "dialogue": dialogue,
                "subtitle": subtitle,
                "visual": visual,
            })

    if not sections:
        print("❌ 未解析到有效分段，请检查脚本格式")
        sys.exit(1)

    return sections


def generate_audio(dialogue, output_path, voice, rate):
    """用 lh-edge-tts 生成配音"""
    cmd = [
        "python3", str(TTS_CONVERTER),
        dialogue,
        "-v", voice,
        "-r", rate,
        "-o", output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ TTS 生成失败：{result.stderr}")
        sys.exit(1)

    return output_path


def generate_slide(subtitle, visual, output_path, width, height, index):
    """用 HTML 截图生成字幕卡片"""
    # 读取模板
    with open(TEMPLATE_HTML, "r", encoding="utf-8") as f:
        template = f.read()

    # 替换占位符
    # 处理字幕换行（\n -> <br>）
    subtitle_html = subtitle.replace("\\n", "<br>")
    subtitle_html = subtitle_html.replace("\n", "<br>")

    # 处理画面说明
    visual_html = visual.replace("\\n", "<br>")
    visual_html = visual_html.replace("\n", "<br>")

    html = template.replace("{{SUBTITLE}}", subtitle_html)
    html = html.replace("{{VISUAL}}", visual_html)
    html = html.replace("{{INDEX}}", str(index))

    # 写入临时 HTML 文件
    temp_html = Path(output_path).with_suffix(".html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html)

    # 用 Chrome headless 截图
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--screenshot=" + str(output_path),
        "--window-size=" + f"{width},{height}",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "file://" + str(temp_html.absolute()),
    ]

    subprocess.run(cmd, capture_output=True)

    # 清理临时 HTML
    temp_html.unlink()

    if not os.path.exists(output_path):
        print(f"❌ 图片生成失败：{output_path}")
        sys.exit(1)

    return output_path



def generate_ai_slide(subtitle, visual, output_path, width, height, index, image_provider=None):
    """用 AI 生成背景图，再叠加字幕，生成字幕卡片"""
    # 1. 组装 AI 图片提示词
    prompt_suffix = "，9:16竖版构图，适合短视频背景，电影感光线，高质量"
    base_prompt = visual if visual else "简洁抽象背景，适合科技类短视频"
    prompt = base_prompt + prompt_suffix

    # 2. 调用 baoyu-image-gen 生成背景图
    bg_image_path = Path(output_path).with_suffix(".bg.png")
    cmd = [
        "npx", "-y", "bun",
        str(IMAGE_GEN_SKILL_DIR / "scripts" / "main.ts"),
        "--prompt", prompt,
        "--image", str(bg_image_path),
        "--ar", "9:16",
    ]
    if image_provider:
        cmd += ["--provider", image_provider]

    print(f"    AI 生成背景图...", end="", flush=True)
    env = {**os.environ, "SKILL_DIR": str(IMAGE_GEN_SKILL_DIR)}
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0 or not bg_image_path.exists():
        print(f" ❌ AI 图片生成失败（{result.stderr[:200]}），回退到普通字幕卡")
        return generate_slide(subtitle, visual, output_path, width, height, index)
    print(" ✓")

    # 3. 读取 AI 背景模板
    with open(TEMPLATE_AI_BG_HTML, "r", encoding="utf-8") as f:
        template = f.read()

    # 转为 file:// URI（绝对路径）
    bg_uri = "file://" + str(bg_image_path.absolute())

    subtitle_html = subtitle.replace("\\n", "<br>").replace("\n", "<br>")

    html = template.replace("{{BG_IMAGE}}", bg_uri)
    html = html.replace("{{SUBTITLE}}", subtitle_html)
    html = html.replace("{{INDEX}}", str(index))

    # 写临时 HTML 并截图
    temp_html = Path(output_path).with_suffix(".html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html)

    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--screenshot=" + str(output_path),
        "--window-size=" + f"{width},{height}",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "file://" + str(temp_html.absolute()),
    ]
    subprocess.run(cmd, capture_output=True)
    temp_html.unlink()

    if not os.path.exists(output_path):
        print(f"❌ 字幕卡生成失败：{output_path}")
        sys.exit(1)

    return output_path

def get_audio_duration(audio_path):
    """获取音频时长（秒）"""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        audio_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def compose_segment(image_path, audio_path, output_path):
    """图 + 音频合成视频片段"""
    cmd = [
        "ffmpeg",
        "-y",  # 覆盖输出
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ 片段合成失败：{result.stderr}")
        sys.exit(1)

    return output_path


def concat_segments(segment_paths, output_path):
    """拼接多个视频片段"""
    # 创建 concat 列表
    concat_list = Path(output_path).parent / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for seg in segment_paths:
            # 使用绝对路径避免相对路径问题
            f.write(f"file '{seg.absolute()}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        output_path,
    ]

    # 修正命令（ffmpeg 不接受两次路径参数）
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ 视频拼接失败：{result.stderr}")
        sys.exit(1)

    # 清理 concat 列表
    if concat_list.exists():
        concat_list.unlink()

    return output_path


def get_video_duration(video_path):
    """获取视频时长（秒）"""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        video_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def main():
    args = parse_args()

    # 检查依赖
    check_dependencies()

    # 创建临时目录
    temp_dir = Path(args.output).parent / TEMP_DIR
    temp_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"🎬 Video-Gen: 从脚本生成视频")
    print(f"{'='*60}\n")

    # 解析脚本
    print("[1/3] 解析脚本...")
    sections = parse_script(args.script)
    print(f"  ✅ 解析到 {len(sections)} 个分段")

    # 生成素材
    print("\n[2/3] 生成素材...")
    audio_files = []
    image_files = []
    segment_files = []

    for i, section in enumerate(sections, 1):
        print(f"\n  - 分段 {i}（{section['title']}）：")

        # 生成配音
        audio_output = temp_dir / f"audio_{i:02d}.mp3"
        print(f"    生成配音 mp3...", end="", flush=True)
        generate_audio(section["dialogue"], str(audio_output), args.voice, args.rate)
        duration = get_audio_duration(str(audio_output))
        print(f" {duration:.1f}s ✓")

        audio_files.append(audio_output)

        # 生成字幕卡
        image_output = temp_dir / f"slide_{i:02d}.png"
        if args.ai_images:
            generate_ai_slide(section["subtitle"], section["visual"], str(image_output),
                              args.width, args.height, i, args.image_provider)
        else:
            print(f"    生成字幕卡...", end="", flush=True)
            generate_slide(section["subtitle"], section["visual"], str(image_output),
                           args.width, args.height, i)
            print(" ✓")

        image_files.append(image_output)

        # 合成片段
        segment_output = temp_dir / f"seg_{i:02d}.mp4"
        compose_segment(str(image_output), str(audio_output), str(segment_output))
        segment_files.append(segment_output)

    # 合成视频
    print("\n[3/3] 合成视频...")

    # 拼接片段
    print(f"  拼接视频：{args.output}...", end="", flush=True)
    concat_segments(segment_files, args.output)
    print(" ✓")

    # 获取总时长
    total_duration = get_video_duration(args.output)

    # 清理临时文件
    if not args.keep_temp:
        print(f"\n  清理临时文件：{temp_dir}", end="", flush=True)
        shutil.rmtree(temp_dir)
        print(" ✓")

    print(f"\n{'='*60}")
    print(f"✅ 完成！输出：{args.output}")
    print(f"   总时长：{total_duration:.1f}秒")
    print(f"   画幅：{args.width}×{args.height}（{(args.height/args.width):.2f}:1）")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
