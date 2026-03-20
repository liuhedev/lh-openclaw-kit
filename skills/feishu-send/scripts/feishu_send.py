#!/usr/bin/env python3
"""feishu-send: 发送文件、图片、文本、卡片、富文本到飞书

用法：
  python3 feishu_send.py file   <路径>      [--to <id>] [--caption <文字>] [--account <账号>]
  python3 feishu_send.py image  <路径或URL> [--to <id>] [--caption <文字>] [--account <账号>]
  python3 feishu_send.py text   <消息>      [--to <id>] [--account <账号>]
  python3 feishu_send.py card   <标题> --items <json文件> [--to <id>] [--color <颜色>] [--account <账号>]
  python3 feishu_send.py post   --title <标题> --content <内容或--content-file> [--to <id>] [--account <账号>]

凭证加载优先级（由 feishu_client 完成）：
  1. 已存在的环境变量
  2. ~/.config/dev-workflow/.env
  3. ~/.openclaw/.env
  4. ~/.openclaw/openclaw.json（channels.feishu.accounts.<账号名>）

接收目标格式：
  ou_xxx    用户 DM（open_id）
  oc_xxx    群聊（chat_id）
  不传      读 FEISHU_DEFAULT_TO 环境变量，或 openclaw.json allowFrom 首个 ou_ 用户
"""

import argparse
import io
import json
import re
import sys
from pathlib import Path

# 同目录导入
from feishu_client import (
    get_token,
    resolve_receive_id,
    send_message,
    send_text,
    upload_image,
    send_image,
    send_file,
)
from feishu_card_utils import build_card, card_hr, card_markdown, card_note, send_card as _send_card


# ── 辅助函数 ────────────────────────────────────

def compress_image(image_bytes: bytes, filename: str, max_size_kb: int = 3072) -> tuple:
    """压缩图片到指定大小以内，返回 (bytes, filename)

    多级策略：
    1. 先尝试降低 JPEG quality（从高到低）
    2. 如果仍然超大，再缩小图片尺寸
    """
    try:
        from PIL import Image
        size_kb = len(image_bytes) / 1024
        if size_kb <= max_size_kb:
            return image_bytes, filename

        img = Image.open(io.BytesIO(image_bytes))
        # 转 RGB（PNG 可能有 alpha）
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # 先尝试只降质量，不缩尺寸
        for quality in [85, 75, 65]:
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            if len(buf.getvalue()) / 1024 <= max_size_kb:
                compressed = buf.getvalue()
                new_filename = Path(filename).stem + ".jpg"
                print(f"压缩: {size_kb:.0f}KB → {len(compressed)//1024}KB (quality={quality})")
                return compressed, new_filename

        # 质量降到最低还超，才缩尺寸
        ratio = (max_size_kb * 1024 / len(image_bytes)) ** 0.5
        new_w = int(img.width * ratio)
        new_h = int(img.height * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=65, optimize=True)
        compressed = buf.getvalue()
        new_filename = Path(filename).stem + ".jpg"
        print(f"压缩: {size_kb:.0f}KB → {len(compressed)//1024}KB (缩放+压缩)")
        return compressed, new_filename
    except ImportError:
        return image_bytes, filename


def markdown_to_post_content(markdown_text: str) -> list:
    """将简单 Markdown 转换为飞书 post content 格式

    支持：
    - **bold** → bold 文本
    - [text](url) → 超链接
    - 空行分段
    """
    paragraphs = []
    # 按空行分段
    raw_paragraphs = re.split(r'\n\s*\n', markdown_text.strip())

    for para in raw_paragraphs:
        if not para.strip():
            continue
        elements = []
        # 合并行内内容（单个换行不分段）
        text = para.replace('\n', ' ').strip()

        # 解析行内格式：**bold** 和 [text](url)
        pattern = r'(\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))'
        parts = re.split(pattern, text)

        for part in parts:
            if not part:
                continue
            # 匹配粗体
            bold_match = re.match(r'\*\*([^*]+)\*\*', part)
            if bold_match:
                elements.append({
                    "tag": "text",
                    "text": bold_match.group(1),
                    "style": {"bold": True}
                })
                continue
            # 匹配链接
            link_match = re.match(r'\[([^\]]+)\]\(([^)]+)\)', part)
            if link_match:
                elements.append({
                    "tag": "a",
                    "text": link_match.group(1),
                    "href": link_match.group(2)
                })
                continue
            # 普通文本
            if part.strip():
                elements.append({"tag": "text", "text": part})

        if elements:
            paragraphs.append(elements)

    return paragraphs


# ── 子命令 ────────────────────────────────────

def cmd_file(args):
    path = Path(args.path)
    if not path.exists():
        print(f"❌ 文件不存在: {args.path}", file=sys.stderr)
        return 1

    token = get_token(args.account)
    receive_id, id_type = resolve_receive_id(args.to)

    if args.caption:
        send_text(token, receive_id, args.caption, id_type)

    msg_id = send_file(token, receive_id, str(path), id_type)
    print(f"✅ [已发送] 文件：{path.name}  message_id: {msg_id}")
    return 0


def cmd_image(args):
    import requests

    token = get_token(args.account)
    receive_id, id_type = resolve_receive_id(args.to)

    source = args.path
    if source.startswith(("http://", "https://")):
        resp = requests.get(source, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        resp.raise_for_status()
        image_bytes = resp.content
        filename = source.split("/")[-1].split("?")[0] or "image.jpg"
    else:
        p = Path(source)
        if not p.exists():
            print(f"❌ 文件不存在: {source}", file=sys.stderr)
            return 1
        image_bytes = p.read_bytes()
        filename = p.name

    # 超 3MB 尝试多级压缩
    if len(image_bytes) > 3 * 1024 * 1024:
        image_bytes, filename = compress_image(image_bytes, filename)

    if args.caption:
        send_text(token, receive_id, args.caption, id_type)

    image_key = upload_image(token, image_bytes, filename)
    msg_id = send_image(token, receive_id, image_key, id_type)
    print(f"✅ [已发送] 图片：{filename}  message_id: {msg_id}")
    return 0


def cmd_text(args):
    token = get_token(args.account)
    receive_id, id_type = resolve_receive_id(args.to)
    msg_id = send_text(token, receive_id, args.message, id_type)
    print(f"✅ [已发送] 文本消息  message_id: {msg_id}")
    return 0


def cmd_card(args):
    token = get_token(args.account)
    with open(args.items, encoding="utf-8") as f:
        items = json.load(f)
    elements = []
    for i, item in enumerate(items):
        if i > 0:
            elements.append(card_hr())
        parts = [f"**{i+1}.** {item['summary']}"]
        if item.get("insight"):
            parts.append(f"💡 {item['insight']}")
        if item.get("author") and item.get("url"):
            parts.append(f"✍️ {item['author']} → [原文]({item['url']})")
        elif item.get("url"):
            parts.append(f"[原文]({item['url']})")
        elements.append(card_markdown("\n".join(parts)))

    receive_id, id_type = resolve_receive_id(args.to)
    from feishu_client import send_interactive_card
    card = build_card(args.title, args.color, elements)
    msg_id = send_interactive_card(token, receive_id, card, id_type)
    print(f"✅ [已发送] 卡片：{args.title}  message_id: {msg_id}")
    return 0


def cmd_post(args):
    """发送富文本消息 (post 类型)"""
    # 获取内容
    if args.content_file:
        content_path = Path(args.content_file)
        if not content_path.exists():
            print(f"❌ 文件不存在: {args.content_file}", file=sys.stderr)
            return 1
        markdown_text = content_path.read_text(encoding="utf-8")
    else:
        markdown_text = args.content

    # 转换为飞书 post 格式
    post_content = markdown_to_post_content(markdown_text)
    content = {
        "zh_cn": {
            "title": args.title,
            "content": post_content
        }
    }

    token = get_token(args.account)
    receive_id, id_type = resolve_receive_id(args.to)
    msg_id = send_message(token, receive_id, "post", content, id_type)
    print(f"✅ [已发送] 富文本消息：{args.title}  message_id: {msg_id}")
    return 0


# ── CLI ────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="发送文件/图片/文本/卡片/富文本到飞书")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--to", help="接收人 open_id 或群 chat_id（oc_ 开头）")
    common.add_argument("--account", default="main", help="飞书账号名（默认: main）")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_file = sub.add_parser("file", parents=[common], help="发送本地文件（强制附件链路）")
    p_file.add_argument("path", help="本地文件路径")
    p_file.add_argument("--caption", help="附带说明文字")
    p_file.set_defaults(func=cmd_file)

    p_img = sub.add_parser("image", parents=[common], help="发送图片（本地路径或 URL）")
    p_img.add_argument("path", help="图片路径或 URL")
    p_img.add_argument("--caption", help="附带说明文字")
    p_img.set_defaults(func=cmd_image)

    p_txt = sub.add_parser("text", parents=[common], help="发送纯文本消息")
    p_txt.add_argument("message", help="消息内容")
    p_txt.set_defaults(func=cmd_text)

    p_card = sub.add_parser("card", parents=[common], help="发送结构化卡片（日报/列表等）")
    p_card.add_argument("title", help="卡片标题")
    p_card.add_argument("--items", required=True, help="items JSON 文件路径")
    p_card.add_argument("--color", default="blue",
                        choices=["blue", "green", "orange", "red", "purple"],
                        help="卡片颜色（默认 blue）")
    p_card.set_defaults(func=cmd_card)

    # post 子命令（富文本消息）
    p_post = sub.add_parser("post", parents=[common], help="发送富文本消息（支持 Markdown）")
    p_post.add_argument("--title", required=True, help="消息标题")
    post_content = p_post.add_mutually_exclusive_group(required=True)
    post_content.add_argument("--content", help="Markdown 格式的消息内容")
    post_content.add_argument("--content-file", help="Markdown 文件路径")
    p_post.set_defaults(func=cmd_post)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
