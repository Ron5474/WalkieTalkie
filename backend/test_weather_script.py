import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools import get_weather
import config

print("API Key loaded by config:", repr(config.openweathermap_api_key()))
print("Result:", get_weather.invoke({"city": "San Francisco"}))
