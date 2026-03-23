#!/usr/bin/env python3
"""飞书 bitable 客户端。"""

import json
from pathlib import Path

import requests

OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
OPENCLAW_ENV = Path.home() / ".openclaw" / ".env"


def load_env_file(path: Path) -> dict:
    """解析 .env 文件，返回 key->value 字典。"""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def load_feishu_credentials() -> tuple[str, str]:
    """从 .env 或 openclaw.json 加载飞书凭证。"""
    env = load_env_file(OPENCLAW_ENV)
    app_id = env.get("FEISHU_MAIN_APP_ID")
    app_secret = env.get("FEISHU_MAIN_APP_SECRET")
    if app_id and app_secret:
        return app_id, app_secret

    with open(OPENCLAW_CONFIG, encoding="utf-8") as file:
        config = json.load(file)
    account = config["channels"]["feishu"]["accounts"]["main"]
    return account["appId"], account["appSecret"]


def get_tenant_token(app_id: str, app_secret: str) -> str:
    """获取飞书 tenant_access_token。"""
    response = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取飞书 token 失败: {data}")
    return data["tenant_access_token"]


def feishu_headers(token: str) -> dict:
    """生成飞书请求头。"""
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def list_bitable_records(token: str, app_token: str, table_id: str) -> list:
    """分页读取飞书 bitable 全量记录。"""
    records = []
    page_token = None
    while True:
        params = {"page_size": 100}
        if page_token:
            params["page_token"] = page_token
        response = requests.get(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            headers=feishu_headers(token),
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise RuntimeError(f"读取 bitable 失败: {data}")
        items = data.get("data", {}).get("items", [])
        records.extend(items)
        if not data["data"].get("has_more"):
            break
        page_token = data["data"]["page_token"]
    return records


def update_bitable_record(
    token: str,
    app_token: str,
    table_id: str,
    record_id: str,
    fields: dict,
    dry_run: bool = False,
) -> None:
    """更新 bitable 单条记录。"""
    if dry_run:
        print(f"  [DRY-RUN] 跳过 bitable 更新 {record_id}: {list(fields.keys())}")
        return

    response = requests.put(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
        headers=feishu_headers(token),
        json={"fields": fields},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 0:
        print(f"  ⚠️ bitable 更新失败 {record_id}: {data}")
    else:
        print(f"  ✅ bitable 已更新 {record_id}")
