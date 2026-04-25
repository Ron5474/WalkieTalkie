from langchain.tools import tool
import chromadb
import os
import requests
from bs4 import BeautifulSoup
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_community.tools import DuckDuckGoSearchRun

import config
from database import get_user_preferences, save_visited_place
from llm_factory import get_embedding_model

db_path = os.path.join(os.path.dirname(__file__), "chroma_db")


@tool
def search_local_history(query: str) -> str:
    """Useful to search for local history, anecdotes, and context about a neighborhood or landmark (San Francisco & Kolkata curated stories)."""
    try:
        client = chromadb.PersistentClient(path=db_path)
        collection = client.get_collection("local_stories")
        embeddings_model = get_embedding_model()
        emb = embeddings_model.embed_query(query)
        results = collection.query(query_embeddings=[emb], n_results=2)

        snippets = []
        for doc in results["documents"][0]:
            snippets.append(doc)
        return "\n\n".join(snippets)
    except Exception as e:
        return f"Vector DB query failed ({e}). Rely on search_web or general knowledge with clear uncertainty."


@tool
def fetch_user_profile(user_id: str) -> str:
    """Fetch the user's budget, dietary restrictions, and home country from the database."""
    prefs = get_user_preferences(user_id)
    if prefs:
        return f"User Profile -> Budget: ${prefs['budget']}/day, Diet: {prefs['dietary']}, Home Country: {prefs['country']}"
    return "No user profile found. Default to budget-conscious student."


@tool
def record_visited_place(user_id: str, place_name: str, city: str = "") -> str:
    """Save a place the user has visited to their Explorer Profile database."""
    return save_visited_place(user_id, place_name, city=city or None)


@tool
def search_web(query: str) -> str:
    """Useful to search the internet for live facts, hours, weather, transit, tickets, visas, or unknown places."""
    try:
        search = DuckDuckGoSearchRun()
        return search.run(query)
    except Exception as e:
        return f"Web search failed: {e}"


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


@tool
def scrape_static_history(city: str) -> str:
    """Scrapes static history pages for itinerary synthesis (hero cities)."""
    try:
        wrapper = DuckDuckGoSearchAPIWrapper(max_results=3)
        results = wrapper.results(f"history timeless hidden gems architectural monuments {city}", max_results=3)

        combined_data = []
        for res in results:
            url = res.get("link")
            snippet = res.get("snippet", "")
            if url:
                try:
                    headers = {"User-Agent": "Mozilla/5.0"}
                    resp = requests.get(url, headers=headers, timeout=4)
                    soup = BeautifulSoup(resp.text, "html.parser")
                    text = " ".join([p.get_text() for p in soup.find_all("p")])
                    content = text[:1500] if text else snippet
                except Exception:
                    content = snippet
                combined_data.append(f"Source: {url}\nContent: {content}")

        return "\n\n".join(combined_data)
    except Exception as e:
        return f"Static scraping failed: {e}"


@tool
def scrape_live_context(city: str, date_range: str) -> str:
    """Scrapes real-time web context for weather, festivals, and events."""
    try:
        wrapper = DuckDuckGoSearchAPIWrapper(max_results=3)
        results = wrapper.results(f"local events festivals weather {city} {date_range}", max_results=3)

        combined_data = ["LIVE CONTEXT:"]
        for res in results:
            snippet = res.get("snippet", "")
            if snippet:
                combined_data.append(snippet)

        return "\n".join(combined_data)
    except Exception as e:
        return f"Live scraping failed: {e}"
