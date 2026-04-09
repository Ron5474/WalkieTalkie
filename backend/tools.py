from langchain.tools import tool
import chromadb
import os
import requests
from bs4 import BeautifulSoup
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from database import get_user_preferences, save_visited_place

db_path = os.path.join(os.path.dirname(__file__), "chroma_db")

@tool
def search_local_history(query: str) -> str:
    """Useful to search for local history, anecdotes, and context about a neighborhood or landmark."""
    try:
        client = chromadb.PersistentClient(path=db_path)
        collection = client.get_collection("local_stories")
        embeddings_model = OllamaEmbeddings(model="nomic-embed-text", base_url="http://localhost:11434")
        emb = embeddings_model.embed_query(query)
        results = collection.query(query_embeddings=[emb], n_results=2)
        
        snippets = []
        for doc in results['documents'][0]:
            snippets.append(doc)
        return "\n\n".join(snippets)
    except Exception as e:
        return "Not enough VectorDB context available yet. Rely on internal knowledge or Web search."

@tool
def fetch_user_profile(user_id: str) -> str:
    """Fetch the user's budget, dietary restrictions, and home country from the database."""
    prefs = get_user_preferences(user_id)
    if prefs:
        return f"User Profile -> Budget: ${prefs['budget']}/day, Diet: {prefs['dietary']}, Home Country: {prefs['country']}"
    return "No user profile found. Default to budget-conscious student."

@tool
def record_visited_place(user_id: str, place_name: str) -> str:
    """Save a place the user has visited to their Explorer Profile database."""
    return save_visited_place(user_id, place_name)

@tool
def search_web(query: str) -> str:
    """Useful to search the internet for live facts, unknown places, mural locations, or real-time context."""
    try:
        search = DuckDuckGoSearchRun()
        return search.run(query)
    except Exception as e:
        return f"Web search failed: {e}"

@tool
def scrape_static_history(city: str) -> str:
    """Scrapes one-time Static History about timeless hidden gems and major architectural monuments for a city."""
    try:
        wrapper = DuckDuckGoSearchAPIWrapper(max_results=3)
        results = wrapper.results(f"history timeless hidden gems architectural monuments {city}", num_results=3)
        
        combined_data = []
        for res in results:
            url = res.get('link')
            snippet = res.get('snippet', '')
            if url:
                try:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    resp = requests.get(url, headers=headers, timeout=4)
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    text = " ".join([p.get_text() for p in soup.find_all('p')])
                    content = text[:1500] if text else snippet
                except:
                    content = snippet
                combined_data.append(f"Source: {url}\nContent: {content}")
        
        return "\n\n".join(combined_data)
    except Exception as e:
        return f"Static Scraping failed: {e}"

@tool
def scrape_live_context(city: str, date_range: str) -> str:
    """Scrapes real-time web context specifically targeting weather forecasts, upcoming festivals, and local current events."""
    try:
        wrapper = DuckDuckGoSearchAPIWrapper(max_results=3)
        results = wrapper.results(f"local events festivals weather {city} {date_range}", num_results=3)
        
        combined_data = ["LIVE CONTEXT:"]
        for res in results:
            snippet = res.get('snippet', '')
            if snippet:
                combined_data.append(snippet)
                
        return "\n".join(combined_data)
    except Exception as e:
        return f"Live Scraping failed: {e}"
