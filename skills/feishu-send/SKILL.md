---
name: feishu-send
description: >
  Send files, images, text messages, and structured cards to Feishu (飞书) / Lark
  reliably via direct API calls. Solves the core problem of local file paths being
  sent as plain text instead of real attachments — a known issue with generic message
  tools. Use this skill whenever the user wants to deliver anything to Feishu,
  including: "发到飞书", "发群里", "发给我", "发文件", "发图片", "发这个", "发卡片",
  "send to feishu", "send file to lark", "把 xxx 发到飞书", or any situation where
  a local file path or image needs to arrive as a real attachment.
  Also use when an agent task produces output files or structured reports that need
  to be delivered to a Feishu user or group.
allowed-tools:
  - Bash
---

# feishu-send

解决 OpenClaw 及通用 Agent 发送文件/图片时不稳定的问题。

**为什么需要这个 skill？**
OpenClaw 的通用 `message` 工具在飞书渠道下，发送本地文件时容易把路径字符串当纯文本发出去，而不是真正的附件。这个 skill 直接调用飞书 API，走"上传 → 获取 key → 发送"的完整链路，确保文件和图片始终作为真实附件到达。

## 脚本路径

入口文件为 skill 内的 `scripts/feishu_send.py`。在 **`skills/feishu-send/` 目录下**（与 `SKILL.md` 同级）执行：

```bash
python3 scripts/feishu_send.py <子命令> <参数>
```

共享客户端仍按「仓库根 → `scripts/feishu/`」解析（OpenClaw workspace、lh-openclaw-kit 等常见布局均适用）。若必须在仓库根一键调用，可用 `python3 skills/feishu-send/scripts/feishu_send.py`（等价）。

### 共享客户端（feishu_client.py）

脚本依赖目录中的 `feishu_client.py`（及卡片所需的 `feishu_card_utils.py`），解析顺序：

1. 环境变量 **`FEISHU_CLIENT_ROOT`**：指向**含有** `feishu_client.py` 的目录（可用 `export` 或写入下文 `.env`）。
2. 若未设置：从本脚本位置向上推断仓库根，尝试 `<仓库根>/scripts/feishu/`（与 lh-openclaw-kit、OpenClaw workspace 等常见布局一致）。

仅当 skill 被拆出、或仓库无 `scripts/feishu/` 时，必须配置 `FEISHU_CLIENT_ROOT`。

**推荐在 `~/.config/dev-workflow/.env` 中配置（脚本启动时会自动 `setdefault` 加载）：**

```env
FEISHU_CLIENT_ROOT=/绝对路径/到/scripts/feishu
```

## 凭证加载（自动，无需手动配置）

优先级（后者仅补充尚未设置的键）：

1. 进程已有环境变量（如 `FEISHU_MAIN_APP_ID` / `FEISHU_MAIN_APP_SECRET`，或与飞书应用文档一致的键）
2. `~/.config/dev-workflow/.env`（由本脚本预载）
3. `~/.openclaw/.env`
4. `~/.openclaw/openclaw.json`（`channels.feishu.accounts.main`）

## 用法

在 **`skills/feishu-send/`** 下执行（相对仓库根可先 `cd skills/feishu-send`）：

```bash
python3 scripts/feishu_send.py <子命令> <参数>
```

### 发送文件

```bash
python3 scripts/feishu_send.py file <路径> [--to <id>] [--caption <说明>]
```

强制走文件上传 → 获取 file_key → 发送 file message，绝不发路径文本。

**示例：**
```bash
python3 scripts/feishu_send.py file /tmp/report.docx --caption "月度报告"
python3 scripts/feishu_send.py file output.pdf --to oc_xxx
```

### 发送图片

```bash
python3 scripts/feishu_send.py image <路径或URL> [--to <id>] [--caption <说明>]
```

支持本地路径和 HTTP URL，超 3MB 自动压缩（依赖 Pillow，可选）。

**示例：**
```bash
python3 scripts/feishu_send.py image cover.png --caption "今日封面"
python3 scripts/feishu_send.py image https://example.com/img.jpg --to ou_xxx
```

### 发送文本

```bash
python3 scripts/feishu_send.py text <消息> [--to <id>]
```

**示例：**
```bash
python3 scripts/feishu_send.py text "部署完成 ✅"
```

### 发送结构化卡片

```bash
python3 scripts/feishu_send.py card <标题> --items <json文件> [--to <id>] [--color blue|green|orange|red|purple]
```

适合日报、列表、摘要等结构化内容。items JSON 格式：

```json
[
  {"summary": "摘要", "insight": "借鉴点", "author": "作者", "url": "链接"},
  {"summary": "另一条", "url": "https://..."}
]
```

`insight`、`author`、`url` 均为可选字段。

**示例：**
```bash
python3 scripts/feishu_send.py card "今日要闻" --items /tmp/news.json --color blue
python3 scripts/feishu_send.py card "周报摘要" --items items.json --to oc_xxx --color green
```

## 接收目标

| 格式 | 说明 |
|------|------|
| `ou_xxx` | 用户 DM（open_id） |
| `oc_xxx` | 群聊（chat_id） |
| 不传 | 读 `FEISHU_DEFAULT_TO` 环境变量，或 openclaw.json allowFrom 首个 ou_ 用户 |

## 依赖

- Python 3.10+
- `requests`（`pip install requests`）
- `Pillow`（可选，图片压缩，`pip install Pillow`）

## 输出

成功：
```
✅ [已发送] 文件：report.docx  message_id: om_xxx
✅ [已发送] 图片：cover.png  message_id: om_xxx
✅ [已发送] 文本消息  message_id: om_xxx
✅ [已发送] 卡片：今日要闻  message_id: om_xxx
```

失败：
```
❌ 文件不存在: /tmp/xxx.docx
RuntimeError: 获取 token 失败: {...}
```

详细排查见 `references/troubleshooting.md`
