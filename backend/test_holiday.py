import asyncio
from main import holiday_briefing, HolidayBriefingRequest

async def run():
    req = HolidayBriefingRequest(
        city="San Francisco",
        start_date="May 10",
        days=3
    )
    result = await holiday_briefing(req)
    print("HOLIDAY BRIEFING RESULT:")
    for k, v in result.items():
        print(f"{k}: {str(v)[:200]}")

asyncio.run(run())
