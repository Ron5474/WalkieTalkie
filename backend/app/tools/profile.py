"""User-profile tools backed by the SQLite store."""
from langchain.tools import tool

from app.db.database import get_user_preferences, save_visited_place


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
