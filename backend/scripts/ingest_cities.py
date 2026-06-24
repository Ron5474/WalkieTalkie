#!/usr/bin/env python3
"""Populate the Chroma vector DB with curated + discovered city knowledge.

Run from backend/ (with venv active):
  python scripts/ingest_cities.py
"""
import sys
from pathlib import Path

# scripts/ -> backend/ so `import app...` resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config
from app.ingestion.ingest import ingest_city


def main():
    config.assert_api_config()
    for city in ("San Francisco", "Kolkata"):
        print(f"Ingesting city: {city}")
        print(ingest_city(city))


if __name__ == "__main__":
    main()
