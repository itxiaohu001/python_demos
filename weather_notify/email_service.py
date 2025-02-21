import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import smtplib
from typing import List, Optional
from loguru import logger

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.qq.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.sender_name = os.getenv('SENDER_NAME', '天气预报助手')
        self.default_recipients = os.getenv('DEFAULT_RECIPIENTS', '').split(',')
    
    def send_email(
        self,
        subject: str,
        content: str,
        recipients: Optional[List[str]] = None,
        content_type: str = 'html'
    ) -> bool:
        """发送邮件

        Args:
            subject: 邮件主题
            content: 邮件内容
            recipients: 收件人列表，如果为None则使用默认收件人
            content_type: 内容类型，'plain'或'html'

        Returns:
            bool: 发送是否成功
        """
        if not recipients:
            recipients = self.default_recipients

        if not recipients or not self.smtp_user or not self.smtp_password:
            logger.error("Missing required email configuration")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = formataddr((self.sender_name, self.smtp_user))
            msg['To'] = ','.join(recipients)
            msg['Subject'] = subject

            msg.attach(MIMEText(content, content_type, 'utf-8'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {len(recipients)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False