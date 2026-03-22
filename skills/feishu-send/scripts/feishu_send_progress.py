#!/usr/bin/env python3
"""飞书分发进度卡片发送器

用法:
    # 从 status.json 自动生成进度卡片
    python3 scripts/feishu/feishu_send_progress.py content/articles/2026-02-27/status.json

    # 指定接收人
    python3 scripts/feishu/feishu_send_progress.py content/articles/2026-02-27/status.json --to ou_xxx

    # Python 调用
    from feishu_send_progress import send_progress_card
    send_progress_card("path/to/status.json")
"""

import argparse
import json

from feishu_card_utils import (
    card_hr,
    card_markdown,
    card_note,
    send_card as send_feishu_card,
)


# 平台显示名 + 链接字段映射
PLATFORM_CONFIG = {
    "wechat":      {"name": "微信公众号", "url_key": "wechat_url"},
    "github":      {"name": "GitHub 博客", "url_key": "github_url"},
    "juejin":      {"name": "掘金", "url_key": "juejin_url"},
    "feishu":      {"name": "飞书知识库", "url_key": "feishu_url"},
    "zhihu":       {"name": "知乎", "url_key": "zhihu_url"},
    "xiaohongshu": {"name": "小红书", "url_key": "xiaohongshu_url"},
    "video":       {"name": "视频号", "url_key": "video_url"},
    "twitter":     {"name": "X/推特", "url_key": "twitter_url"},
}

STATUS_ICON = {
    "done": "🟢",
    "pending": "🟡",
    "failed": "🔴",
    "skipped": "⚪",
}

STATUS_TEXT = {
    "done": "✅ 已发布",
    "pending": "⏳ 待发布",
    "failed": "❌ 失败",
    "skipped": "⏭️ 跳过",
}

def send_progress_card(status_path, to=None):
    """从 status.json 生成并发送分发进度卡片"""
    with open(status_path, "r", encoding="utf-8") as f:
        status = json.load(f)

    title = status.get("title", "未命名文章")
    date = status.get("date", "")
    platforms = status.get("platforms", {})
    urls = status.get("urls", {})

    # 统计
    done_count = sum(1 for v in platforms.values() if v == "done")
    total_count = len(platforms)

    elements = []
    for key, cfg in PLATFORM_CONFIG.items():
        if key not in platforms:
            continue
        st = platforms[key]
        icon = STATUS_ICON.get(st, "⚪")
        text = STATUS_TEXT.get(st, st)
        url = urls.get(cfg["url_key"], "")

        if url and st == "done":
            line = f"{icon} **{cfg['name']}**　{text.replace('已发布', '[已发布](' + url + ')')}"
        else:
            line = f"{icon} **{cfg['name']}**　{text}"

        elements.append(card_markdown(line))

    elements.append(card_hr())
    elements.append(card_note(f"📅 {date} | 完成 {done_count}/{total_count} 平台 | 🦞 龙虾哥自动分发"))

    # 根据完成率选颜色
    if done_count == total_count:
        color = "green"
    elif done_count >= total_count * 0.5:
        color = "orange"
    else:
        color = "red"

    msg_id = send_feishu_card(
        f"📊 分发进度：{title}",
        color,
        elements,
        to=to,
        env_key="FEISHU_WORK_GROUP",
    )
    print(f"✅ 进度卡片已发送: {msg_id}")
    return msg_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="飞书分发进度卡片发送器")
    parser.add_argument("status_json", help="status.json 文件路径")
    parser.add_argument("--to", default=None, help="接收人 open_id")
    args = parser.parse_args()

    send_progress_card(args.status_json, to=args.to)
