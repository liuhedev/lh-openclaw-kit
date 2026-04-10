---
name: feishu-bitable
description: >
  Interact with Feishu (飞书) Bitable (多维表格) via direct API calls. Use this skill
  whenever the user wants to read records from a Feishu Bitable, update Bitable records,
  sync data to a Bitable, or perform any operations on Feishu multidimensional tables.
  Triggers include: "查多维表", "更新多维表", "bitable", "飞书表格", "同步到多维表",
  "读取 bitable 数据", "更新 bitable 记录", or any task involving querying or modifying
  Feishu Bitable records programmatically.
allowed-tools:
  - Bash
---

# feishu-bitable

飞书多维表格 (Bitable) 数据操作客户端。提供读取和更新多维表记录的基础能力。

## 核心功能

| 功能 | 说明 |
|------|------|
| `list_bitable_records` | 分页读取多维表全量记录 |
| `update_bitable_record` | 更新单条记录（支持 dry-run 模式） |

## 脚本路径

入口文件位于 `scripts/feishu_bitable_client.py`。这是一个库模块，没有独立 CLI；在 **`skills/feishu-bitable/`** 目录下由其他 Python 脚本导入使用。

## 凭证加载

与 `feishu-send`、`feishu-doc` 一致，优先级：

1. 进程已有环境变量（`FEISHU_MAIN_APP_ID` / `FEISHU_MAIN_APP_SECRET`）
2. `~/.config/dev-workflow/.env`
3. `~/.openclaw/.env`
4. `~/.openclaw/openclaw.json`（`channels.feishu.accounts.<账号名>`）

默认账号为 `main`。也可以调用 `load_feishu_credentials("其他账号名")` 读取其他账号。

## 使用方法

此脚本为**库文件**，需在其他 Python 脚本中导入使用：

```python
from scripts.feishu_bitable_client import (
    load_feishu_credentials,
    get_tenant_token,
    list_bitable_records,
    update_bitable_record,
)

# 加载凭证
app_id, app_secret = load_feishu_credentials()
token = get_tenant_token(app_id, app_secret)

# 读取记录
records = list_bitable_records(token, app_token="YOUR_APP_TOKEN", table_id="YOUR_TABLE_ID")

# 更新记录
update_bitable_record(
    token=token,
    app_token="YOUR_APP_TOKEN",
    table_id="YOUR_TABLE_ID",
    record_id="recXXXXXX",
    fields={"状态": "已完成"},
    dry_run=False,  # 设为 True 可预览变更而不实际执行
)
```

## API 函数说明

### `load_feishu_credentials(account_name: str = "main") -> tuple[str, str]`

从环境变量或 openclaw.json 加载飞书应用凭证。

**返回：** `(app_id, app_secret)`

### `get_tenant_token_for_account(account_name: str = "main") -> str`

按账号名直接获取 tenant_access_token。

### `get_tenant_token(app_id: str, app_secret: str) -> str`

获取飞书 tenant_access_token。

### `list_bitable_records(token: str, app_token: str, table_id: str) -> list`

分页读取多维表全量记录，自动处理分页。

**参数：**
- `token`: tenant_access_token
- `app_token`: 多维表应用 token（从飞书多维表 URL 中获取）
- `table_id`: 表格 ID（默认为 `tbltI5f5RxG0jJ7c`，可从 URL 获取）

**返回：** 记录列表，每项包含 `record_id` 和 `fields`

### `update_bitable_record(token, app_token, table_id, record_id, fields, dry_run=False)`

更新单条记录。

**参数：**
- `token`: tenant_access_token
- `app_token`: 多维表应用 token
- `table_id`: 表格 ID
- `record_id`: 记录 ID
- `fields`: 要更新的字段字典
- `dry_run`: 为 True 时仅打印预览，不实际更新

## 获取 app_token 和 table_id

1. 在飞书多维表中，点击右上角「...」→「复制链接」
2. 链接格式：`https://example.feishu.cn/base/<app_token>?table=<table_id>`
3. 提取 `app_token` 和 `table_id`

## 依赖

- Python 3.10+
- `requests`（`pip install requests`）

## 注意事项

- 读取记录时自动分页，可处理大数据量
- 更新操作默认直接执行，建议先用 `dry_run=True` 验证
- 失败时会打印错误信息但不会中断程序
