#!/usr/bin/env python3
"""
飞书知识库文档图片插入工具

三步法：1.创建空 Image Block → 2.上传图片素材 → 3.PATCH 设置素材

用法：
  python3 feishu_wiki_image.py list   <doc_token>
  python3 feishu_wiki_image.py insert <doc_token> <image_path> <index>
  python3 feishu_wiki_image.py batch  <doc_token> <image1:index1> [image2:index2] ...

示例：
  python3 feishu_wiki_image.py list   doxcnXXXXXX
  python3 feishu_wiki_image.py insert doxcnXXXXXX cover.png 0
  python3 feishu_wiki_image.py batch  doxcnXXXXXX cover.png:0 chart.png:3
"""
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request

from feishu_client import get_token, load_credentials

BASE_URL = "https://open.feishu.cn/open-apis"


# ── API 工具 ────────────────────────────────────────────────────────────────

def api_post(token, path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}", data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  HTTP {e.code}: {error_body[:500]}")
        return json.loads(error_body) if error_body else {"code": e.code, "msg": str(e)}


def api_patch(token, path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}", data=body, method="PATCH",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  HTTP {e.code}: {error_body[:500]}")
        return json.loads(error_body) if error_body else {"code": e.code, "msg": str(e)}


def api_get(token, path):
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


# ── 三步插图 ────────────────────────────────────────────────────────────────

def step1_create_image_block(token, doc_token, index):
    """Step 1: 创建空 Image Block，返回 block_id"""
    result = api_post(token,
        f"/docx/v1/documents/{doc_token}/blocks/{doc_token}/children",
        {"children": [{"block_type": 27, "image": {}}], "index": index}
    )
    if result.get("code") != 0:
        print(f"  Step1 FAILED: {result.get('code')} {result.get('msg')}")
        return None
    children = result.get("data", {}).get("children", [])
    if children:
        block_id = children[0].get("block_id")
        print(f"  Step1 OK: Image Block created → {block_id}")
        return block_id
    return None


def step2_upload_image(token, image_block_id, image_path):
    """Step 2: 上传图片素材，parent_node = Image BlockID，返回 file_token"""
    file_size = os.path.getsize(image_path)
    file_name = os.path.basename(image_path)
    mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
    boundary = "----PythonFormBoundary7MA4YWxkTrZu0gW"
    parts = []
    for name, value in [
        ("file_name", file_name),
        ("parent_type", "docx_image"),
        ("parent_node", image_block_id),
        ("size", str(file_size)),
    ]:
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}"
        )
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
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    if result.get("code") != 0:
        print(f"  Step2 FAILED: {result}")
        return None
    file_token = result["data"]["file_token"]
    print(f"  Step2 OK: Uploaded → {file_token}")
    return file_token


def step3_set_image(token, doc_token, image_block_id, file_token):
    """Step 3: PATCH Image Block 写入素材 token"""
    result = api_patch(token,
        f"/docx/v1/documents/{doc_token}/blocks/{image_block_id}",
        {"replace_image": {"token": file_token}}
    )
    if result.get("code") != 0:
        print(f"  Step3 FAILED: {result.get('code')} {result.get('msg')}")
        return False
    print(f"  Step3 OK: Image block updated")
    return True


def insert_image(token, doc_token, image_path, index):
    """完整三步插入图片，返回是否成功"""
    print(f"\n--- Inserting {os.path.basename(image_path)} at index {index} ---")
    block_id = step1_create_image_block(token, doc_token, index)
    if not block_id:
        return False
    file_token = step2_upload_image(token, block_id, image_path)
    if not file_token:
        return False
    return step3_set_image(token, doc_token, block_id, file_token)


# ── 列出文档 blocks ──────────────────────────────────────────────────────────

def list_blocks(token, doc_token):
    result = api_get(token, f"/docx/v1/documents/{doc_token}/blocks?page_size=100")
    blocks = result.get("data", {}).get("items", [])
    for i, b in enumerate(blocks):
        bt = b.get("block_type")
        bid = b.get("block_id")
        txt = ""
        for key in ["heading1", "heading2", "heading3", "text", "bullet", "ordered", "quote"]:
            if key in b:
                elems = b[key].get("elements", [])
                txt = "".join(e.get("text_run", {}).get("content", "") for e in elems)
                break
        if bt == 27:
            img_token = b.get("image", {}).get("token", "")
            txt = f"[IMAGE token={img_token or 'EMPTY'}]"
        print(f"  {i:3d}: [type={bt:2d}] {bid} | {txt[:60]}")
    return blocks


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]
    doc_token = sys.argv[2]

    account = os.environ.get("FEISHU_ACCOUNT", "main")
    load_credentials(account)
    token = get_token(account)
    print(f"Token obtained (account={account})")

    if action == "list":
        print(f"\nBlocks in document {doc_token}:")
        list_blocks(token, doc_token)

    elif action == "insert":
        if len(sys.argv) < 5:
            print("Usage: feishu_wiki_image.py insert <doc_token> <image_path> <index>")
            sys.exit(1)
        image_path = sys.argv[3]
        index = int(sys.argv[4])
        success = insert_image(token, doc_token, image_path, index)
        sys.exit(0 if success else 1)

    elif action == "batch":
        items = []
        for arg in sys.argv[3:]:
            path, idx = arg.rsplit(":", 1)
            items.append((path, int(idx)))
        items.sort(key=lambda x: x[1])
        offset = 0
        for image_path, index in items:
            success = insert_image(token, doc_token, image_path, index + offset)
            if success:
                offset += 1

    else:
        print(f"Unknown action: {action}")
        sys.exit(1)


if __name__ == "__main__":
    main()
