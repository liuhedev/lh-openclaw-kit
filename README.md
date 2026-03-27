# lh-openclaw-kit

围绕 OpenClaw 的实用工具集，包含 skills 和 demos。

## skills

| Skill | 说明 |
|-------|------|
| [feishu-send](skills/feishu-send/) | 通过飞书开放平台 API 发送文件、图片、文本、结构化卡片、巡检报告、分发进度、工作日报 |
| [feishu-bitable](skills/feishu-bitable/) | 通过飞书 API 直接读写多维表格（Bitable）记录，支持查询、新增、修改、删除 |
| [feishu-doc](skills/feishu-doc/) | 将 Markdown 推送到飞书知识库文档，支持批量插图、内容块增删改查、文件上传 |
| [lh-deepwiki](skills/lh-deepwiki/) | 通过 DeepWiki MCP 查询 GitHub 仓库文档结构与 AI 问答 |
| [lh-edge-tts](skills/lh-edge-tts/) | 基于微软 Edge TTS 的文字转语音工具，支持多音色、语速调节和字幕导出 |
| [lh-html-to-image](skills/lh-html-to-image/) | 通过 Chrome 无头截图将 HTML+CSS 渲染为独立图片，适用于封面图、海报、信息卡片 |
| [lh-video-gen](skills/lh-video-gen/) | 从 Markdown 脚本一键生成竖版短视频（9:16），内部联动 lh-edge-tts 和 lh-html-to-image |
| [lh-wechat-to-markdown](skills/lh-wechat-to-markdown/) | 微信公众号文章抓取与 Markdown 转换，自动修复图片懒加载、下载图片、保存 HTML 快照 |

## 贡献

欢迎 PR，敏感信息（密钥、token）请通过环境变量传入，不要硬编码。
