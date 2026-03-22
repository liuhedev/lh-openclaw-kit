---
name: feishu-doc
description: >
  Write, sync, and manage content inside Feishu (飞书) Wiki documents via direct
  API calls. Use this skill whenever the user wants to push Markdown content into
  a Feishu doc, insert or batch-upload images into a Feishu Wiki document, list
  document blocks, or sync a local article to a Feishu knowledge base. Triggers
  include: "同步到飞书", "推送到知识库", "飞书文档插图", "批量插图", "把文章同步到飞书",
  "feishu wiki sync", "update feishu doc", "push markdown to feishu",
  or any task involving writing structured content into a Feishu docx document.
allowed-tools:
  - Bash
---

# feishu-doc

飞书文档内容写入与图片管理。解决两个核心场景：

1. **Markdown → 飞书文档同步**：将本地 `.md` 文件的内容（标题、正文、代码块、列表、图片）完整推送到指定飞书文档（清空旧内容后重建）。
2. **文档插图**：向已有飞书文档的任意位置插入图片，走三步法（创建空块 → 上传素材 → PATCH 填充），规避飞书 API 的两阶段图片限制。

## 脚本

| 脚本 | 功能 |
|------|------|
| `feishu_wiki_sync.py` | Markdown 文件同步到飞书文档（单文档 / 批量） |
| `feishu_wiki_image.py` | 飞书文档插图（list / insert / batch） |

依赖 `feishu_client.py`（同 `scripts/` 目录下）。

## 凭证加载

与 `feishu-send` 一致，优先级：

1. 进程已有环境变量（`FEISHU_MAIN_APP_ID` / `FEISHU_MAIN_APP_SECRET`）
2. `~/.config/dev-workflow/.env`
3. `~/.openclaw/.env`
4. `~/.openclaw/openclaw.json`（`channels.feishu.accounts.<账号名>`）

所有脚本支持 `--account <账号名>`（默认 `main`），或通过 `FEISHU_ACCOUNT` 环境变量指定。

## 使用方法

在 **`skills/feishu-doc/`** 目录下执行脚本。

### 同步 Markdown 到飞书文档

```bash
# 单文档
python3 scripts/feishu_wiki_sync.py <md_file> <doc_token>

# 单文档 + 指定图片查找目录
python3 scripts/feishu_wiki_sync.py article.md doxcnXXXX --image-dir /path/to/images

# 批量（通过 doc-map JSON）
python3 scripts/feishu_wiki_sync.py --doc-map feishu-doc-map.json

# 批量 + 自定义文章根目录
python3 scripts/feishu_wiki_sync.py --doc-map feishu-doc-map.json --articles-base ~/myworkspace
```

**doc-map JSON 格式：**
```json
{
  "content/articles/2026-03-01/article.md": "FBSibkClaa...",
  "content/articles/2026-03-22/article.md": "XYZTokenHere"
}
```

**路径解析规则：**
- 绝对路径：直接使用
- 相对路径：从 `--articles-base`（或 `FEISHU_ARTICLES_BASE` 环境变量，默认 `~/.openclaw/workspace`）拼接

**图片路径解析：**
- 绝对路径：直接使用
- 相对路径：按 `--image-dir` 指定的目录列表依次查找

### 文档插图

```bash
# 列出文档所有 block（含 block_type 和文本预览）
python3 scripts/feishu_wiki_image.py list <doc_token>

# 在指定位置插入单张图片
python3 scripts/feishu_wiki_image.py insert <doc_token> <image_path> <index>

# 批量插入（格式 path:index，自动按 index 排序并修正偏移）
python3 scripts/feishu_wiki_image.py batch <doc_token> cover.png:0 chart.png:3
```

## 支持的 Markdown 格式

| 语法 | 飞书 block 类型 |
|------|----------------|
| `# H1` ~ `######### H9` | heading1 ~ heading9 |
| 普通段落 | text |
| `` ``` `` 代码块（支持语言标注） | code（含语言映射） |
| `- item` / `* item` | bullet |
| `1. item` | ordered |
| `---` | divider |
| `> 引用` | text（前缀保留） |
| `![alt](path)` | image（三步法上传） |
| `**粗体**` | bold text_run |
| `` `行内代码` `` | inline_code text_run |
| `[链接文字](url)` | link text_run（仅 http/https） |

## 注意事项

- 同步前会**清空文档全部内容**，请确认 doc_token 正确
- 飞书图片上传限制：单张建议 < 20MB
- 批量插入时自动处理 index 偏移（每成功插入一张 +1）
- `status.json` 回写为可选功能，依赖 workspace 内的 `scripts/ops/status_utils.py`，缺失时静默跳过
