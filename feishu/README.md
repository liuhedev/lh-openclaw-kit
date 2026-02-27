# feishu_send.py

通过飞书 API 发送图片、文件或文字消息。支持本地路径和 URL。

## 依赖

```bash
pip install requests python-dotenv
```

## 环境变量配置

在 `~/.openclaw/.env` 或项目根目录 `.env` 中配置：

```
FEISHU_APP_ID=cli_xxxxxxxx
FEISHU_APP_SECRET=xxxxxxxx
FEISHU_DEFAULT_TO=ou_xxxxxxxx   # 可选，默认接收人 open_id
```

## 用法

```bash
# 发图片
python3 feishu_send.py image.png --to ou_xxxxxxxx

# 发图片 + 文字说明
python3 feishu_send.py image.png --to ou_xxxxxxxx --caption "这是说明"

# 发 URL 图片
python3 feishu_send.py https://example.com/image.png --to ou_xxxxxxxx

# 不指定 --to，使用默认接收人（需配置 FEISHU_DEFAULT_TO）
python3 feishu_send.py image.png
```
