#!/usr/bin/env python3
"""
Generate evaluation/queries.yaml from one reusable 20-query template.

Usage:
  python evaluation/generate_queries.py
  python evaluation/generate_queries.py --cities "San Francisco,Kolkata,Boston"
  python evaluation/generate_queries.py --user-id student_1 --default-city "San Francisco"
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "evaluation" / "queries.yaml"

TEMPLATE_20 = [
    "What are 5 cheap lunch spots near a historic district where locals actually eat?",
    "I’m in this city and have $25 for the day—suggest 3 activities and 2 meals.",
    "Which neighborhoods are best for seeing community-driven street art?",
    "I want a free Instagram spot that is culturally significant but not a tourist trap.",
    "What is a snack from a local eatery in a cultural neighborhood that has been there for over 20 years?",
    "Tell me about a cultural intersection in this city where two different communities met.",
    "Plan a walking route from Point A to Point B with 2 stops that explain city history.",
    "I'm standing in front of a landmark/mural—what is its significance to local people living here today?",
    "How has one old neighborhood changed in the last 50 years, and where can I still see the old version?",
    "Give me a 1-day plan under $30 that includes history, local food, and a sunset.",
    "I land at the airport and need to get to city center—what’s the cheapest public transit vs rideshare cost?",
    "I have $90 for 3 days including stay—break down a feasible plan.",
    "Compare staying in a hostel vs an Airbnb in a central neighborhood for a student traveler.",
    "Is a major attraction sold out this weekend, or is there a local alternative nearby?",
    "I’m vegan and want food under $12 near city center.",
    "Image upload: What is this building/statue and why should a student traveler care?",
    "Image upload: I’m looking at this menu—which item is the most authentic local specialty?",
    "What’s the weather tomorrow—should I plan indoor museums or outdoor walking?",
    "Is a major park/monument open today and is there any pay-what-you-wish day?",
    "Find me the fastest transit route from my current location to a destination using only local buses/trains.",
]


def city_prefix(city: str) -> str:
    return "".join(ch for ch in city.lower() if ch.isalnum())[:3] or "cty"


def build_queries(cities: list[str]) -> list[dict]:
    out: list[dict] = []
    for city in cities:
        prefix = city_prefix(city)
        for idx, text in enumerate(TEMPLATE_20, start=1):
            out.append(
                {
                    "id": f"{prefix}{idx:02d}",
                    "text": text,
                    "city": city,
                }
            )
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cities",
        default="San Francisco,Kolkata",
        help="Comma-separated list of cities to instantiate the 20-query template for.",
    )
    parser.add_argument("--user-id", default="student_1")
    parser.add_argument("--default-city", default="San Francisco")
    args = parser.parse_args()

    cities = [c.strip() for c in args.cities.split(",") if c.strip()]
    if not cities:
        raise SystemExit("No valid cities provided.")

    payload = {
        "meta": {
            "user_id": args.user_id,
            "default_city": args.default_city,
        },
        "queries": build_queries(cities),
    }

    header = (
        "# Cross-city evaluation set generated from one 20-query template.\n"
        f"# Cities: {', '.join(cities)}\n"
        f"# Total queries: {len(payload['queries'])}\n\n"
    )
    OUT_PATH.write_text(header + yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(payload['queries'])} queries)")


if __name__ == "__main__":
    main()

