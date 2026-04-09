#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video-Gen: 从脚本 Markdown 生成视频号竖版短视频

依赖：
- TTS 工具（推荐 lh-edge-tts）
- templates/slide.html
- FFmpeg
- Chrome headless（仅在未提供 --images-dir 时需要）
"""

import os
import re
import sys
import json
import shlex
import shutil
import subprocess
import argparse
from pathlib import Path
from PIL import Image

# 路径自动检测（相对于脚本位置）
SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"
TEMPLATE_HTML = TEMPLATES_DIR / "slide.html"

# 默认配置
DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1920  # 9:16 竖版
DEFAULT_VOICE = "zh-CN-YunxiNeural"
DEFAULT_RATE = "+0%"
DEFAULT_OUTPUT = "tmp/video-output.mp4"
TEMP_DIR = "tmp/video-gen-temp"
DEFAULT_PLATFORM = "generic"
WECHAT_CHANNEL_PLATFORM = "wechat-channel"
DEFAULT_VISUAL_MODE = "basic"
VISUAL_MODE_FRONTEND = "frontend"
VISUAL_MODE_AUTO = "auto"


def _detect_tts():
    """自动检测 lh-edge-tts 路径"""
    sibling = SKILL_DIR.parent / "lh-edge-tts" / "scripts" / "tts_converter.py"
    if sibling.exists():
        return str(sibling)
    env_path = os.environ.get("EDGE_TTS_PATH")
    if env_path and Path(env_path).exists():
        return env_path
    return None


def _detect_chrome():
    """自动检测 Chrome 路径"""
    env_path = os.environ.get("CHROME_PATH")
    if env_path:
        if os.path.exists(env_path) or shutil.which(env_path):
            return env_path
    mac_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(mac_path):
        return mac_path
    for name in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]:
        found = shutil.which(name)
        if found:
            return found
    return None


def parse_args():
    parser = argparse.ArgumentParser(
        description="从脚本 Markdown 生成视频号竖版短视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python3 generate.py script.md -o output.mp4
  python3 generate.py script.md -v zh-CN-XiaoxiaoNeural -r +10%
  python3 generate.py script.md --images-dir ./slides --keep-temp
  python3 generate.py script.md --tts-command "my-tts {text} -o {output}"
        """
    )
    parser.add_argument("script", help="脚本 Markdown 文件路径")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT, help=f"输出 MP4 路径（默认：{DEFAULT_OUTPUT}）")
    parser.add_argument("-v", "--voice", default=DEFAULT_VOICE, help=f"TTS 音色（默认：{DEFAULT_VOICE}）")
    parser.add_argument("-r", "--rate", default=DEFAULT_RATE, help="TTS rate, e.g. +10%%, -10%%")
    parser.add_argument("-w", "--width", type=int, default=DEFAULT_WIDTH, help=f"视频宽度（默认：{DEFAULT_WIDTH}）")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help=f"视频高度（默认：{DEFAULT_HEIGHT}）")
    parser.add_argument("--keep-temp", action="store_true", help="保留临时文件")
    parser.add_argument("--no-subs", action="store_true", help="不烧录字幕（字幕已渲染在图片中）")
    parser.add_argument("--images-dir", default=None,
                        help="使用已有图片目录（slide_01.png, slide_02.png...），跳过图片生成")
    parser.add_argument("--platform", default=DEFAULT_PLATFORM,
                        choices=[DEFAULT_PLATFORM, WECHAT_CHANNEL_PLATFORM],
                        help=f"输出平台（默认：{DEFAULT_PLATFORM}；视频号用：{WECHAT_CHANNEL_PLATFORM}）")
    parser.add_argument("--tts-command", default=None,
                        help="自定义 TTS 命令模板，占位符：{text} {output} {voice} {rate}。"
                             "默认自动检测 lh-edge-tts 或 EDGE_TTS_PATH 环境变量")
    parser.add_argument("--template", default=None,
                        help="HTML 模板文件名（不含 .html 后缀），位于 templates/ 目录。"
                             "默认：slide（即 templates/slide.html）")
    parser.add_argument("--visual-mode", default=DEFAULT_VISUAL_MODE,
                        choices=[DEFAULT_VISUAL_MODE, VISUAL_MODE_FRONTEND, VISUAL_MODE_AUTO],
                        help="画面生成模式：basic=默认字幕卡，frontend=前端幻灯片模式，auto=按平台自动选择")
    parser.add_argument("--frontend-dir", default=None,
                        help="前端幻灯片输出目录。frontend 模式下会在该目录生成 preview.html 和 render/slide_XX.png")
    return parser.parse_args()


def resolve_visual_mode(args):
    if args.visual_mode == VISUAL_MODE_AUTO:
        return VISUAL_MODE_FRONTEND if args.platform == WECHAT_CHANNEL_PLATFORM else DEFAULT_VISUAL_MODE
    return args.visual_mode


def check_dependencies(args):
    """检查依赖工具是否可用"""
    missing = []
    visual_mode = resolve_visual_mode(args)

    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing.append("FFmpeg（需安装：brew install ffmpeg）")

    if not args.tts_command and not _detect_tts():
        missing.append("TTS（安装 lh-edge-tts 到同级目录，或设置 EDGE_TTS_PATH 环境变量）")

    if visual_mode == VISUAL_MODE_FRONTEND:
        try:
            import playwright  # noqa: F401
        except ImportError:
            missing.append("playwright（frontend 模式需要：pip install playwright）")
    elif not args.images_dir:
        if not _detect_chrome():
            missing.append("Chrome（安装 Google Chrome，或设置 CHROME_PATH 环境变量）")
        template_path = TEMPLATES_DIR / f"{args.template}.html" if args.template else TEMPLATE_HTML
        if not template_path.exists():
            missing.append(f"模板文件（{template_path}）")

    if missing:
        print("缺少依赖：\n  " + "\n  ".join(missing))
        sys.exit(1)


def parse_script(script_path):
    """解析脚本 Markdown 文件"""
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    sections_raw = re.split(r"^---+$", content, flags=re.MULTILINE)
    sections = []

    for section in sections_raw:
        section = section.strip()
        if not section:
            continue

        title_match = re.search(r"^#+\s*(.+)$", section, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else "未命名"

        dialogue_match = re.search(r"\*\*口播\*\*[:：]\s*(.+?)(?=\\n\\n|\*\*|$)", section, re.DOTALL)
        dialogue = dialogue_match.group(1).strip() if dialogue_match else ""

        subtitle_match = re.search(r"\*\*字幕\*\*[:：]\s*(.+?)(?=\\n\\n|\*\*|$)", section, re.DOTALL)
        subtitle = subtitle_match.group(1).strip() if subtitle_match else ""

        visual_match = re.search(r"\*\*画面\*\*[:：]\s*(.+?)(?=\\n\\n|\*\*|$)", section, re.DOTALL)
        visual = visual_match.group(1).strip() if visual_match else ""

        if dialogue or subtitle:
            sections.append({
                "title": title,
                "dialogue": dialogue,
                "subtitle": subtitle,
                "visual": visual,
            })

    if not sections:
        print("未解析到有效分段，请检查脚本格式")
        sys.exit(1)

    return sections


def generate_audio(dialogue, output_path, voice, rate, tts_command=None, max_retries=3):
    """生成配音（带重试）"""
    import time as _time
    for attempt in range(1, max_retries + 1):
        if tts_command:
            cmd_str = tts_command.format(
                text=shlex.quote(dialogue),
                output=shlex.quote(output_path),
                voice=shlex.quote(voice),
                rate=shlex.quote(rate),
            )
            result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True)
        else:
            tts_path = _detect_tts()
            cmd = [
                "python3", tts_path,
                dialogue,
                "-v", voice,
                "-r", rate,
                "-o", output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return output_path

        if attempt < max_retries:
            print(f" TTS 失败（第 {attempt} 次），{2 * attempt}s 后重试...")
            _time.sleep(2 * attempt)
        else:
            print(f" TTS 生成失败（已重试 {max_retries} 次）：{result.stderr}")
            sys.exit(1)

    return output_path


def generate_slide(subtitle, visual, output_path, width, height, index, template_path=None):
    """用 HTML 截图生成字幕卡片"""
    tpl = template_path if template_path else TEMPLATE_HTML
    with open(tpl, "r", encoding="utf-8") as f:
        template = f.read()

    subtitle_html = subtitle.replace("\\n", "<br>").replace("\n", "<br>")
    visual_html = visual.replace("\\n", "<br>").replace("\n", "<br>")

    html = template.replace("{{SUBTITLE}}", subtitle_html)
    html = html.replace("{{VISUAL}}", visual_html)
    html = html.replace("{{INDEX}}", str(index))

    temp_html = Path(output_path).with_suffix(".html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html)

    chrome = _detect_chrome()
    cmd = [
        chrome,
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
        print(f" 图片生成失败：{output_path}")
        sys.exit(1)

    return output_path


def build_frontend_slides(sections, frontend_dir, width, height):
    frontend_dir = Path(frontend_dir)
    frontend_dir.mkdir(parents=True, exist_ok=True)
    render_dir = frontend_dir / 'render'
    render_dir.mkdir(parents=True, exist_ok=True)

    slides = []
    for idx, section in enumerate(sections, 1):
        title = section['title']
        subtitle = (section['subtitle'] or '').replace('\n', '<br>').replace('\n', '<br>')
        visual = section['visual'] or ''

        if idx == 1:
            tag = 'VIDEO BRIEF'
        elif idx == len(sections):
            tag = 'FINAL VERDICT'
        else:
            tag = 'KEY POINT'

        title_html = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace(' / ', ' &<br>').replace('、', '、<br>')
        visual_rows = []
        if visual:
            for chunk in re.split(r'[，。；;\n]+', visual):
                chunk = chunk.strip()
                if not chunk:
                    continue
                visual_rows.append(chunk)
        if not visual_rows and subtitle:
            visual_rows = [s.strip() for s in subtitle.replace('<br>', '\n').split('\n') if s.strip()]
        visual_rows = visual_rows[:3]

        if idx == len(sections):
            visual_html = """
                    <div style=\"display:flex;gap:40px;width:100%;\">
                        <div class=\"feature-card\" style=\"flex:1;text-align:center;\">
                            <div style=\"font-size:48px;margin-bottom:20px;\">⚡️</div>
                            <h3>重度用户</h3>
                            <p style=\"color:#10b981;\">建议尽快升级</p>
                        </div>
                        <div class=\"feature-card\" style=\"flex:1;text-align:center;\">
                            <div style=\"font-size:48px;margin-bottom:20px;\">☕️</div>
                            <h3>稳定环境</h3>
                            <p style=\"color:#3b82f6;\">可先观察</p>
                        </div>
                    </div>
            """
        else:
            items = []
            for row in visual_rows:
                safe = row.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                items.append(f'''<div class="item-row"><div class="item-icon">{idx}</div><div class="item-text"><h3>{safe}</h3></div></div>''')
            visual_html = f'<div class="feature-card">{"".join(items)}</div>'

        slides.append({
            'tag': tag,
            'title': title_html,
            'subtitle': (section['visual'] or section['subtitle'] or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'),
            'visual_html': visual_html,
            'caption': subtitle or title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        })

    slides_json = json.dumps(slides, ensure_ascii=False)
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Video Frontend Slides</title>
<style>
:root {{ --bg-dark:#09090b; --accent-blue:#3b82f6; --accent-green:#10b981; --accent-red:#ef4444; --card-bg:rgba(24,24,27,0.8); --border-color:rgba(63,63,70,0.5); }}
* {{ box-sizing:border-box; }}
body {{ background-color:var(--bg-dark); color:#f4f4f5; font-family:-apple-system,"PingFang SC","SF Pro Display","Noto Sans SC","Microsoft YaHei",sans-serif; margin:0; display:flex; flex-direction:column; align-items:center; padding:40px 0; }}
body.render-mode {{ display:block; padding:0; background:transparent; }}
.canvas {{ width:{width}px; height:{height}px; background:radial-gradient(circle at 50% 50%, #111827 0%, #000000 100%); border:1px solid var(--border-color); position:relative; overflow:hidden; display:flex; flex-direction:column; box-shadow:0 25px 50px -12px rgba(0,0,0,0.5); margin-bottom:40px; transform-origin:top center; transform:scale(0.4); }}
body.render-mode .canvas {{ margin:0; transform:none; box-shadow:none; border:none; }}
.canvas::before {{ content:""; position:absolute; inset:0; background-image:linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px); background-size:60px 60px; z-index:0; }}
.content {{ z-index:10; flex:1; display:flex; flex-direction:column; padding:100px 80px; }}
.header-tag {{ font-family:"JetBrains Mono", monospace; font-size:24px; color:var(--accent-blue); background:rgba(59,130,246,0.1); padding:8px 20px; border-radius:999px; width:fit-content; border:1px solid rgba(59,130,246,0.3); margin-bottom:40px; }}
.main-title {{ font-size:84px; font-weight:800; line-height:1.1; letter-spacing:-0.02em; margin-bottom:20px; background:linear-gradient(to bottom right, #ffffff, #a1a1aa); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
.sub-title {{ font-size:42px; color:#a1a1aa; margin-bottom:80px; }}
.visual-container {{ flex:1; display:flex; justify-content:center; align-items:center; position:relative; }}
.feature-card {{ background:var(--card-bg); border:1px solid var(--border-color); border-radius:32px; width:100%; padding:60px; backdrop-filter:blur(20px); box-shadow:0 40px 100px -20px rgba(0,0,0,0.8); }}
.item-row {{ display:flex; align-items:flex-start; margin-bottom:32px; gap:24px; }}
.item-icon {{ width:50px; height:50px; background:rgba(59,130,246,0.2); border-radius:12px; display:flex; align-items:center; justify-content:center; color:var(--accent-blue); flex-shrink:0; margin-top:5px; font-weight:700; }}
.item-text h3 {{ font-size:34px; font-weight:700; margin-bottom:10px; line-height:1.35; }}
.footer-caption {{ background:rgba(255,255,255,0.05); padding:60px 80px; border-top:1px solid var(--border-color); height:300px; display:flex; align-items:center; justify-content:center; text-align:center; font-size:48px; font-weight:600; line-height:1.4; color:#ffffff; }}
.highlight {{ color:var(--accent-blue); }}
.controls {{ position:fixed; bottom:20px; left:50%; transform:translateX(-50%); display:flex; gap:10px; background:rgba(0,0,0,0.8); padding:10px 20px; border-radius:999px; border:1px solid #333; z-index:100; }}
body.render-mode .controls {{ display:none; }}
button {{ background:#27272a; color:white; border:none; padding:10px 20px; border-radius:999px; cursor:pointer; font-weight:600; }}
button.active {{ background:var(--accent-blue); }}
</style>
</head>
<body>
<div id="slide-container" class="canvas"><div class="content" id="slide-content"></div><div class="footer-caption" id="slide-caption"></div></div>
<div class="controls" id="controls"></div>
<script>
const slides = {slides_json};
const controls = document.getElementById('controls');
slides.forEach((s, i) => {{ const btn=document.createElement('button'); btn.className='btn'; btn.textContent=String(i+1).padStart(2,'0'); btn.onclick=() => {{ location.hash = 'slide-' + i; }}; controls.appendChild(btn); }});
function renderSlide(index) {{
  const slide = slides[index];
  document.getElementById('slide-content').innerHTML = `<div class="header-tag">${{slide.tag}}</div><h1 class="main-title">${{slide.title}}</h1><p class="sub-title">${{slide.subtitle}}</p><div class="visual-container">${{slide.visual_html}}</div>`;
  document.getElementById('slide-caption').innerHTML = slide.caption;
  document.querySelectorAll('.btn').forEach((btn, i) => btn.classList.toggle('active', i === index));
}}
function initFromHash() {{
  const hash = window.location.hash || '';
  const match = hash.match(/slide-(\d+)/);
  const idx = match ? Math.max(0, Math.min(slides.length - 1, parseInt(match[1], 10))) : 0;
  if (hash.includes('render=1')) document.body.classList.add('render-mode');
  renderSlide(idx);
}}
window.addEventListener('hashchange', initFromHash);
initFromHash();
</script>
</body>
</html>'''

    preview_path = frontend_dir / 'preview.html'
    preview_path.write_text(html, encoding='utf-8')

    server_proc = subprocess.Popen(
        ['python3', '-m', 'http.server', '8765'],
        cwd=str(frontend_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        screenshot_script = frontend_dir / 'screenshot_slides.py'
        screenshot_script.write_text(
            "from pathlib import Path\n"
            "from playwright.sync_api import sync_playwright\n"
            f"BASE = Path({json.dumps(str(frontend_dir))})\n"
            "OUT = BASE / 'render'\n"
            "OUT.mkdir(exist_ok=True)\n"
            "URL = 'http://127.0.0.1:8765/preview.html'\n"
            "with sync_playwright() as p:\n"
            "    browser = p.chromium.launch()\n"
            f"    page = browser.new_page(viewport={{'width': {width}, 'height': {height}}}, device_scale_factor=1)\n"
            f"    for i in range({len(sections)}):\n"
            "        page.goto(f'{URL}#slide-{i}&render=1', wait_until='networkidle')\n"
            "        page.locator('#slide-container').screenshot(path=str(OUT / f'slide_{i+1:02d}.png'))\n"
            "        print('saved', OUT / f'slide_{i+1:02d}.png')\n"
            "    browser.close()\n",
            encoding='utf-8'
        )
        result = subprocess.run(['python3', str(screenshot_script)], capture_output=True, text=True)
        if result.returncode != 0:
            print(f' frontend slides 渲染失败：{result.stderr or result.stdout}')
            sys.exit(1)
    finally:
        server_proc.terminate()
        server_proc.wait(timeout=5)

    return render_dir


def get_image_size(image_path):
    with Image.open(image_path) as img:
        return img.size


def adapt_image_for_platform(image_path, output_path, width, height, platform):
    """平台适配：横版图包进竖版容器，避免直接拉伸变形"""
    src = Path(image_path)
    dst = Path(output_path)

    if platform != WECHAT_CHANNEL_PLATFORM:
        shutil.copy2(src, dst)
        return dst

    src_width, src_height = get_image_size(src)

    if src_width == width and src_height == height:
        shutil.copy2(src, dst)
        return dst

    if src_width < src_height:
        shutil.copy2(src, dst)
        return dst

    filter_complex = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},boxblur=20:10[bg];"
        f"[0:v]scale=960:540:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-filter_complex", filter_complex,
        "-frames:v", "1",
        str(dst),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f" 图片平台适配失败：{result.stderr}")
        sys.exit(1)

    return dst


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
        "-y",
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
        print(f" 片段合成失败：{result.stderr}")
        sys.exit(1)

    return output_path


def concat_segments(segment_paths, output_path):
    """拼接多个视频片段"""
    concat_list = Path(output_path).parent / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for seg in segment_paths:
            f.write(f"file '{seg.absolute()}'\n")

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
        print(f" 视频拼接失败：{result.stderr}")
        sys.exit(1)

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

    check_dependencies(args)
    visual_mode = resolve_visual_mode(args)

    temp_dir = Path(args.output).parent / TEMP_DIR
    temp_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Video-Gen: 从脚本生成视频")
    print(f"{'='*60}\n")

    print("[1/3] 解析脚本...")
    sections = parse_script(args.script)
    print(f"  解析到 {len(sections)} 个分段")

    frontend_render_dir = None
    if visual_mode == VISUAL_MODE_FRONTEND and not args.images_dir:
        print("  前端画面模式：frontend-slides + frontend-design")
        frontend_dir = args.frontend_dir or str(Path(args.output).parent / 'frontend-slides')
        frontend_render_dir = build_frontend_slides(sections, frontend_dir, args.width, args.height)

    print("\n[2/3] 生成素材...")
    segment_files = []

    for i, section in enumerate(sections, 1):
        print(f"\n  - 分段 {i}（{section['title']}）：")

        # 生成配音
        audio_output = temp_dir / f"audio_{i:02d}.mp3"
        print(f"    生成配音 mp3...", end="", flush=True)
        generate_audio(section["dialogue"], str(audio_output), args.voice, args.rate, args.tts_command)
        duration = get_audio_duration(str(audio_output))
        print(f" {duration:.1f}s")

        # 生成/加载字幕卡
        image_output = temp_dir / f"slide_{i:02d}.png"
        effective_images_dir = args.images_dir or (str(frontend_render_dir) if frontend_render_dir else None)
        if effective_images_dir:
            src = Path(effective_images_dir) / f"slide_{i:02d}.png"
            if not src.exists():
                print(f"    图片不存在：{src}")
                sys.exit(1)
            adapt_image_for_platform(str(src), str(image_output), args.width, args.height, args.platform)
            source_mode = 'frontend 预制图片' if frontend_render_dir and not args.images_dir else '预制图片'
            print(f"    使用{source_mode}：{src}（platform={args.platform}）")
        else:
            print(f"    生成字幕卡...", end="", flush=True)
            tpl_path = TEMPLATES_DIR / f"{args.template}.html" if args.template else None
            generate_slide(section["subtitle"], section["visual"], str(image_output),
                           args.width, args.height, i, template_path=tpl_path)
            print(" done")

        # 合成片段
        segment_output = temp_dir / f"seg_{i:02d}.mp4"
        compose_segment(str(image_output), str(audio_output), str(segment_output))
        segment_files.append(segment_output)

    # 合成视频
    print("\n[3/3] 合成视频...")

    print(f"  拼接视频：{args.output}...", end="", flush=True)
    concat_segments(segment_files, args.output)
    print(" done")

    total_duration = get_video_duration(args.output)

    if not args.keep_temp:
        print(f"\n  清理临时文件：{temp_dir}", end="", flush=True)
        shutil.rmtree(temp_dir)
        print(" done")

    print(f"\n{'='*60}")
    print(f"完成！输出：{args.output}")
    print(f"  总时长：{total_duration:.1f}秒")
    print(f"  平台：{args.platform}")
    print(f"  画面模式：{visual_mode}")
    if frontend_render_dir:
        print(f"  前端渲染目录：{frontend_render_dir}")
    print(f"  画幅：{args.width}x{args.height}（{(args.height/args.width):.2f}:1）")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
