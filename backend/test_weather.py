import requests
import sys
import os

API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "")
city = "San Francisco"

print(f"Testing Geocoding API for {city}...")
geo_url = "https://api.openweathermap.org/geo/1.0/direct"
try:
    if not API_KEY:
        raise ValueError("Set OPENWEATHERMAP_API_KEY before running this test script.")
    resp = requests.get(geo_url, params={"q": city, "limit": 1, "appid": API_KEY}, timeout=5)
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
