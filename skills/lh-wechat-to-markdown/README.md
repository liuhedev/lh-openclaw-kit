# lh-wechat-to-markdown

抓取微信公众号文章并转换为干净的 Markdown 格式，同时保存渲染后的 HTML 快照。

## 快速开始

```bash
# 依赖安装
pip install -r requirements.txt
playwright install chromium
```

## 常用命令
```bash
# 默认：无头模式自动抓取公开文章
python3 scripts/main.py <微信文章链接>

# 保存到指定文件
python3 scripts/main.py <微信文章链接> -o output.md

# 自动下载图片到本地 images/ 目录，链接自动替换为相对路径
python3 scripts/main.py <微信文章链接> --download-images

# 有头模式 + 等待人工确认（用于需要登录/有访问限制的文章）
python3 scripts/main.py <微信文章链接> --headed --wait
```

## 说明
- 默认采用无头模式抓取公开可访问的文章，无需人工干预
- 遇到需要登录或有访问限制的内容，使用 `--headed --wait` 打开可视浏览器，完成验证后按 Enter 触发抓取
- 开启 `--download-images` 时会自动下载正文图片到本地，避免图片链接失效

完整文档请见 [SKILL.md](./SKILL.md)