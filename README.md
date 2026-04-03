# lh-openclaw-kit

围绕 OpenClaw 的 Agent Skills 集合，本仓库仅包含 `skills/` 下的各技能目录。

## skills

| Skill | 说明 |
|-------|------|
| [feishu-send](skills/feishu-send/) | 通过飞书开放平台 API 发送文件、图片、文本、结构化卡片、巡检报告、分发进度、工作日报 |
| [feishu-bitable](skills/feishu-bitable/) | 通过飞书 API 直接读写多维表格（Bitable）记录，支持查询、新增、修改、删除 |
| [feishu-doc](skills/feishu-doc/) | 将 Markdown 推送到飞书知识库文档，支持批量插图、内容块增删改查、文件上传 |
| [lh-deepwiki](skills/lh-deepwiki/) | 通过 DeepWiki MCP 查询 GitHub 仓库文档结构与 AI 问答 |
| [lh-edge-tts](skills/lh-edge-tts/) | 基于微软 Edge TTS 的文字转语音工具，支持多音色、语速调节和字幕导出 |
| [lh-html-to-image](skills/lh-html-to-image/) | 通过 Chrome 无头截图将 HTML+CSS 渲染为独立图片，适用于封面图、海报、信息卡片 |
| [lh-url-to-markdown](skills/lh-url-to-markdown/) | 通过 Chrome CDP 抓取任意 URL 并转为 Markdown，保存 HTML 快照，支持媒体本地化；可配合登录/等待用户信号 |
| [lh-video-gen](skills/lh-video-gen/) | 从 Markdown 脚本一键生成竖版短视频（9:16），内部联动 lh-edge-tts 和 lh-html-to-image |
| [send-email](skills/send-email/) | 通过 SMTP 发信（企业微信/QQ/163/Gmail/Outlook 等），Markdown 正文转 HTML，支持多附件、抄送、HTML 签名 |

## 安装

通过 [skills CLI](https://skills.sh) 一键安装到任意 AI Agent：

```bash
# 安装全部 skills
npx skills add liuhedev/lh-openclaw-kit

# 安装指定 skill
npx skills add liuhedev/lh-openclaw-kit --skill feishu-send
```

## 贡献

欢迎 PR，敏感信息（密钥、token）请通过环境变量传入，不要硬编码。
