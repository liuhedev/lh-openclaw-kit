# SMTP 配置指南

## 腾讯企业邮箱

### 获取客户端专用密码

1. 登录企业邮箱 → 设置 → 客户端设置 → 开启 IMAP/SMTP 服务，勾选"保存已发送邮件到服务器"
2. 设置 → 微信绑定 → 安全登录 → 开启安全登录
3. 安全登录页面 → 客户端专用密码 → 生成新密码 → 复制保存（只显示一次）

### .env 配置

```
SMTP_HOST=smtp.exmail.qq.com
SMTP_PORT=465
SMTP_USER=yourname@company.com
SMTP_PASS=客户端专用密码
```

## QQ 邮箱

1. 登录 QQ 邮箱 → 设置 → 账户 → POP3/IMAP/SMTP 服务 → 开启 SMTP
2. 按提示生成授权码

```
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=yourqq@qq.com
SMTP_PASS=授权码
```

## 163 邮箱

1. 登录 163 邮箱 → 设置 → POP3/SMTP/IMAP → 开启 SMTP
2. 按提示设置授权码

```
SMTP_HOST=smtp.163.com
SMTP_PORT=465
SMTP_USER=yourname@163.com
SMTP_PASS=授权码
```

## Gmail

1. 开启两步验证：Google 账户 → 安全性 → 两步验证
2. 生成应用专用密码：Google 账户 → 安全性 → 应用专用密码

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=yourname@gmail.com
SMTP_PASS=应用专用密码
```

## Outlook / Office 365

```
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=yourname@outlook.com
SMTP_PASS=账户密码
```

注意：Outlook 使用 587 端口（STARTTLS），当前脚本默认用 SSL（465），使用 Outlook 需确认兼容性。
