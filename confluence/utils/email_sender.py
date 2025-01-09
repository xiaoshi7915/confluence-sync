import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
from datetime import datetime
from confluence.config import EMAIL_CONFIG
import logging

def send_update_email(subject, content, attachments=None):
    """发送更新邮件"""
    logger = logging.getLogger('email_sender')
    try:
        logger.info(f"准备发送邮件: {subject}")
        logger.info(f"收件人: {EMAIL_CONFIG['recipients']}")
        
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = EMAIL_CONFIG['sender']
        msg['To'] = ', '.join(EMAIL_CONFIG['recipients'])
        
        # 添加邮件正文
        msg.attach(MIMEText(content, 'html'))
        logger.info("已添加邮件正文")
        
        # 添加附件
        if attachments:
            for file_path in attachments:
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        part = MIMEApplication(f.read())
                        part.add_header('Content-Disposition', 'attachment', 
                                      filename=os.path.basename(file_path))
                        msg.attach(part)
                    logger.info(f"已添加附件: {file_path}")
                else:
                    logger.warning(f"附件不存在: {file_path}")
        
        # 发送邮件
        logger.info(f"连接SMTP服务器: {EMAIL_CONFIG['smtp_server']}:{EMAIL_CONFIG['smtp_port']}")
        with smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.login(EMAIL_CONFIG['username'], EMAIL_CONFIG['password'])
            logger.info("SMTP登录成功")
            server.send_message(msg)
            logger.info("邮件发送成功")
            
        return True
    except Exception as e:
        logger.error(f"发送邮件失败: {str(e)}")
        return False

def format_update_content(updates):
    """格式化更新内容为HTML"""
    logger = logging.getLogger('email_sender')
    logger.info(f"格式化 {len(updates) if updates else 0} 条更新内容")
    
    if not updates:
        logger.info("没有需要发送的更新内容")
        return None
        
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
    logger.info("更新内容格式化完成")
    return html

def send_hourly_update(updates):
    """发送每小时更新邮件"""
    logger = logging.getLogger('email_sender')
    if not updates:
        logger.info("没有每小时更新内容，跳过发送")
        return
        
    subject = f"Confluence文档更新通知 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    content = format_update_content(updates)
    if content:
        send_update_email(subject, content)
    else:
        logger.info("没有格式化后的内容，跳过发送")

def send_daily_summary(updates):
    """发送每日汇总邮件"""
    logger = logging.getLogger('email_sender')
    if not updates:
        logger.info("没有每日更新内容，跳过发送")
        return
        
    subject = f"Confluence文档每日更新汇总 - {datetime.now().strftime('%Y-%m-%d')}"
    content = format_update_content(updates)
    if content:
        send_update_email(subject, content)
    else:
        logger.info("没有格式化后的内容，跳过发送") 