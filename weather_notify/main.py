import os
from dotenv import load_dotenv
from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
import pytz
from weather_service import WeatherService
from email_service import EmailService

class WeatherNotifier:
    def __init__(self):
        self.scheduler = BlockingScheduler()
        self.timezone = pytz.timezone('Asia/Shanghai')
        self.weather_service = WeatherService()
        self.email_service = EmailService()
    
    def start(self):
        """启动定时任务"""
        try:
            # 默认每天早上7点发送天气预报
            self.scheduler.add_job(
                self.send_weather_notification,
                'cron',
                hour=7,
                minute=0,
                timezone=self.timezone
            )
            logger.info("Weather notification scheduler started")
            self.scheduler.start()
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
    
    def send_weather_notification(self):
        """发送天气通知"""
        try:
            # 获取天气数据
            weather_info = self.weather_service.get_formatted_weather()
            
            # 发送邮件通知
            subject = f"天气预报 - {datetime.now(self.timezone).strftime('%Y-%m-%d')}"
            sent = self.email_service.send_email(
                subject=subject,
                content=weather_info,
                content_type='plain'
            )
            
            if sent:
                logger.info("Weather notification sent successfully")
            else:
                logger.error("Failed to send weather notification email")
        except Exception as e:
            logger.error(f"Failed to send weather notification: {e}")

def main():
    notifier = WeatherNotifier()
    notifier.start()

if __name__ == "__main__":
    main()
