from typing import Optional

from pydantic import BaseModel


class ItineraryRequest(BaseModel):
    city: str
    dates: Optional[str] = None
    days: Optional[int] = 1
    budget: Optional[str] = "Moderate"
    llm_tier: Optional[str] = "large"


class HolidayBriefingRequest(BaseModel):
    city: str
    start_date: Optional[str] = None  # YYYY-MM-DD
    days: int = 1


class WalkStoryRequest(BaseModel):
    city: str
    place_title: str
    anecdote: str
    llm_tier: Optional[str] = "small"
