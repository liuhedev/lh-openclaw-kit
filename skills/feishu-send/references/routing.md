# Routing Rules

## 子命令选择

| 场景 | 子命令 |
|------|--------|
| 本地文件（docx/pdf/zip 等非图片） | `file` |
| 本地图片或图片 URL | `image` |
| 纯文本消息 | `text` |

## 图片扩展名

`.jpg` `.jpeg` `.png` `.gif` `.webp` `.bmp` `.ico` `.tiff` `.svg`

## 文件发送链路（核心）

本地文件必须走：
1. 上传文件到飞书 → 获取 `file_key`
2. 发送 `file` 类型消息（携带 `file_key`）

**绝不能把路径字符串本身发送到飞书。**

## 接收目标

| 格式 | 说明 |
|------|------|
| `ou_xxx` | 用户 open_id，发 DM |
| `oc_xxx` | 群聊 chat_id |
| 不传 | 读 `FEISHU_DEFAULT_TO` 环境变量 |
