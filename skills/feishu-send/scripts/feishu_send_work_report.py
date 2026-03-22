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

import argparse
import json

from feishu_card_utils import card_hr, card_markdown, send_card as send_feishu_card

def send_work_report(date, data, to=None, color="purple"):
    """发送工作日报卡片
    
    Args:
        date: 日期字符串，如 "02-28"
        data: dict，包含 done/in_progress/blocked/tomorrow 四个列表
        to: 接收人 open_id
        color: 卡片颜色
    """
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
            elements.append(card_hr())
        first = False
        
        elements.append(card_markdown(f"**{title}**"))
        
        # done 和 tomorrow 用有序列表，其余用无序
        if title.startswith("✅") or title.startswith("📋"):
            md = "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
        else:
            md = "\n".join(f"- {item}" for item in items)
        elements.append(card_markdown(md))

    return send_feishu_card(f"🦞 龙虾哥工作日报 | {date}", color, elements, to=to)

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
