from fastapi import APIRouter

from app.schemas.itinerary import HolidayBriefingRequest, ItineraryRequest, WalkStoryRequest
from app.services.itinerary_service import (
    generate_holiday_briefing,
    generate_walk_story,
    synthesize_itinerary,
)

router = APIRouter()


@router.post("/api/synthesize-itinerary")
async def synthesize_itinerary_endpoint(req: ItineraryRequest):
    return await synthesize_itinerary(req)


@router.post("/api/holiday-briefing")
async def holiday_briefing_endpoint(req: HolidayBriefingRequest):
    return await generate_holiday_briefing(req)


@router.post("/api/walk-story")
async def walk_story_endpoint(req: WalkStoryRequest):
    return await generate_walk_story(req)
