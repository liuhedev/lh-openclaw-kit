# lh-openclaw-kit

围绕 OpenClaw 的实用工具集，包含 scripts、skills 和 demos。

## 目录结构

```
lh-openclaw-kit/
├── scripts/
│   └── feishu/                    # 飞书相关脚本
│       └── feishu_send.py         # 发图片/消息工具
└── skills/                        # OpenClaw 自定义 Skills
    ├── feishu-send/               # 飞书文件/图片/文本/卡片/日报发送（API 直发附件）
    │   └── scripts/
    │       ├── feishu_send.py           # 主入口（text/image/file/card/post）
    │       ├── feishu_send_card.py      # 结构化列表卡片
    │       ├── feishu_send_patrol.py    # 每日巡检报告卡片
    │       ├── feishu_send_progress.py  # 分发进度卡片
    │       └── feishu_send_work_report.py # 工作日报卡片
    └── lh-edge-tts/               # 文字转语音 Skill
```

## scripts

| 脚本 | 说明 |
|------|------|
| [feishu_send.py](scripts/feishu/feishu_send.py) | 通过飞书 API 发送图片、文件或文字消息，支持本地路径和 URL |

## skills

| Skill | 说明 |
|-------|------|
| [feishu-send](skills/feishu-send/) | 通过飞书开放平台 API 发送文件、图片、文本、结构化卡片、巡检报告、分发进度、工作日报 |
| [lh-edge-tts](skills/lh-edge-tts/) | 基于微软 Edge TTS 的文字转语音工具，支持多音色、语速调节和字幕导出 |
| [lh-wechat-to-markdown](skills/lh-wechat-to-markdown/) | 微信公众号文章抓取与 Markdown 转换工具，支持浏览器自动化和 HTML 快照保存 |

## 贡献

欢迎 PR，敏感信息（密钥、token）请通过环境变量传入，不要硬编码。
