"""Web-scraping tools used for itinerary synthesis context."""
import requests
from bs4 import BeautifulSoup
from langchain.tools import tool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper


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
