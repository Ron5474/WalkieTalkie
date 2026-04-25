import asyncio
from main import synthesize_itinerary, ItineraryRequest

async def run():
    req = ItineraryRequest(
        city="San Francisco",
        dates="May 10 to May 12, 2026",
        days=3,
        budget="budget-friendly"
    )
    result = await synthesize_itinerary(req)
    print("KEYS:", result.keys())
    print("PLACES COUNT:", len(result.get("places", [])))
    print("EATS COUNT:", len(result.get("eats", [])))
    print("ITINERARY:", result.get("itinerary", []))

asyncio.run(run())
