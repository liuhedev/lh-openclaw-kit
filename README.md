# lh-openclaw-kit

围绕 OpenClaw 的实用工具集，包含 scripts、skills 和 demos。

## 目录结构

```
lh-openclaw-kit/
├── scripts/
│   └── feishu/                    # 飞书相关脚本
│       ├── feishu_send.py         # 发图片/消息工具
│       └── feishu_send_card.py    # 飞书消息卡片发送器
├── demos/
│   └── cover-generator/           # 公众号封面图生成器
│       └── index.html
└── skills/                        # OpenClaw 自定义 Skills
    └── lh-edge-tts/               # 文字转语音 Skill
```

## scripts

| 脚本 | 说明 |
|------|------|
| [feishu_send.py](scripts/feishu/feishu_send.py) | 通过飞书 API 发送图片、文件或文字消息，支持本地路径和 URL |
| [feishu_send_card.py](scripts/feishu/feishu_send_card.py) | 飞书消息卡片发送器，支持 markdown、分割线、彩色标题头，适合日报/周报推送 |

详细用法见 [scripts/feishu/README.md](scripts/feishu/README.md)

## demos

| Demo | 说明 | 在线体验 |
|------|------|---------|
| [cover-generator](demos/cover-generator/) | 公众号封面图生成器，5 种配色，实时预览，900×383px | [GitHub Pages](https://liuhedev.github.io/lh-openclaw-kit/demos/cover-generator/) |

## skills

| Skill | 说明 |
|-------|------|
| [lh-edge-tts](skills/lh-edge-tts/) | 基于微软 Edge TTS 的文字转语音工具，支持多音色、语速调节和字幕导出 |

## 贡献

欢迎 PR，敏感信息（密钥、token）请通过环境变量传入，不要硬编码。
