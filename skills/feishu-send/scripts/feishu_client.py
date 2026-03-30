#!/usr/bin/env python3
"""飞书通用发送能力。"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests

OPENCLAW_CONFIG = os.path.expanduser("~/.openclaw/openclaw.json")
OPENCLAW_ENV = os.path.expanduser("~/.openclaw/.env")
DEV_WORKFLOW_ENV = os.path.expanduser("~/.config/dev-workflow/.env")


def expand_env(value: str) -> str:
    """展开 ${VAR} 格式的环境变量占位符。"""
    import re

    return re.sub(
        r"[$][{]([^}]+)[}]",
        lambda match: os.environ.get(match.group(1), match.group(0)),
        value,
    )


def _load_env_path(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_env_file() -> None:
    """加载 ~/.config/dev-workflow/.env 与 ~/.openclaw/.env 到进程环境变量（后者不覆盖已有键）。"""
    _load_env_path(DEV_WORKFLOW_ENV)
    _load_env_path(OPENCLAW_ENV)


def load_credentials(account_name: str = "main") -> tuple[str, str]:
    """从 .env 或 openclaw.json 加载飞书凭证。"""
    load_env_file()

    app_id = os.environ.get("FEISHU_MAIN_APP_ID")
    app_secret = os.environ.get("FEISHU_MAIN_APP_SECRET")
    if app_id and app_secret and account_name == "main":
        return app_id, app_secret

    with open(OPENCLAW_CONFIG, encoding="utf-8") as file:
        config = json.load(file)
    accounts = config["channels"]["feishu"]["accounts"]
    account = accounts.get(account_name) or accounts.get("main")
    return expand_env(account["appId"]), expand_env(account["appSecret"])


def get_token(account_name: str = "main") -> str:
    """获取 tenant_access_token。"""
    app_id, app_secret = load_credentials(account_name)
    response = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 token 失败: {data}")
    return data["tenant_access_token"]


def resolve_receive_id(to: str | None, env_key: str = "FEISHU_DEFAULT_TO") -> tuple[str, str]:
    """解析接收方 ID 与类型。"""
    load_env_file()
    if to:
        if to.startswith("oc_"):
            return to, "chat_id"
        return to, "open_id"

    env_to = os.environ.get(env_key)
    if env_to:
        return resolve_receive_id(env_to)

    with open(OPENCLAW_CONFIG, encoding="utf-8") as file:
        config = json.load(file)
    allow_from = config.get("channels", {}).get("feishu", {}).get("allowFrom", [])
    for uid in allow_from:
        if uid != "*" and uid.startswith("ou_"):
            return uid, "open_id"

    raise ValueError("未找到默认接收人，请显式传 --to 或配置 FEISHU_DEFAULT_TO")


def send_message(
    token: str,
    receive_id: str,
    msg_type: str,
    content: dict,
    receive_id_type: str = "open_id",
) -> str:
    """发送飞书消息，返回 message_id。"""
    response = requests.post(
        f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": json.dumps(content, ensure_ascii=False),
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 0:
        raise RuntimeError(f"发送消息失败: {data}")
    return data["data"]["message_id"]


def send_interactive_card(
    token: str,
    receive_id: str,
    card: dict,
    receive_id_type: str = "open_id",
) -> str:
    """发送交互卡片消息。"""
    return send_message(token, receive_id, "interactive", card, receive_id_type)


def send_text(
    token: str, receive_id: str, text: str, receive_id_type: str = "open_id"
) -> str:
    """发送文本消息。"""
    return send_message(token, receive_id, "text", {"text": text}, receive_id_type)


def upload_image(token: str, image_bytes: bytes, filename: str) -> str:
    """上传图片，返回 image_key。"""
    response = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/images",
        headers={"Authorization": f"Bearer {token}"},
        data={"image_type": "message"},
        files={"image": (filename, image_bytes, "image/png")},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 0:
        raise RuntimeError(f"上传图片失败: {data}")
    return data["data"]["image_key"]


def send_image(
    token: str, receive_id: str, image_key: str, receive_id_type: str = "open_id"
) -> str:
    """发送图片消息。"""
    return send_message(
        token, receive_id, "image", {"image_key": image_key}, receive_id_type
    )


def send_file(
    token: str, receive_id: str, file_path: str, receive_id_type: str = "open_id"
) -> str:
    """上传并发送文件。"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    with open(path, "rb") as file:
        response = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/files",
            headers={"Authorization": f"Bearer {token}"},
            data={"file_type": "stream", "file_name": path.name},
            files={"file": (path.name, file)},
            timeout=60,
        )
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 0:
        raise RuntimeError(f"上传文件失败: {data}")

    return send_message(
        token,
        receive_id,
        "file",
        {"file_key": data["data"]["file_key"]},
        receive_id_type,
    )
