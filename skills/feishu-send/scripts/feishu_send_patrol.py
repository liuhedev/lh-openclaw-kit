#!/usr/bin/env python3
"""飞书每日巡检报告卡片发送器

用法:
    # 传 JSON 数据
    python3 scripts/feishu/feishu_send_patrol.py --json '{"backup":"✅ 已提交(42 files)","checks":[{"name":"Git","status":"✅ 正常"},...],"memory":"✅ 正常","alerts":["掘金cookie未配置"]}'

    # 传 JSON 文件
    python3 scripts/feishu/feishu_send_patrol.py --file patrol-report.json

JSON 格式:
    {
        "date": "2026-03-01",           // 可选，默认今天
        "backup": "✅ 已提交(42 files)",  // 备份状态
        "checks": [                      // 环境自检项
            {"name": "Git", "status": "✅ 正常"},
            {"name": "磁盘", "status": "✅ 29%"},
            {"name": "掘金 cookie", "status": "⚠️ 未配置"}
        ],
        "memory": "✅ 全部正常，无需归档",  // 记忆维护
        "alerts": ["掘金 cookie 需补配"]   // 需关注项，空数组则全绿
    }
"""

import argparse
import json
import sys
from datetime import datetime

from feishu_card_utils import (
    card_hr,
    card_markdown,
    card_note,
    send_card as send_feishu_card,
)


WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def send_patrol_card(data, to=None):
    date_str = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekday = WEEKDAYS[dt.weekday()]
        display_date = f"{dt.month}月{dt.day}日（{weekday}）"
    except:
        display_date = date_str

    backup = data.get("backup", "—")
    checks = data.get("checks", [])
    memory = data.get("memory", "—")
    alerts = data.get("alerts", [])

    has_warning = any("⚠" in c.get("status", "") or "❌" in c.get("status", "") for c in checks)
    has_alerts = len(alerts) > 0
    color = "orange" if (has_warning or has_alerts) else "green"

    elements = []

    # 备份
    elements.append(card_markdown(f"**📦 备份**　{backup}"))
    elements.append(card_hr())

    # 环境自检
    elements.append(card_markdown("**🔍 环境自检**"))
    # 表头
    elements.append({
        "tag": "column_set",
        "flex_mode": "none",
        "background_style": "grey",
        "columns": [
            {"tag": "column", "width": "weighted", "weight": 2, "vertical_align": "top",
             "elements": [{"tag": "markdown", "content": "**项目**"}]},
            {"tag": "column", "width": "weighted", "weight": 3, "vertical_align": "top",
             "elements": [{"tag": "markdown", "content": "**状态**"}]}
        ]
    })
    # 数据行
    for c in checks:
        elements.append({
            "tag": "column_set",
            "flex_mode": "none",
            "background_style": "default",
            "columns": [
                {"tag": "column", "width": "weighted", "weight": 2, "vertical_align": "top",
                 "elements": [{"tag": "markdown", "content": c["name"]}]},
                {"tag": "column", "width": "weighted", "weight": 3, "vertical_align": "top",
                 "elements": [{"tag": "markdown", "content": c["status"]}]}
            ]
        })
    elements.append(card_hr())

    # 记忆维护
    elements.append(card_markdown(f"**🧠 记忆维护**　{memory}"))

    # 需关注
    if alerts:
        elements.append(card_hr())
        alert_lines = "\n".join(f"⚠️ {a}" for a in alerts)
        elements.append(card_markdown(f"**🚨 需关注**\n{alert_lines}"))

    # 待办事项
    todo = data.get("todo")
    if todo:
        elements.append(card_hr())
        elements.append(card_markdown(f"**📌 今日待办**\n{todo}"))

    elements.append(card_hr())
    elements.append(card_note(f"🦞 龙虾哥每日巡检 | {date_str}"))

    msg_id = send_feishu_card(
        f"📋 每日巡检 — {display_date}",
        color,
        elements,
        to=to,
        env_key="FEISHU_WORK_GROUP",
    )
    print(f"✅ 巡检卡片已发送: {msg_id}")
    return msg_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="飞书巡检报告卡片发送器")
    parser.add_argument("--json", default=None, help="JSON 字符串")
    parser.add_argument("--file", default=None, help="JSON 文件路径")
    parser.add_argument("--to", default=None, help="接收人 open_id")
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            data = json.load(f)
    elif args.json:
        data = json.loads(args.json)
    else:
        data = json.load(sys.stdin)

    send_patrol_card(data, to=args.to)
