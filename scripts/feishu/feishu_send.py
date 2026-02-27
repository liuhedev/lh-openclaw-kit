#!/usr/bin/env python3
"""发送图片到飞书会话（DM 或群）

用法：
  python3 scripts/feishu_send_image.py <图片路径或URL> [--to <open_id或chat_id>] [--caption <文字>]

示例：
  python3 scripts/feishu_send_image.py tmp/cover.png
  python3 scripts/feishu_send_image.py tmp/cover.png --to ou_6a0198bf2e0cc783c612d115a9c936b8
  python3 scripts/feishu_send_image.py https://example.com/img.jpg --caption "今日封面"

--to 默认读取 FEISHU_DEFAULT_TO 环境变量，或 openclaw.json 里的 allowFrom[0]
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

OPENCLAW_CONFIG = os.path.expanduser("~/.openclaw/openclaw.json")


def expand_env(value: str) -> str:
    """展开 ${VAR} 格式的环境变量占位符"""
    import re
    return re.sub(r"[$][{]([^}]+)[}]", lambda m: os.environ.get(m.group(1), m.group(0)), value)


def load_env_file():
    """加载 ~/.openclaw/.env"""
    env_path = os.path.expanduser("~/.openclaw/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()


def load_credentials(account_name: str = "main"):
    load_env_file()
    with open(OPENCLAW_CONFIG) as f:
        config = json.load(f)
    accounts = config["channels"]["feishu"]["accounts"]
    # 优先用指定账号，fallback 到 main
    account = accounts.get(account_name) or accounts.get("main")
    app_id = expand_env(account["appId"])
    app_secret = expand_env(account["appSecret"])
    return app_id, app_secret


def get_token(app_id: str, app_secret: str) -> str:
    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 token 失败: {data}")
    return data["tenant_access_token"]


def upload_image(token: str, image_bytes: bytes, filename: str) -> str:
    """上传图片，返回 image_key"""
    resp = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/images",
        headers={"Authorization": f"Bearer {token}"},
        data={"image_type": "message"},
        files={"image": (filename, image_bytes, "image/png")},
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"上传图片失败: {data}")
    return data["data"]["image_key"]


def send_image(token: str, receive_id: str, image_key: str, receive_id_type: str = "open_id"):
    """发送图片消息"""
    resp = requests.post(
        f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "receive_id": receive_id,
            "msg_type": "image",
            "content": json.dumps({"image_key": image_key}),
        },
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"发送图片失败: {data}")
    return data["data"]["message_id"]


def send_text(token: str, receive_id: str, text: str, receive_id_type: str = "open_id"):
    """发送文字消息"""
    resp = requests.post(
        f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        },
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"发送文字失败: {data}")
    return data["data"]["message_id"]


def send_file(token: str, receive_id: str, file_path: str, receive_id_type: str = "open_id"):
    """上传并发送文件"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    # 上传
    with open(path, "rb") as f:
        resp = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/files",
            headers={"Authorization": f"Bearer {token}"},
            data={"file_type": "stream", "file_name": path.name},
            files={"file": (path.name, f)},
        )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"上传文件失败: {data}")
    file_key = data["data"]["file_key"]
    # 发送
    resp = requests.post(
        f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "receive_id": receive_id,
            "msg_type": "file",
            "content": json.dumps({"file_key": file_key}),
        },
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"发送文件失败: {data}")
    return data["data"]["message_id"]



def compress_image(image_bytes: bytes, filename: str, max_size_kb: int = 3072) -> tuple:
    """压缩图片到指定大小以内，返回 (bytes, filename)"""
    try:
        from PIL import Image
        import io
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


def load_image(source: str) -> tuple:
    """加载图片，返回 (bytes, filename)"""
    if source.startswith("http://") or source.startswith("https://"):
        resp = requests.get(source, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        resp.raise_for_status()
        image_bytes = resp.content
        filename = source.split("/")[-1].split("?")[0] or "image.jpg"
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {source}")
        image_bytes = path.read_bytes()
        filename = path.name
    return image_bytes, filename


def resolve_receive_id(to: str | None) -> tuple[str, str]:
    """返回 (receive_id, receive_id_type)"""
    if to:
        if to.startswith("oc_"):
            return to, "chat_id"
        return to, "open_id"
    # 从环境变量读
    env_to = os.environ.get("FEISHU_DEFAULT_TO")
    if env_to:
        return resolve_receive_id(env_to)
    # 从 openclaw.json 读 allowFrom[0]（跳过通配符 *）
    with open(OPENCLAW_CONFIG) as f:
        config = json.load(f)
    allow_from = config.get("channels", {}).get("feishu", {}).get("allowFrom", [])
    for uid in allow_from:
        if uid != "*" and uid.startswith("ou_"):
            return uid, "open_id"
    raise ValueError("未指定 --to，也没有找到默认接收人，请用 --to 指定 open_id 或 chat_id，或在 .env 中设置 FEISHU_DEFAULT_TO")


def main():
    parser = argparse.ArgumentParser(description="发送图片到飞书")
    parser.add_argument("image", help="图片路径、文件路径或 URL")
    parser.add_argument("--to", help="接收人 open_id 或群 chat_id（oc_ 开头）")
    parser.add_argument("--caption", help="图片/文件前附带的文字说明")
    parser.add_argument("--account", default="main", help="飞书账号名（默认: main，章鱼哥用 octopus）")
    parser.add_argument("--file", action="store_true", help="强制作为文件发送（非图片）")
    args = parser.parse_args()

    app_id, app_secret = load_credentials(args.account)
    token = get_token(app_id, app_secret)

    receive_id, receive_id_type = resolve_receive_id(args.to)

    # 判断是否为本地非图片文件
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".ico", ".tiff"}
    source = args.image
    is_local = not source.startswith("http://") and not source.startswith("https://")
    ext = Path(source).suffix.lower() if is_local else ""
    is_file_mode = args.file or (is_local and ext and ext not in IMAGE_EXTS)

    if args.caption:
        send_text(token, receive_id, args.caption, receive_id_type)
        print(f"已发送文字: {args.caption}")

    if is_file_mode:
        print(f"发送文件: {source} → {receive_id}")
        msg_id = send_file(token, receive_id, source, receive_id_type)
        print(f"✅ 文件发送成功，message_id: {msg_id}")
    else:
        image_bytes, filename = load_image(source)
        image_bytes, filename = compress_image(image_bytes, filename)
        print(f"上传图片: {filename} ({len(image_bytes) // 1024}KB) → {receive_id}")
        image_key = upload_image(token, image_bytes, filename)
        print(f"image_key: {image_key}")
        msg_id = send_image(token, receive_id, image_key, receive_id_type)
        print(f"✅ 发送成功，message_id: {msg_id}")


if __name__ == "__main__":
    main()
