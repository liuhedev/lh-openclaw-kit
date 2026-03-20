# Troubleshooting

## 现象：飞书里收到的是文件路径文本，不是附件

原因：发送链路走错了，把路径当文本发了。

处理：
- 确认使用了 `file` 子命令
- 确认脚本走的是上传 → 获取 file_key → 发送 file message 链路

## 现象：文件不存在

处理：
- 检查路径是否正确（支持绝对路径和相对路径）
- 确认文件未被清理或移动

## 现象：token 获取失败

处理：
- 检查环境变量或 `~/.config/dev-workflow/.env` / `~/.openclaw/.env` 中的飞书应用凭证
- 确认飞书应用未过期、未被禁用

## 现象：未找到飞书共享客户端 / FEISHU_CLIENT_ROOT 无效

处理：
- 在 `~/.config/dev-workflow/.env` 或环境中设置 `FEISHU_CLIENT_ROOT` 为包含 `feishu_client.py` 的目录绝对路径
- 或将本 skill 放在含 `scripts/feishu/feishu_client.py` 的标准仓库根下

## 现象：receive_id 无效 / 发送失败

处理：
- 群聊用 `oc_` 开头的 chat_id
- 用户用 `ou_` 开头的 open_id
- 不传 `--to` 时确认 `FEISHU_DEFAULT_TO` 已配置

## 现象：图片发送失败

处理：
- 检查文件大小（飞书图片限制 10MB）
- 超 3MB 会自动压缩，需安装 Pillow：`pip install Pillow`
- 确认图片格式合法（jpg/png/gif/webp 等）

## 现象：上传文件报 400 Bad Request

处理：
- 检查文件大小不超过 30MB
- 确认飞书应用有 `im:message:create` 权限
