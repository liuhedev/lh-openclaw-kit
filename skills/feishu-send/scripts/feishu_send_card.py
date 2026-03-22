#!/usr/bin/env python3
"""飞书消息卡片发送器 - 用于日报等结构化内容推送

用法:
    python3 feishu_send_card.py --title "标题" --items items.json [--to open_id] [--color blue]
    
items.json 格式:
    [
        {"summary": "摘要", "insight": "借鉴点", "author": "作者", "url": "链接"},
        ...
    ]

也可通过 Python 直接调用:
    from feishu_send_card import send_card
    send_card(title, items, to=open_id, color="blue")
"""

import argparse
import json

from feishu_card_utils import card_hr, card_markdown, send_card as send_feishu_card

def send_card(title, items, to=None, color="blue"):
    """发送飞书消息卡片
    
    Args:
        title: 卡片标题
        items: 列表，每项包含 summary, insight, author, url
        to: 接收人 open_id，默认从 .env 读 FEISHU_DEFAULT_TO
        color: 卡片颜色 (blue/green/orange/red/purple)
    """
    elements = []
    for i, item in enumerate(items):
        if i > 0:
            elements.append(card_hr())
        
        md = f"**{i+1}.** {item['summary']}\n💡 {item['insight']}\n✍️ {item['author']} → [原文]({item['url']})"
        elements.append(card_markdown(md))

    return send_feishu_card(title, color, elements, to=to)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="飞书消息卡片发送器")
    parser.add_argument("--title", required=True, help="卡片标题")
    parser.add_argument("--items", required=True, help="items JSON 文件路径")
    parser.add_argument("--to", default=None, help="接收人 open_id")
    parser.add_argument("--color", default="blue", help="卡片颜色")
    args = parser.parse_args()
    
    with open(args.items) as f:
        items = json.load(f)
    
    msg_id = send_card(args.title, items, to=args.to, color=args.color)
    print(f"✅ 卡片已发送: {msg_id}")
