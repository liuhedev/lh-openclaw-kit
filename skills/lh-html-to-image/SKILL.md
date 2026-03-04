---
name: lh-html-to-image
description: Generate images from HTML+CSS via Chrome headless screenshot. Perfect for covers, posters, info cards, and text-layout images. Zero API cost, 100% accurate text rendering. Triggers: "generate cover", "poster", "HTML to image", "make image".
homepage: https://github.com/liuhedev/lh-openclaw-kit
---

# HTML 转图片

用 HTML+CSS 编写视觉设计，通过 Chrome headless 截图生成 PNG。适合大字报封面、信息卡片等文字排版类图片。

## 适用场景

- ✅ 大字报封面（标题+副标题+标签）
- ✅ 信息卡片（数据展示、对比图）
- ✅ 文字排版类图片（引用卡、金句卡）
- ❌ 插画、照片类（用 baoyu-image-gen）

## 工作流程

### Step 1：编写 HTML

在 `tmp/` 下创建 HTML 文件，要点：

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {
    /* 设置画布尺寸 */
    width: 1080px;    /* 根据需要调整 */
    height: 1440px;   /* 3:4 竖屏 */
    margin: 0;
    overflow: hidden;
    font-family: -apple-system, "PingFang SC", "Noto Sans SC", sans-serif;
  }
</style>
</head>
<body>
  <!-- 内容 -->
</body>
</html>
```

### Step 2：Chrome headless 截图

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new \
  --disable-gpu \
  --screenshot="输出路径.png" \
  --window-size=宽,高 \
  --hide-scrollbars \
  --force-device-scale-factor=2 \
  "file:///HTML文件绝对路径"
```

### Step 3：发送图片

```bash
openclaw message send \
  --channel feishu \
  --account main \
  --target <your_feishu_open_id> \
  --media "图片路径" \
  --message "说明文字"
```

## 常用尺寸

| 用途 | 宽×高 | 比例 |
|------|-------|------|
| 小红书封面 | 1080×1440 | 3:4 |
| 小红书方图 | 1080×1080 | 1:1 |
| 微信封面（宽） | 1280×720 | 16:9 |
| 微信封面（方） | 1080×1080 | 1:1 |

## 品牌色

| 名称 | 色值 | 用途 |
|------|------|------|
| 龙虾红 | #D32F2F | 主色、高亮 |
| 深海蓝 | #1E3A5F | 辅助色 |
| 暗色背景 | #0D1B2A | 深色底 |
| 亮红 | #FF6B6B | 强调、标签 |
| 浅蓝 | #48CAE4 | 副标题、装饰 |

## 设计模板

### 大字报封面（深色底）
- 背景：#0D1B2A + 半透明装饰圆
- 标题：白色大字 + 红色高亮关键词
- 副标题：浅蓝色
- 底部：标签 + 署名
- 参考：`tmp/xhs-blog-fix/cover.html`

## 注意事项

- Chrome 路径（macOS）：`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- GPU 错误日志可忽略，不影响截图
- 中文字体用 PingFang SC（macOS 自带）
- `--force-device-scale-factor=1` 确保尺寸精确
- 生成后直接发飞书，不给路径
