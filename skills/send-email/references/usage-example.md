# 使用示例

## 基础用法

发送一封简单的邮件：

```bash
python3 scripts/send-email.py \
  --to "recipient@company.com" \
  --subject "测试邮件" \
  --body-file "./test-email.md"
```

## 完整用法

发送带抄送、多个附件和签名的邮件：

```bash
python3 scripts/send-email.py \
  --to "recipient1@company.com,recipient2@company.com" \
  --cc "cc1@company.com,cc2@company.com" \
  --subject "【通知】邮件主题" \
  --body-file "./email-body.md" \
  --attachment "./attachment1.md" \
  --attachment "./attachment2.md" \
  --attachment "./attachment3.md" \
  --signature "./references/email-signature-template.html"
```

## 测试邮件内容 (test-email.md)

```markdown
# 测试邮件

这是一封测试邮件。

## 功能列表

- 支持 Markdown 格式
- 支持表格
- 支持列表
- 支持附件

## 示例表格

| 功能 | 状态 | 备注 |
|------|------|------|
| Markdown 转 HTML | ✅ | 支持表格、标题、列表 |
| 多附件 | ✅ | 可多次指定 --attachment |
| 签名 | ✅ | HTML 格式 |

## 示例列表

1. 第一项
2. 第二项
3. 第三项

- 无序列表项 1
- 无序列表项 2
- 无序列表项 3

**加粗文本** 和 `行内代码` 也支持。
```
