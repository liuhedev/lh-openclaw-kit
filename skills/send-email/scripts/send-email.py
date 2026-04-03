#!/usr/bin/env python3
"""
通用邮件发送脚本
支持任意 SMTP 邮箱（企业微信、QQ、163、Gmail、Outlook 等）

用法:
  python3 send-email.py \
    --to "recipient1@company.com,recipient2@company.com" \
    --cc "cc@company.com" \
    --subject "邮件主题" \
    --body-file "./email-body.md" \
    [--attachment "./attachment.md"]

环境变量 (或 .env 文件):
  SMTP_HOST=smtp服务器地址（默认 smtp.exmail.qq.com）
  SMTP_PORT=端口号（默认 465）
  SMTP_USER=发件邮箱
  SMTP_PASS=密码或授权码
"""

import argparse
import mimetypes
import os
import smtplib
import ssl
import sys
from html import escape
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path


def load_env(env_path=None):
    """从 .env 文件加载环境变量（不覆盖已有）"""
    skill_root = Path(__file__).resolve().parent.parent
    paths = [
        env_path,
        os.path.expanduser('~/.config/dev-workflow/.env'),
        str(skill_root / '.env'),
    ]
    for p in paths:
        if p and os.path.isfile(p):
            with open(p) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        if line.startswith('export '):
                            line = line[len('export '):].strip()
                        key, _, value = line.partition('=')
                        key, value = key.strip(), value.strip()
                        if value and ((value[0] == value[-1]) and value[0] in ['"', "'"]):
                            value = value[1:-1]
                        if key and key not in os.environ:
                            os.environ[key] = value
            break


def md_to_html(md_content):
    """简易 Markdown 转 HTML（表格+标题+列表+行内语法）"""
    import re

    def inline_format(text):
        """处理行内 Markdown 语法：加粗、行内代码、链接"""
        text = escape(text)
        # 行内代码 `code`
        text = re.sub(r'`([^`]+)`', r'<code style="background:#f0f0f0;padding:1px 4px;border-radius:3px;font-size:13px;">\1</code>', text)
        # 加粗 **text**
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        # 链接 [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        return text

    lines = md_content.split('\n')
    html_lines = []
    in_table = False
    in_code = False
    in_ul = False
    in_ol = False

    def close_list_if_needed():
        nonlocal in_ul, in_ol
        if in_ul:
            html_lines.append('</ul>')
            in_ul = False
        if in_ol:
            html_lines.append('</ol>')
            in_ol = False

    for line in lines:
        stripped = line.strip()

        # 代码块
        if stripped.startswith('```'):
            close_list_if_needed()
            if in_table:
                html_lines.append('</table>')
                in_table = False
            if in_code:
                html_lines.append('</pre>')
                in_code = False
            else:
                html_lines.append('<pre style="background:#f5f5f5;padding:10px;border-radius:4px;font-size:13px;">')
                in_code = True
            continue

        if in_code:
            html_lines.append(escape(line))
            continue

        # 表格
        if '|' in line and stripped.startswith('|'):
            close_list_if_needed()
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            # 跳过分隔行
            if all(set(c) <= set('-: ') for c in cells):
                continue
            if not in_table:
                html_lines.append('<table style="border-collapse:collapse;width:100%;margin:8px 0;">')
                tag = 'th'
                in_table = True
            else:
                tag = 'td'
            style = 'border:1px solid #ddd;padding:6px 10px;text-align:left;'
            if tag == 'th':
                style += 'background:#f0f0f0;font-weight:bold;'
            row = ''.join(f'<{tag} style="{style}">{inline_format(c)}</{tag}>' for c in cells)
            html_lines.append(f'<tr>{row}</tr>')
            continue
        else:
            if in_table:
                html_lines.append('</table>')
                in_table = False

        # 标题
        if line.startswith('# '):
            close_list_if_needed()
            html_lines.append(f'<h2 style="color:#333;border-bottom:1px solid #eee;padding-bottom:6px;">{inline_format(line[2:])}</h2>')
        elif line.startswith('## '):
            close_list_if_needed()
            html_lines.append(f'<h3 style="color:#444;margin-top:16px;">{inline_format(line[3:])}</h3>')
        elif line.startswith('### '):
            close_list_if_needed()
            html_lines.append(f'<h4 style="color:#555;">{inline_format(line[4:])}</h4>')
        # 列表
        elif stripped.startswith('- '):
            if in_ol:
                html_lines.append('</ol>')
                in_ol = False
            if not in_ul:
                html_lines.append('<ul style="margin:6px 0 6px 18px;padding:0;">')
                in_ul = True
            html_lines.append(f'<li>{inline_format(stripped[2:])}</li>')
        elif stripped and stripped[0].isdigit() and '. ' in stripped:
            if in_ul:
                html_lines.append('</ul>')
                in_ul = False
            if not in_ol:
                html_lines.append('<ol style="margin:6px 0 6px 18px;padding:0;">')
                in_ol = True
            html_lines.append(f'<li>{inline_format(stripped.split(". ", 1)[1])}</li>')
        # 空行
        elif not stripped:
            close_list_if_needed()
            html_lines.append('<br>')
        else:
            close_list_if_needed()
            html_lines.append(f'<p style="margin:4px 0;">{inline_format(line)}</p>')

    if in_table:
        html_lines.append('</table>')
    close_list_if_needed()
    if in_code:
        html_lines.append('</pre>')

    body = '\n'.join(html_lines)
    return f'''<html><body style="font-family:Arial,sans-serif;font-size:14px;color:#333;line-height:1.6;max-width:800px;">
{body}
</body></html>'''


def send_email(to_addrs, cc_addrs, subject, body_md, attachments=None, signature_html=None):
    host = os.environ.get('SMTP_HOST', 'smtp.exmail.qq.com')
    port = int(os.environ.get('SMTP_PORT', '465'))
    user = os.environ.get('SMTP_USER')
    password = os.environ.get('SMTP_PASS')

    if not user or not password:
        print('错误: 缺少 SMTP_USER 或 SMTP_PASS 环境变量', file=sys.stderr)
        print('请在 ~/.config/dev-workflow/.env 或本 skill 目录 .env 中配置:', file=sys.stderr)
        print('  SMTP_USER=your@company.com', file=sys.stderr)
        print('  SMTP_PASS=your_auth_code', file=sys.stderr)
        sys.exit(1)

    msg = MIMEMultipart('alternative')
    msg['From'] = user
    msg['To'] = ', '.join(to_addrs)
    if cc_addrs:
        msg['Cc'] = ', '.join(cc_addrs)
    msg['Subject'] = subject

    # 纯文本版本
    msg.attach(MIMEText(body_md, 'plain', 'utf-8'))
    # HTML 版本（拼接签名）
    html_body = md_to_html(body_md)
    if signature_html:
        html_body = html_body.replace('</body>', f'<br><hr style="border:none;border-top:1px solid #eee;margin:20px 0;">\n{signature_html}\n</body>')
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    # 附件
    if attachments:
        # 切换为 mixed 类型以支持附件
        msg_with_attach = MIMEMultipart('mixed')
        msg_with_attach['From'] = msg['From']
        msg_with_attach['To'] = msg['To']
        if cc_addrs:
            msg_with_attach['Cc'] = msg['Cc']
        msg_with_attach['Subject'] = msg['Subject']
        msg_with_attach.attach(msg)

        for filepath in attachments:
            if not os.path.isfile(filepath):
                print(f'警告: 附件不存在，跳过: {filepath}', file=sys.stderr)
                continue

            # 强制 md 文件类型为 text/markdown
            if filepath.lower().endswith('.md'):
                maintype, subtype = 'text', 'markdown'
            else:
                mime_type, _ = mimetypes.guess_type(filepath)
                if mime_type:
                    maintype, subtype = mime_type.split('/', 1)
                else:
                    maintype, subtype = 'application', 'octet-stream'

            part = MIMEBase(maintype, subtype)
            with open(filepath, 'rb') as f:
                part.set_payload(f.read())
            encoders.encode_base64(part)
            filename = os.path.basename(filepath)

            # 修复中文附件名导致客户端无法识别扩展名的问题 (RFC 2231)
            part.add_header('Content-Disposition', 'attachment', filename=filename)
            msg_with_attach.attach(part)

        msg = msg_with_attach

    all_recipients = to_addrs + (cc_addrs or [])

    # 阶段一：建立连接（可重试，连接失败不会发送邮件）
    context = ssl.create_default_context()
    max_retries = 2
    server = None
    for attempt in range(max_retries + 1):
        try:
            server = smtplib.SMTP_SSL(host, port, context=context)
            server.login(user, password)
            break
        except smtplib.SMTPAuthenticationError:
            print('错误: SMTP 认证失败，请检查 SMTP_USER 和 SMTP_PASS', file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            if attempt < max_retries:
                import time
                print(f'[WARN] SMTP 连接失败（第 {attempt+1} 次），3s 后重试: {e}', file=sys.stderr)
                time.sleep(3)
            else:
                print(f'错误: SMTP 连接失败（已重试 {max_retries} 次）: {e}', file=sys.stderr)
                sys.exit(1)

    # 阶段二：发送邮件（不重试，避免重复发送）
    try:
        server.sendmail(user, all_recipients, msg.as_string())
        print(f'邮件发送成功 -> {", ".join(all_recipients)}')
    except Exception as e:
        print(f'错误: 邮件发送失败: {e}', file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            server.quit()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description='通用邮件发送')
    parser.add_argument('--to', required=True, help='收件人邮箱，逗号分隔')
    parser.add_argument('--cc', default='', help='抄送人邮箱，逗号分隔')
    parser.add_argument('--subject', required=True, help='邮件主题')
    parser.add_argument('--body-file', required=True, help='邮件正文 Markdown 文件路径')
    parser.add_argument('--attachment', action='append', default=[], help='附件路径（可多次指定）')
    parser.add_argument('--signature', default=None, help='签名 HTML 文件路径')
    parser.add_argument('--env-file', default=None, help='.env 文件路径')

    args = parser.parse_args()

    load_env(args.env_file)

    body_file = Path(args.body_file)
    if not body_file.is_file():
        print(f'错误: 正文文件不存在: {body_file}', file=sys.stderr)
        sys.exit(1)

    body_md = body_file.read_text(encoding='utf-8')
    to_addrs = [a.strip() for a in args.to.split(',') if a.strip()]
    cc_addrs = [a.strip() for a in args.cc.split(',') if a.strip()] if args.cc else []
    if not to_addrs:
        print('错误: 收件人不能为空（--to）', file=sys.stderr)
        sys.exit(1)

    # 加载签名并替换占位符
    signature_html = None
    if args.signature:
        sig_path = Path(args.signature)
        if sig_path.is_file():
            signature_html = sig_path.read_text(encoding='utf-8')
            # 从环境变量替换签名占位符
            sig_vars = {
                'name': os.environ.get('SIG_NAME', ''),
                'department': os.environ.get('SIG_DEPARTMENT', ''),
                'mobile': os.environ.get('SIG_MOBILE', ''),
                'email': os.environ.get('SIG_EMAIL', os.environ.get('SMTP_USER', '')),
                'address': os.environ.get('SIG_ADDRESS', ''),
            }
            for key, value in sig_vars.items():
                signature_html = signature_html.replace('{{ ' + key + ' }}', value)
                signature_html = signature_html.replace('{{' + key + '}}', value)
        else:
            print(f'警告: 签名文件不存在，跳过: {sig_path}', file=sys.stderr)

    send_email(to_addrs, cc_addrs, args.subject, body_md, args.attachment or None, signature_html)


if __name__ == '__main__':
    main()
