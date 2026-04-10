---
name: lh-url-to-markdown
description: 抓取任意 URL，经 Chrome CDP 完整渲染后转为 Markdown，并可本地化图片和视频。用于把网页、文章、文档、帖子、页面链接保存下来做收藏、归档、稍后阅读、学习沉淀、知识库入库、转 Markdown、网页转 md、保存网页内容、抓取网页正文等场景；当用户贴出 URL 并说“收藏这篇”“保存这个链接”“留着学习”“学习这篇”“归档一下”“转成 Markdown”“抓成 md”“存到本地”时触发。
metadata:
  openclaw:
    homepage: https://github.com/liuhedev/lh-openclaw-kit
    requires:
      anyBins:
        - bun
        - npx
---

# URL 转 Markdown（lh-url-to-markdown）

通过 Chrome CDP 拉取并渲染页面，输出带元数据的 Markdown。

## 意图映射

将下面这些表达视为本技能的直接触发信号，即使用户没有明确说“转 Markdown”也应命中：

- 收藏这篇 / 收藏这个链接 / 先存一下
- 留着学习 / 稍后看 / 稍后阅读
- 归档这篇文章 / 沉淀到本地 / 入库到知识库前先抓下来
- 把这个网页保存成 md / 转成 Markdown / 网页转 md
- 抓取这个链接 / 保存正文 / 拉成 Markdown

## Agent 执行顺序（必读）

1. 将本 `SKILL.md` 所在目录记为 `{baseDir}`；**仅直接运行** `{baseDir}/scripts/main.ts`。
2. 解析运行时：`bun` 可用则用 `bun`，否则 `npx -y bun`；下文 `${BUN_X}`、`{baseDir}` 替换为实际值。
3. 当前实现仅支持命令行参数和环境变量控制，不读取 `EXTEND.md`，也没有内建首轮偏好初始化流程。

## 脚本说明

| 脚本 | 作用 |
|------|------|
| `scripts/main.ts` | **唯一入口**，由 Agent 直接执行 |
| `scripts/html-to-markdown.ts` | 内部：HTML→Markdown（Defuddle 优先，失败则降级 legacy） |
| `scripts/cdp.ts` | 内部：CDP 启动、页面捕获、跨平台路径与超时 |
| `scripts/media-localizer.ts` | 内部：媒体下载与 Markdown 链接重写 |

## 运行配置

当前实现支持以下控制方式：

| 方式 | 支持项 |
|------|--------|
| CLI 参数 | `-o`、`--output-dir`、`--wait`、`--timeout`、`--download-media` |
| 环境变量 | `URL_CHROME_PATH`、`URL_DATA_DIR`、`URL_CHROME_PROFILE_DIR` |

优先级：命令行参数 > 环境变量 > 脚本默认值。

## 功能要点

- Chrome CDP 全量执行 JS 后的 DOM
- 抓取模式：默认自动；`--wait` 等用户就绪（登录、懒加载、付费墙）
- Defuddle 优先，异常或质量明显差时自动回退到历史 legacy 管线
- 可选将图片/视频拉到本地并重写链接

## 命令示例

```bash
# 默认：网络空闲后抓取
${BUN_X} {baseDir}/scripts/main.ts <url>

# 等待用户在终端按 Enter 后再抓取
${BUN_X} {baseDir}/scripts/main.ts <url> --wait

# 指定输出文件
${BUN_X} {baseDir}/scripts/main.ts <url> -o output.md

# 指定输出目录（自动生成 slug 文件名）
${BUN_X} {baseDir}/scripts/main.ts <url> --output-dir ./posts/

# 本次强制下载媒体并改写链接
${BUN_X} {baseDir}/scripts/main.ts <url> --download-media
```

## 命令行选项

| 选项 | 说明 |
|------|------|
| `<url>` | 目标地址 |
| `-o <path>` | 输出 **文件** 路径（非目录）；默认按规则生成 |
| `--output-dir <dir>` | 输出目录，生成 `{dir}/{slug}.md`；未指定时默认为 cwd 下 `url-to-markdown/`（或 `URL_DATA_DIR`） |
| `--wait` | 等待用户信号再截图/抓 HTML |
| `--timeout <ms>` | 页面超时，默认 `30000` |
| `--download-media` | 下载图片/视频到同级 `imgs/`、`videos/`，并重写为相对路径 |

## 抓取模式

| 模式 | 行为 | 适用 |
|------|------|------|
| 自动（默认） | 网络空闲后捕获 | 公开页、静态内容 |
| `--wait` | 终端提示后由用户确认再捕获 | 需登录、强懒加载、付费墙 |

**`--wait` 流程**：脚本输出 `Page opened. Press Enter when ready to capture...` → 确认用户页面就绪 → 向 stdin 发送换行触发捕获。

## 输出说明

每次运行默认产出一个 Markdown 文件：

- **Markdown**：YAML front matter（`url`、`title`、`description`、`author`、`published`、可选 `coverImage`、`captured_at`）+ 正文

默认路径：`url-to-markdown/<slug>.md`。`--output-dir ./posts/` 时为 `./posts/<slug>.md`。

- `slug`：优先页面标题，否则取自 URL；去除路径非法字符，最长约 80 字符（与 `main.ts` 一致）
- 重名：追加时间戳 `<slug>-YYYYMMDD-HHMMSS.md`

启用 `--download-media` 时：`imgs/`、`videos/` 与 Markdown 同级，链接改为相对路径。

## 转换降级

1. 先试 Defuddle  
2. 若抛错、无法加载、产出明显残缺或劣于 legacy，则自动回退到基于 Readability/选择器/Next 数据等的旧实现  
3. 日志：`Converter: defuddle` 或 `Converter: legacy:...` 及 `Fallback used: ...`

## 媒体下载

- 默认保留远程媒体 URL。
- 需要本地化图片/视频时，显式加 `--download-media`。

## 环境变量与排错

| 变量 | 作用 |
|------|------|
| `URL_CHROME_PATH` | 指定 Chrome 可执行文件 |
| `URL_DATA_DIR` | 覆盖默认输出根目录（未设置时脚本使用 `cwd/url-to-markdown`） |
| `URL_CHROME_PROFILE_DIR` | Chrome Profile 目录 |

找不到 Chrome → 设 `URL_CHROME_PATH`。超时 → 增大 `--timeout`。复杂页 → 试 `--wait`。Markdown 质量差 → 重点看 `Converter` 与 `Fallback used` 日志判断是否走了 legacy。
