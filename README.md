# lh-openclaw-kit

围绕 OpenClaw 的实用工具集，包含 scripts 和 skills。

## 目录结构

```
lh-openclaw-kit/
├── scripts/              # 通用自动化脚本
│   └── feishu_send.py    # 飞书发图片/消息工具
└── skills/               # OpenClaw 自定义 Skills
    └── lh-edge-tts/      # 文字转语音 Skill
```

## scripts

| 脚本 | 说明 |
|------|------|
| [feishu_send.py](scripts/feishu_send.py) | 通过飞书 API 发送图片、文件或文字消息，支持本地路径和 URL |

详细用法见 [scripts/feishu_send_README.md](scripts/feishu_send_README.md)

## skills

| Skill | 说明 |
|-------|------|
| [lh-edge-tts](skills/lh-edge-tts/) | 基于微软 Edge TTS 的文字转语音工具，支持多音色、语速调节和字幕导出 |

## 贡献

欢迎 PR，敏感信息（密钥、token）请通过环境变量传入，不要硬编码。
