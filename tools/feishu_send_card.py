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

import json, os, sys, argparse, urllib.request

def get_token():
    """从环境变量获取飞书 tenant_access_token"""
    # 读 .env
    env_path = os.path.expanduser("~/.openclaw/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    
    app_id = os.environ.get("FEISHU_MAIN_APP_ID", "")
    app_secret = os.environ.get("FEISHU_MAIN_APP_SECRET", "")
    if not app_id or not app_secret:
        raise ValueError("FEISHU_MAIN_APP_ID / FEISHU_MAIN_APP_SECRET not set")
    
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": app_id, "app_secret": app_secret}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["tenant_access_token"]

def send_card(title, items, to=None, color="blue"):
    """发送飞书消息卡片
    
    Args:
        title: 卡片标题
        items: 列表，每项包含 summary, insight, author, url
        to: 接收人 open_id，默认从 .env 读 FEISHU_DEFAULT_TO
        color: 卡片颜色 (blue/green/orange/red/purple)
    """
    if not to:
        to = os.environ.get("FEISHU_DEFAULT_TO", "ou_6a0198bf2e0cc783c612d115a9c936b8")
    
    token = get_token()
    
    # 构造卡片元素
    elements = []
    for i, item in enumerate(items):
        if i > 0:
            elements.append({"tag": "hr"})
        
        md = f"**{i+1}.** {item['summary']}\n💡 {item['insight']}\n✍️ {item['author']} → [原文]({item['url']})"
        elements.append({"tag": "markdown", "content": md})
    
    card = {
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": color
        },
        "elements": elements
    }
    
    body = {
        "receive_id": to,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False)
    }
    
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
        data=json.dumps(body, ensure_ascii=False).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        if result.get("code") != 0:
            raise Exception(f"Send failed: {result}")
        return result["data"]["message_id"]

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
