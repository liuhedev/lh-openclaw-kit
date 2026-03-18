
---
name: lh-wechat-to-markdown
description: |
  抓取微信公众号文章并转换为 Markdown，支持自动下载图片、保存 HTML 快照。
  触发关键词："抓取微信文章"、"保存公众号文章"、"微信转 markdown"、"wechat article"。
version: 1.2.1
metadata:
  openclaw:
    homepage: https://github.com/liuhedev/lh-openclaw-kit
    requires:
      anyBins:
        - python3
---

# 微信公众号文章转 Markdown

## 1. 功能与适用场景
抓取微信公众号文章，转换为干净的 Markdown 格式，同时保存渲染后的 HTML 快照。
适用场景：
- 个人收藏/归档公众号文章
- 内容二次加工（需获得原创授权）
- 离线阅读

## 2. 基础用法
```bash
# 默认：无头模式自动抓取公开文章
python3 {baseDir}/scripts/main.py <微信文章链接>

# 保存到指定文件
python3 {baseDir}/scripts/main.py <微信文章链接> -o output.md

# 自动下载图片到本地
python3 {baseDir}/scripts/main.py <微信文章链接> --download-images

# 自定义输出目录
python3 {baseDir}/scripts/main.py <微信文章链接> --output-dir ./wechat-articles/
```

## 3. 推荐工作流
- **默认场景（公开文章）**：直接使用默认无头模式，无需人工干预
- **需要登录/有访问限制的文章**：使用 `--headed --wait` 参数，打开可视浏览器，完成登录/验证后按 Enter 触发抓取：
  ```bash
  python3 {baseDir}/scripts/main.py <微信文章链接> --headed --wait
  ```

## 4. 输出结果与注意事项
### 输出文件
1. Markdown 文件：包含标题、作者、发布时间等元数据 + 正文内容
2. HTML 快照：与 Markdown 同名的 `*-captured.html` 文件，保存渲染后的原始页面
3. （启用 `--download-images` 时）图片保存到 Markdown 同级 `images/` 目录，链接自动替换为相对路径

### 注意事项
- 仅抓取您有权访问和使用的内容，尊重原创版权
- 遵守微信服务条款，不要用于批量抓取或商业用途
