#!/usr/bin/env python3
"""飞书工作日报卡片发送器

用法:
    python3 feishu_send_work_report.py --date 02-28 --items report.json [--to open_id] [--color purple]

report.json 格式:
    {
        "done": ["完成项1", "完成项2"],
        "in_progress": ["进行中1"],
        "blocked": ["阻塞项1"],
        "tomorrow": ["明日计划1"]
    }

也可通过 Python 直接调用:
    from feishu_send_work_report import send_work_report
    send_work_report(date, data, to=open_id)
"""

import json, os, sys, argparse

# 复用 feishu_send_card 的认证逻辑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from feishu_send_card import get_token
import urllib.request

def send_work_report(date, data, to=None, color="purple"):
    """发送工作日报卡片
    
    Args:
        date: 日期字符串，如 "02-28"
        data: dict，包含 done/in_progress/blocked/tomorrow 四个列表
        to: 接收人 open_id
        color: 卡片颜色
    """
    if not to:
        to = os.environ.get("FEISHU_DEFAULT_TO", "ou_6a0198bf2e0cc783c612d115a9c936b8")
    
    token = get_token()
    
    elements = []
    
    sections = [
        ("✅ 今日完成", data.get("done", [])),
        ("⏳ 进行中", data.get("in_progress", [])),
        ("🚫 阻塞项", data.get("blocked", [])),
        ("📋 明日计划", data.get("tomorrow", [])),
    ]
    
    first = True
    for title, items in sections:
        if not items:
            continue
        if not first:
            elements.append({"tag": "hr"})
        first = False
        
        elements.append({"tag": "markdown", "content": f"**{title}**"})
        
        # done 和 tomorrow 用有序列表，其余用无序
        if title.startswith("✅") or title.startswith("📋"):
            md = "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
        else:
            md = "\n".join(f"- {item}" for item in items)
        elements.append({"tag": "markdown", "content": md})
    
    card = {
        "header": {
            "title": {"tag": "plain_text", "content": f"🦞 龙虾哥工作日报 | {date}"},
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
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        if result.get("code") != 0:
            raise Exception(f"Send failed: {result}")
        return result["data"]["message_id"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="飞书工作日报卡片发送器")
    parser.add_argument("--date", required=True, help="日期，如 02-28")
    parser.add_argument("--items", required=True, help="report JSON 文件路径")
    parser.add_argument("--to", default=None, help="接收人 open_id")
    parser.add_argument("--color", default="purple", help="卡片颜色")
    args = parser.parse_args()
    
    with open(args.items) as f:
        data = json.load(f)
    
    msg_id = send_work_report(args.date, data, to=args.to, color=args.color)
    print(f"✅ 工作日报已发送: {msg_id}")
