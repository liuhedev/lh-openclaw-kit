#!/usr/bin/env python3
"""飞书卡片构造公共方法。"""
from __future__ import annotations

from feishu_client import get_token, resolve_receive_id, send_interactive_card


def card_markdown(content: str) -> dict:
    """构造 markdown 元素。"""
    return {"tag": "markdown", "content": content}


def card_hr() -> dict:
    """构造分割线元素。"""
    return {"tag": "hr"}


def card_note(content: str) -> dict:
    """构造 note 元素。"""
    return {
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": content}],
    }


def build_card(title: str, color: str, elements: list[dict]) -> dict:
    """构造交互卡片。"""
    return {
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": color,
        },
        "elements": elements,
    }


def send_card(
    title: str,
    color: str,
    elements: list[dict],
    to: str | None = None,
    env_key: str = "FEISHU_DEFAULT_TO",
) -> str:
    """发送交互卡片。"""
    receive_id, receive_id_type = resolve_receive_id(to, env_key=env_key)
    token = get_token()
    card = build_card(title, color, elements)
    return send_interactive_card(token, receive_id, card, receive_id_type)
