#!/usr/bin/env python3
"""
飞书知识库文档同步：将本地 Markdown 文件同步到飞书文档

用法：
  # 同步单个文档（指定 md 路径和 doc_token）
  python3 feishu_wiki_sync.py <md_file> <doc_token>

  # 批量同步（通过 doc-map JSON 文件）
  python3 feishu_wiki_sync.py --doc-map feishu-doc-map.json [--articles-base /path/to/workspace]

doc-map JSON 格式：
  {
    "content/articles/2026-03-01/article.md": "FBSibkClaa...",
    "content/articles/2026-03-02/article.md": "XYZTokenHere"
  }

环境变量（均可选，有 --articles-base 参数时优先用参数）：
  FEISHU_ARTICLES_BASE   文章根目录，默认 ~/.openclaw/workspace
"""
import argparse
import json
import os
import re
import sys
import time
import mimetypes

from feishu_client import get_token, load_credentials


# ── 路径配置 ────────────────────────────────────────────────────────────────

def resolve_articles_base(cli_value=None):
    if cli_value:
        return os.path.expanduser(cli_value)
    env = os.environ.get("FEISHU_ARTICLES_BASE")
    if env:
        return os.path.expanduser(env)
    return os.path.expanduser("~/.openclaw/workspace")


BASE_URL = "https://open.feishu.cn/open-apis"


# ── API 工具 ────────────────────────────────────────────────────────────────

def api(token, method, path, data=None):
    import urllib.request
    import urllib.error
    headers = {"Authorization": f"Bearer {token}"}
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"  HTTP {e.code} {method} {path}: {err[:1000]}")
        try:
            return json.loads(err)
        except Exception:
            return {"code": e.code, "msg": err[:300]}


# ── Markdown 解析 ────────────────────────────────────────────────────────────

def strip_frontmatter(text):
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].lstrip("\n")
    return text


def get_code_lang(lang):
    lang_map = {
        "": 1, "python": 49, "javascript": 33, "typescript": 67, "bash": 7,
        "shell": 7, "sh": 7, "json": 34, "yaml": 74, "html": 28, "css": 14,
        "go": 24, "rust": 56, "java": 32, "c": 10, "cpp": 12, "sql": 61,
        "markdown": 41, "xml": 73, "plaintext": 1, "text": 1,
    }
    return lang_map.get(lang.lower(), 1)


def parse_inline(text):
    """解析行内 Markdown（粗体、行内代码、链接）为飞书 elements"""
    elements = []
    pos = 0
    pattern = re.compile(r'(\*\*(.+?)\*\*|`([^`]+)`|\[([^\]]+)\]\(([^)]+)\))')
    for m in pattern.finditer(text):
        if m.start() > pos:
            elements.append({"text_run": {"content": text[pos:m.start()]}})
        if m.group(2):
            elements.append({"text_run": {"content": m.group(2), "text_element_style": {"bold": True}}})
        elif m.group(3):
            elements.append({"text_run": {"content": m.group(3), "text_element_style": {"inline_code": True}}})
        elif m.group(4):
            url = m.group(5)
            if url.startswith("http://") or url.startswith("https://"):
                elements.append({"text_run": {"content": m.group(4), "text_element_style": {"link": {"url": url}}}})
            else:
                elements.append({"text_run": {"content": m.group(4)}})
        pos = m.end()
    if pos < len(text):
        elements.append({"text_run": {"content": text[pos:]}})
    if not elements:
        elements.append({"text_run": {"content": text}})
    return elements


def md_to_blocks(md_text):
    """将 Markdown 转换为飞书 block JSON 列表，返回 (blocks, image_indices)
    image_indices: [(block_index, image_path)]
    """
    blocks = []
    image_indices = []
    lines = md_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        img_match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', line.strip())
        if img_match:
            image_indices.append((len(blocks), img_match.group(2)))
            blocks.append({"block_type": 27, "image": {}})
            i += 1
            continue
        heading_match = re.match(r'^(#{1,9})\s+(.*)', line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            block_type = 2 + level  # heading1=3, heading2=4, ...
            key = f"heading{level}"
            blocks.append({
                "block_type": block_type,
                key: {"elements": [{"text_run": {"content": text}}]}
            })
            i += 1
            continue
        if line.strip().startswith("```"):
            lang_match = re.match(r'```(\w*)', line.strip())
            lang = lang_match.group(1) if lang_match else ""
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            blocks.append({
                "block_type": 14,
                "code": {
                    "elements": [{"text_run": {"content": "\n".join(code_lines)}}],
                    "language": get_code_lang(lang)
                }
            })
            continue
        bullet_match = re.match(r'^(\s*)[-*]\s+(.*)', line)
        if bullet_match:
            blocks.append({
                "block_type": 12,
                "bullet": {"elements": parse_inline(bullet_match.group(2))}
            })
            i += 1
            continue
        ordered_match = re.match(r'^(\s*)\d+\.\s+(.*)', line)
        if ordered_match:
            blocks.append({
                "block_type": 13,
                "ordered": {"elements": parse_inline(ordered_match.group(2))}
            })
            i += 1
            continue
        if re.match(r'^---+\s*$', line):
            blocks.append({"block_type": 22, "divider": {}})
            i += 1
            continue
        quote_match = re.match(r'^>\s*(.*)', line)
        if quote_match:
            blocks.append({
                "block_type": 2,
                "text": {"elements": parse_inline("> " + quote_match.group(1))}
            })
            i += 1
            continue
        blocks.append({
            "block_type": 2,
            "text": {"elements": parse_inline(line)}
        })
        i += 1
    return blocks, image_indices


# ── 文档操作 ────────────────────────────────────────────────────────────────

def clear_document(token, doc_token):
    result = api(token, "GET", f"/docx/v1/documents/{doc_token}/blocks/{doc_token}?document_revision_id=-1")
    if result.get("code") != 0:
        print(f"  Failed to get doc blocks: {result}")
        return False
    children = result.get("data", {}).get("block", {}).get("children", [])
    if not children:
        print("  Document already empty")
        return True
    print(f"  Deleting {len(children)} blocks...")
    for i in range(0, len(children), 50):
        batch = children[i:i + 50]
        del_result = api(token, "DELETE",
            f"/docx/v1/documents/{doc_token}/blocks/{doc_token}/children/batch_delete",
            {"start_index": 0, "end_index": len(batch)})
        if del_result.get("code") != 0:
            print(f"  Delete batch failed: {del_result}")
            time.sleep(1)
            result2 = api(token, "GET",
                f"/docx/v1/documents/{doc_token}/blocks/{doc_token}?document_revision_id=-1")
            children2 = result2.get("data", {}).get("block", {}).get("children", [])
            if children2:
                api(token, "DELETE",
                    f"/docx/v1/documents/{doc_token}/blocks/{doc_token}/children/batch_delete",
                    {"start_index": 0, "end_index": len(children2)})
        time.sleep(0.5)
    return True


def insert_blocks(token, doc_token, blocks, start_index=0):
    for i in range(0, len(blocks), 50):
        batch = blocks[i:i + 50]
        result = api(token, "POST",
            f"/docx/v1/documents/{doc_token}/blocks/{doc_token}/children",
            {"children": batch, "index": start_index + i})
        if result.get("code") != 0:
            print(f"  Insert batch {i}-{i + len(batch)} failed: {result.get('code')} {result.get('msg')}")
            return False
        print(f"  Inserted blocks {i}-{i + len(batch)}")
        time.sleep(0.5)
    return True


def upload_image(token, image_block_id, image_path):
    import urllib.request
    file_size = os.path.getsize(image_path)
    file_name = os.path.basename(image_path)
    mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
    boundary = "----PythonFormBoundary7MA4YWxkTrZu0gW"
    parts = []
    for name, value in [("file_name", file_name), ("parent_type", "docx_image"),
                         ("parent_node", image_block_id), ("size", str(file_size))]:
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}")
    with open(image_path, "rb") as f:
        file_data = f.read()
    body = b""
    for part in parts:
        body += part.encode() + b"\r\n"
    body += (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"{file_name}\"\r\nContent-Type: {mime_type}\r\n\r\n"
    ).encode()
    body += file_data
    body += f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{BASE_URL}/drive/v1/medias/upload_all", data=body,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    if result.get("code") != 0:
        print(f"  Upload FAILED: {result}")
        return None
    return result["data"]["file_token"]


def process_images(token, doc_token, image_indices, image_search_dirs=None):
    """处理文档中的图片占位块，上传并填充图片。
    image_search_dirs: 查找图片的目录列表（按顺序尝试）
    """
    if not image_indices:
        return
    time.sleep(1)
    result = api(token, "GET",
        f"/docx/v1/documents/{doc_token}/blocks/{doc_token}?document_revision_id=-1")
    children = result.get("data", {}).get("block", {}).get("children", [])
    image_block_ids = []
    for child_id in children:
        block_result = api(token, "GET", f"/docx/v1/documents/{doc_token}/blocks/{child_id}")
        block = block_result.get("data", {}).get("block", {})
        if block.get("block_type") == 27:
            image_block_ids.append(child_id)
        time.sleep(0.2)
    print(f"  Found {len(image_block_ids)} image blocks, expected {len(image_indices)}")
    for idx, (block_idx, img_path) in enumerate(image_indices):
        if idx >= len(image_block_ids):
            print(f"  Skipping image {img_path}: no matching block")
            continue
        image_block_id = image_block_ids[idx]
        full_path = None
        if os.path.isabs(img_path):
            full_path = img_path if os.path.exists(img_path) else None
        else:
            for search_dir in (image_search_dirs or []):
                candidate = os.path.join(search_dir, img_path.lstrip("/"))
                if os.path.exists(candidate):
                    full_path = candidate
                    break
        if not full_path:
            print(f"  Image not found: {img_path}")
            continue
        print(f"  Uploading {img_path} → block {image_block_id}")
        file_token = upload_image(token, image_block_id, full_path)
        if not file_token:
            continue
        time.sleep(0.5)
        patch_result = api(token, "PATCH",
            f"/docx/v1/documents/{doc_token}/blocks/{image_block_id}",
            {"replace_image": {"token": file_token}})
        if patch_result.get("code") == 0:
            print(f"  ✓ Image {img_path} done")
        else:
            print(f"  ✗ Patch failed: {patch_result}")
        time.sleep(0.5)


def sync_document(token, md_path, doc_token, articles_base, image_search_dirs=None):
    """将单个 Markdown 文件同步到飞书文档"""
    full_path = md_path if os.path.isabs(md_path) else os.path.join(articles_base, md_path)
    print(f"\n{'=' * 60}")
    print(f"Syncing: {md_path} → {doc_token}")
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = strip_frontmatter(content)
    blocks, image_indices = md_to_blocks(content)
    print(f"  Generated {len(blocks)} blocks, {len(image_indices)} images")
    clear_document(token, doc_token)
    time.sleep(1)
    if not insert_blocks(token, doc_token, blocks):
        print("  FAILED to insert blocks")
        return False
    if image_indices:
        print(f"  Processing {len(image_indices)} images...")
        process_images(token, doc_token, image_indices, image_search_dirs)
    print(f"  ✓ Done: {md_path}")
    return True


# ── 状态回写（可选依赖）────────────────────────────────────────────────────

def try_update_status(articles_base, md_path, doc_token):
    try:
        sys.path.insert(0, os.path.join(articles_base, "scripts"))
        from ops.status_utils import update_platform_status, update_platform_url
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', md_path)
        if date_match:
            article_dir = os.path.join(articles_base, "content", "articles", date_match.group(1))
            if os.path.isdir(article_dir):
                update_platform_status(article_dir, "feishu_wiki", "done")
                update_platform_url(article_dir, "feishu_wiki",
                    f"https://lobster-he.feishu.cn/wiki/{doc_token}")
    except ImportError:
        pass


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Markdown → 飞书文档同步工具")
    parser.add_argument("md_file", nargs="?", help="Markdown 文件路径（单文档模式）")
    parser.add_argument("doc_token", nargs="?", help="飞书文档 token（单文档模式）")
    parser.add_argument("--doc-map", help="doc-map JSON 文件路径（批量模式）")
    parser.add_argument("--articles-base", help="文章根目录（默认: ~/.openclaw/workspace 或 FEISHU_ARTICLES_BASE 环境变量）")
    parser.add_argument("--image-dir", action="append", dest="image_dirs",
                        help="图片查找目录，可多次指定")
    parser.add_argument("--account", default="main", help="飞书账号名（默认: main）")
    args = parser.parse_args()

    if not args.md_file and not args.doc_map:
        parser.print_help()
        sys.exit(1)

    load_credentials(args.account)
    token = get_token(args.account)
    articles_base = resolve_articles_base(args.articles_base)
    image_dirs = args.image_dirs or []

    if args.md_file and args.doc_token:
        # 单文档模式
        success = sync_document(token, args.md_file, args.doc_token, articles_base, image_dirs)
        if success:
            try_update_status(articles_base, args.md_file, args.doc_token)
        sys.exit(0 if success else 1)

    # 批量模式
    doc_map_path = args.doc_map
    with open(doc_map_path, encoding="utf-8") as f:
        doc_map = json.load(f)

    results = {}
    for md_path, doc_token in doc_map.items():
        try:
            success = sync_document(token, md_path, doc_token, articles_base, image_dirs)
            results[md_path] = "✓" if success else "✗"
            if success:
                try_update_status(articles_base, md_path, doc_token)
        except Exception as e:
            import traceback
            traceback.print_exc()
            results[md_path] = f"✗ {e}"
        time.sleep(2)

    print(f"\n{'=' * 60}")
    print("Results:")
    for path, status in results.items():
        print(f"  {status} {path}")


if __name__ == "__main__":
    main()
