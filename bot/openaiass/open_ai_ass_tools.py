# encoding:utf-8

from datetime import datetime

import requests


# OpenAI Assistant对话模型API (可用)
def get_current_time():
    # 获取当前服务器时间
    now = datetime.now()
    # 将时间格式化为指定格式
    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
    return formatted_time

def get_public_ip():
    response = requests.get('https://api.ipify.org?format=json')
    ip_data = response.json()
    return ip_data['ip']

def get_location(ip):
    response = requests.get(f'http://ip-api.com/json/{ip}?lang=zh-CN')
    location_data = response.json()
    if location_data['status'] == 'success':
        city = location_data['city']
        return city
    else:
        return None

def get_weather(city):
    api_key = 'YOUR_API_KEY'  # 请替换为您的实际API密钥
    url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&lang=zh_cn&units=metric'
    response = requests.get(url)
    weather_data = response.json()
    if weather_data['cod'] == 200:
        weather = weather_data['weather'][0]['description']
        temp = weather_data['main']['temp']
        print(f"{city}的当前天气是: {weather}, 温度是: {temp}°C")
    else:
        print("无法获取天气信息")

if __name__ == '__main__':
    ip = get_public_ip()
    print(f"您的公共IP地址是: {ip}")

    city = get_location(ip)
    if city:
        print(f"您的城市是: {city}")
        get_weather(city)
    else:
        print("无法获取位置信息")

