import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
from datetime import datetime
from confluence.config import EMAIL_CONFIG

def send_update_email(subject, content, attachments=None):
    """发送更新邮件"""
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = EMAIL_CONFIG['sender']
        msg['To'] = ', '.join(EMAIL_CONFIG['recipients'])
        
        # 添加邮件正文
        msg.attach(MIMEText(content, 'html'))
        
        # 添加附件
        if attachments:
            for file_path in attachments:
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        part = MIMEApplication(f.read())
                        part.add_header('Content-Disposition', 'attachment', 
                                      filename=os.path.basename(file_path))
                        msg.attach(part)
        
        # 发送邮件
        with smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.login(EMAIL_CONFIG['username'], EMAIL_CONFIG['password'])
            server.send_message(msg)
            
        return True
    except Exception as e:
        print(f"发送邮件失败: {str(e)}")
        return False

def format_update_content(updates):
    """格式化更新内容为HTML"""
    html = """
    <html>
    <head>
        <style>
            table {{border-collapse: collapse; width: 100%;}}
            th, td {{border: 1px solid #ddd; padding: 8px; text-align: left;}}
            th {{background-color: #f2f2f2;}}
            tr:nth-child(even) {{background-color: #f9f9f9;}}
        </style>
    </head>
    <body>
        <h2>Confluence文档更新通知</h2>
        <p>更新时间：{}</p>
        <table>
            <tr>
                <th>标题</th>
                <th>作者</th>
                <th>部门</th>
                <th>链接</th>
                <th>更新时间</th>
            </tr>
    """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    for update in updates:
        html += """
            <tr>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td><a href="{}">查看</a></td>
                <td>{}</td>
            </tr>
        """.format(
            update['title'],
            update['author'],
            update['department'],
            update['url'],
            update['last_modified']
        )
    
    html += """
        </table>
    </body>
    </html>
    """
    return html

def send_hourly_update(updates):
    """发送每小时更新邮件"""
    if not updates:
        return
        
    subject = f"Confluence文档更新通知 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    content = format_update_content(updates)
    send_update_email(subject, content)

def send_daily_summary(updates):
    """发送每日汇总邮件"""
    if not updates:
        return
        
    subject = f"Confluence文档每日更新汇总 - {datetime.now().strftime('%Y-%m-%d')}"
    content = format_update_content(updates)
    send_update_email(subject, content) 