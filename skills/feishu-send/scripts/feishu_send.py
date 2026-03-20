#!/usr/bin/env python3
"""feishu-send: 发送文件、图片、文本、卡片到飞书

用法：
  python3 feishu_send.py file  <路径>      [--to <id>] [--caption <文字>]
  python3 feishu_send.py image <路径或URL> [--to <id>] [--caption <文字>]
  python3 feishu_send.py text  <消息>      [--to <id>]
  python3 feishu_send.py card  <标题> --items <json文件> [--to <id>] [--color <颜色>]

凭证加载优先级（由 feishu_client 与本脚本预载共同完成）：
  1. 已存在的环境变量
  2. ~/.config/dev-workflow/.env（本脚本启动时 setdefault 注入）
  3. ~/.openclaw/.env
  4. ~/.openclaw/openclaw.json（channels.feishu.accounts.main）

共享客户端目录（须含 feishu_client.py）：
  1. 环境变量 FEISHU_CLIENT_ROOT（可在 dev-workflow/.env 中配置）
  2. 若未设置：从本脚本向上解析仓库根（skills/.../scripts/ 的上三级），尝试 <根>/scripts/feishu

接收目标格式：
  ou_xxx    用户 DM（open_id）
  oc_xxx    群聊（chat_id）
  不传      读 FEISHU_DEFAULT_TO 环境变量，或 openclaw.json allowFrom 首个 ou_ 用户
"""

import argparse
import io
import json
import os
import sys
from pathlib import Path


def _load_dotenv_setdefault(path: Path) -> None:
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def _ensure_feishu_client_on_path() -> None:
    _load_dotenv_setdefault(Path.home() / ".config" / "dev-workflow" / ".env")

    raw = (os.environ.get("FEISHU_CLIENT_ROOT") or "").strip()
    if raw:
        root = Path(raw).expanduser().resolve()
        if (root / "feishu_client.py").is_file():
            sys.path.insert(0, str(root))
            return
        print(
            f"❌ FEISHU_CLIENT_ROOT 无效（未找到 feishu_client.py）: {root}",
            file=sys.stderr,
        )
        sys.exit(2)

    here = Path(__file__).resolve()
    repo_root = here.parents[3]
    legacy = repo_root / "scripts" / "feishu"
    if (legacy / "feishu_client.py").is_file():
        sys.path.insert(0, str(legacy))
        return

    print(
        "❌ 未找到飞书共享客户端。请任选其一：\n"
        "  - 在环境变量或 ~/.config/dev-workflow/.env 中设置 FEISHU_CLIENT_ROOT="
        "（指向包含 feishu_client.py 的目录）\n"
        "  - 或将 skill 置于含 scripts/feishu/feishu_client.py 的仓库中（标准布局）",
        file=sys.stderr,
    )
    sys.exit(2)


_ensure_feishu_client_on_path()

from feishu_client import (
    get_token,
    resolve_receive_id,
    send_text,
    upload_image,
    send_image,
    send_file,
)

try:
    from feishu_card_utils import build_card, send_card as _send_card
    _HAS_CARD = True
except ImportError:
    _HAS_CARD = False


# ── 子命令 ────────────────────────────────────

def cmd_file(args):
    path = Path(args.path)
    if not path.exists():
        print(f"❌ 文件不存在: {args.path}", file=sys.stderr)
        return 1

    token = get_token()
    receive_id, id_type = resolve_receive_id(args.to)

    if args.caption:
        send_text(token, receive_id, args.caption, id_type)

    msg_id = send_file(token, receive_id, str(path), id_type)
    print(f"✅ [已发送] 文件：{path.name}  message_id: {msg_id}")
    return 0


def cmd_image(args):
    import requests

    token = get_token()
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

    # 超 3MB 尝试压缩
    if len(image_bytes) > 3 * 1024 * 1024:
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75, optimize=True)
            image_bytes = buf.getvalue()
            filename = Path(filename).stem + ".jpg"
            print(f"图片已压缩: {len(image_bytes) // 1024}KB")
        except ImportError:
            pass

    if args.caption:
        send_text(token, receive_id, args.caption, id_type)

    image_key = upload_image(token, image_bytes, filename)
    msg_id = send_image(token, receive_id, image_key, id_type)
    print(f"✅ [已发送] 图片：{filename}  message_id: {msg_id}")
    return 0


def cmd_text(args):
    token = get_token()
    receive_id, id_type = resolve_receive_id(args.to)
    msg_id = send_text(token, receive_id, args.message, id_type)
    print(f"✅ [已发送] 文本消息  message_id: {msg_id}")
    return 0


def cmd_card(args):
    if not _HAS_CARD:
        print("❌ feishu_card_utils 未找到，无法发送卡片", file=sys.stderr)
        return 1

    with open(args.items, encoding="utf-8") as f:
        items = json.load(f)

    from feishu_card_utils import card_hr, card_markdown
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

    msg_id = _send_card(args.title, args.color, elements, to=args.to)
    print(f"✅ [已发送] 卡片：{args.title}  message_id: {msg_id}")
    return 0


# ── CLI ────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="发送文件/图片/文本/卡片到飞书")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--to", help="接收人 open_id 或群 chat_id（oc_ 开头）")

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

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
