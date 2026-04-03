---
name: send-email
version: 1.0.0
description: 当用户需要发送邮件、发送通知邮件、发送带附件的邮件、发送正式邮件、发送工作报告时，必须立刻触发本 skill。支持任意 SMTP 邮箱（企业微信、QQ、163、Gmail、Outlook 等），Markdown 正文自动转 HTML，多附件、抄送、签名功能。
---

# 发送邮件 Skill

通过 SMTP 发送邮件，支持任意邮箱服务商。Markdown 正文自动转 HTML，支持多附件、抄送、签名。

## 必需输入

| 输入项 | 说明 |
|------|------|
| 收件人邮箱 | --to 参数，逗号分隔多个 |
| 邮件主题 | --subject 参数 |
| 正文内容 | --body-file（Markdown 文件路径） |

可选输入：
- 抄送邮箱（--cc）
- 附件（--attachment，可多次指定）
- 签名文件（--signature，HTML 格式）
- .env 文件路径（--env-file）

## 使用方式

确认收件人、主题、正文后，执行脚本发送：

```bash
python3 scripts/send-email.py \
  --to "recipient1@company.com,recipient2@company.com" \
  --cc "cc@company.com" \
  --subject "邮件主题" \
  --body-file "./email-body.md" \
  --attachment "./attachment1.md" \
  --attachment "./attachment2.md"
```

需要签名时加 `--signature references/email-signature-template.html`。

## SMTP 配置

通过环境变量或 `.env` 文件配置：

```
SMTP_HOST=smtp服务器地址
SMTP_PORT=端口号
SMTP_USER=发件邮箱
SMTP_PASS=密码或授权码
```

常见邮箱服务商配置：

| 邮箱 | SMTP_HOST | SMTP_PORT |
|------|-----------|-----------|
| 企业微信 | smtp.exmail.qq.com | 465 |
| QQ 邮箱 | smtp.qq.com | 465 |
| 163 邮箱 | smtp.163.com | 465 |
| Gmail | smtp.gmail.com | 465 |
| Outlook | smtp.office365.com | 587 |

未配置时默认使用企业微信（smtp.exmail.qq.com:465）。

各邮箱服务商的 SMTP 开通和授权码获取步骤见 `references/smtp-setup-guide.md`。

.env 文件加载优先级（从高到低）：
1. --env-file 指定的路径
2. ~/.config/dev-workflow/.env
3. 本 skill 目录下的 .env

## 签名模板

`references/email-signature-template.html` 支持以下占位符，从 `.env` 中读取：

| 占位符 | .env 变量 | 说明 |
|--------|-----------|------|
| `{{ name }}` | SIG_NAME | 姓名 |
| `{{ department }}` | SIG_DEPARTMENT | 部门 |
| `{{ mobile }}` | SIG_MOBILE | 手机号 |
| `{{ email }}` | SIG_EMAIL | 邮箱（默认取 SMTP_USER） |
| `{{ address }}` | SIG_ADDRESS | 公司地址 |

不需要签名时省略 `--signature` 参数即可。

## 功能特性

1. **Markdown 自动转 HTML**：支持表格、标题、列表、加粗、行内代码、链接
2. **多附件支持**：可多次指定 --attachment
3. **中文附件名兼容**：使用 RFC 2231 标准编码
4. **签名拼接**：自动在 HTML 正文末尾拼接签名
5. **重试机制**：SMTP 连接失败自动重试 2 次，避免重复发送
6. **纯文本 + HTML 双版本**：邮件客户端可选择显示格式

## 依赖

| 依赖 | 用途 |
|------|------|
| Python 3 | 脚本运行环境 |
| smtplib/ssl | Python 标准库，无需额外安装 |

## 失败处理

| 异常 | 处理方式 |
|------|---------|
| 缺少 SMTP 配置 | 提示用户在 .env 中配置 |
| SMTP 认证失败 | 提示检查 SMTP_USER 和 SMTP_PASS |
| 附件不存在 | 警告并跳过该附件，继续发送 |
| 邮件发送失败 | 输出错误信息，不重试（避免重复发送） |
