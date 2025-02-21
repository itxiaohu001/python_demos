import os
import requests
from typing import Dict, Any
from loguru import logger
from datetime import datetime

class WeatherService:
    def __init__(self):
        self.api_key = os.getenv('QWEATHER_API_KEY')
        self.base_url = os.getenv('QWEATHER_API_URL', 'https://devapi.qweather.com')
        self.location = os.getenv('QWEATHER_LOCATION', '101250101')
    
    def get_weather_data(self) -> Dict[str, Any]:
        """获取天气数据"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Accept-Encoding': 'gzip'
            }
            # 获取实时天气
            now_response = requests.get(
                f"{self.base_url}/weather/now",
                params={'location': self.location},
                headers=headers
            )
            now_response.raise_for_status()
            now_data = now_response.json()

            # 获取天气预报
            forecast_response = requests.get(
                f"{self.base_url}/weather/3d",
                params={'location': self.location},
                headers=headers
            )
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()

            return {
                'now': now_data.get('now', {}),
                'forecast': forecast_data.get('daily', [{}])[0] if forecast_data.get('daily') else {}
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch weather data: {e}")
            return {}
    
    def format_weather_data(self, data: Dict[str, Any]) -> str:
        """格式化天气数据"""
        if not data:
            return "无法获取天气数据"
        
        try:
            now = data['now']
            update_time = datetime.strptime(now['obsTime'], '%Y-%m-%dT%H:%M%z').strftime('%Y-%m-%d %H:%M')
            
            return f"""今日天气预报：
更新时间：{update_time}
地点：{self.location}
当前温度：{now['temp']}°C
体感温度：{now['feelsLike']}°C
天气状况：{now['text']}
湿度：{now['humidity']}%
风向：{now['windDir']}
风力等级：{now['windScale']}级"""
        except KeyError as e:
            logger.error(f"Failed to format weather data: {e}")
            return "天气数据格式错误"

    def get_formatted_weather(self) -> str:
        """获取格式化的天气信息"""
        data = self.get_weather_data()
        return self.format_weather_data(data)