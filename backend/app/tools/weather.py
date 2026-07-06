"""Real-time weather tool (OpenWeatherMap)."""
import requests
from langchain.tools import tool

from app import config


@tool
def get_weather(city: str) -> str:
    """Fetch real-time weather for any city using OpenWeatherMap.
    Returns temperature (°F and °C), feels-like, humidity, wind speed, and a short condition description.
    Use this whenever the user asks about weather, rain, temperature, what to wear, or packing for climate.
    Input: city name (e.g. 'San Francisco', 'New York', 'Boston').
    """
    api_key = config.openweathermap_api_key()
    if not api_key:
        return (
            "Weather tool is unavailable (OPENWEATHERMAP_API_KEY not set). "
            "Please check https://openweathermap.org/current for conditions."
        )
    try:
        # Step 1: geocode city → lat/lon via /geo/1.0/direct
        geo_url = "https://api.openweathermap.org/geo/1.0/direct"
        geo_resp = requests.get(
            geo_url,
            params={"q": city, "limit": 1, "appid": api_key},
            timeout=8,
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        if not geo_data:
            return f"Could not geocode '{city}'. Try a different spelling."
        lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]
        resolved_name = geo_data[0].get("name", city)
        country = geo_data[0].get("country", "")

        # Step 2: current weather via /data/2.5/weather (units=imperial for °F)
        wx_url = "https://api.openweathermap.org/data/2.5/weather"
        wx_resp = requests.get(
            wx_url,
            params={"lat": lat, "lon": lon, "units": "imperial", "appid": api_key},
            timeout=8,
        )
        wx_resp.raise_for_status()
        d = wx_resp.json()

        temp_f = d["main"]["temp"]
        temp_c = round((temp_f - 32) * 5 / 9, 1)
        feels_f = d["main"]["feels_like"]
        feels_c = round((feels_f - 32) * 5 / 9, 1)
        humidity = d["main"]["humidity"]
        wind_mph = d["wind"]["speed"]
        wind_kph = round(wind_mph * 1.609, 1)
        desc = d["weather"][0]["description"].capitalize()
        visibility_m = d.get("visibility", None)
        visibility_str = f", visibility {round(visibility_m / 1000, 1)} km" if visibility_m else ""

        return (
            f"Current weather in {resolved_name}, {country}: {desc}. "
            f"Temp {temp_f:.1f}°F ({temp_c}°C), feels like {feels_f:.1f}°F ({feels_c}°C). "
            f"Humidity {humidity}%, wind {wind_mph:.1f} mph ({wind_kph} km/h){visibility_str}."
        )
    except requests.HTTPError as e:
        return f"OpenWeatherMap API error ({e.response.status_code}): {e}"
    except Exception as e:
        return f"Weather lookup failed: {e}"
