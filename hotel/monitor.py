import requests
from bs4 import BeautifulSoup
import time
import sys
import os

# 添加项目根目录到Python路径以导入notice模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from notice.tts import speak_text

class HotelMonitor:
    def __init__(self, base_url, check_interval=30, cookies=None, params=None):
        self.base_url = base_url
        self.check_interval = check_interval
        self.params = params or {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        default_cookies = {
        }
        self.cookies = {**default_cookies, **(cookies or {})}
    
    def build_url(self):
        """构建完整的URL，包含所有查询参数"""
        url = self.base_url
        if self.params:
            query_params = '&'.join([f'{k}={v}' for k, v in self.params.items()])
            url = f'{url}?{query_params}' if '?' not in url else f'{url}&{query_params}'
        return url

    def get_hotel_prices(self):
        """获取网页中的酒店房型价格信息"""
        try:
            url = self.build_url()
            response = requests.get(url, headers=self.headers, cookies=self.cookies)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检查是否存在无房提示
            no_room_element = soup.select_one('div.ant-result-title.hotel-price__result-title')
            if no_room_element and '抱歉！您所查询的酒店暂没有合适报价或已满房。' in no_room_element.text:
                return []
            
            # 如果没有找到无房提示，说明有房
            return [{'name': '有房可订', 'price': '请立即预订'}]
        
        except requests.RequestException as e:
            print(f"获取网页数据时出错: {e}")
            return []
    
    def notify(self, hotels):
        """当发现多个酒店时触发通知"""
        message = f"发现{len(hotels)}个酒店房型:\n"
        for hotel in hotels:
            message += f"- {hotel['name']}: {hotel['price']}\n"
        
        # 使用TTS播放通知
        speak_text(message)
        print(message)
    
    def start_monitoring(self):
        """开始监控流程"""
        print(f"开始监控酒店房型，检查间隔: {self.check_interval}秒")
        
        while True:
            hotels = self.get_hotel_prices()
            
            if hotels:
                print("\n检测到酒店有房！")
                self.notify(hotels)
            else:
                print(f"\n当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                print("酒店暂无房间")
            
            time.sleep(self.check_interval)

def main():
    if len(sys.argv) < 2:
        print("使用方法: python monitor.py <酒店页面URL> [参数1=值1 参数2=值2 ...]")
        print("示例: python monitor.py https://example.com/hotel checkOutDate=2025-05-04 roomCount=1")
        return
    
    base_url = sys.argv[1]
    params = {}
    cookies = {}
    
    # 解析命令行参数
    for arg in sys.argv[2:]:
        if '=' in arg:
            key, value = arg.split('=', 1)
            # 特殊处理occupancy相关参数
            if key.startswith('occupancy.'):
                params[key] = value
            else:
                params[key] = value
    
    monitor = HotelMonitor(base_url, cookies=cookies, params=params)
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\n监控已停止")

if __name__ == "__main__":
    main()