#!/usr/bin/env python3
"""
Run evaluation queries against both API model tiers (small vs large).

Usage (from repo root):
  cd backend && source venv/bin/activate
  export OPENROUTER_API_KEY=...
  python ../evaluation/run_eval.py

Writes JSONL to evaluation/results/ with latency per query.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

os.chdir(BACKEND)

from langchain_core.messages import HumanMessage  # noqa: E402

from agent_runner import run_chat_turn  # noqa: E402

CITY_GPS = {
    "San Francisco": (37.7955, -122.3937),
    "Kolkata": (22.5726, 88.3639),
}


def load_queries(path: Path) -> tuple[dict, list[dict]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    meta = raw.get("meta", {})
    return meta, raw.get("queries", [])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", default=str(ROOT / "evaluation" / "queries.yaml"))
    parser.add_argument("--injection", action="store_true", help="Run injection_tests.json instead")
    parser.add_argument("--tier", choices=("small", "large", "both"), default="both")
    args = parser.parse_args()

    if args.injection:
        inj_path = ROOT / "evaluation" / "injection_tests.json"
        items = json.loads(inj_path.read_text(encoding="utf-8"))
        meta = {"user_id": "student_1", "default_city": "San Francisco"}
        queries = [{"id": x["id"], "text": x["text"], "city": meta["default_city"]} for x in items]
    else:
        meta, queries = load_queries(Path(args.queries))

    out_dir = ROOT / "evaluation" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_file = out_dir / f"eval_{ts}.jsonl"

    tiers = ["small", "large"] if args.tier == "both" else [args.tier]

    for tier in tiers:
        for q in queries:
            uid = meta.get("user_id", "student_1")
            city = q.get("city") or meta.get("default_city", "San Francisco")
            lat = q.get("latitude")
            lng = q.get("longitude")
            if lat is None or lng is None:
                lat, lng = CITY_GPS.get(city, (37.7955, -122.3937))
            text = q["text"]
            human = HumanMessage(
                content=(
                    f"Backend context: user_id={uid}; GPS=Lat: {lat}, Long: {lng}; focus_city={city}.\n\n"
                    f"{text}"
                )
            )
            try:
                answer, elapsed = run_chat_turn([human], tier=tier, user_id=uid, city=city, latitude=lat, longitude=lng)
            except Exception as e:
                answer, elapsed = repr(e), -1.0

            row = {
                "query_id": q.get("id"),
                "tier": tier,
                "elapsed_sec": elapsed,
                "answer_preview": (answer or "")[:400],
            }
            print(json.dumps(row))
            with open(out_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")

    print(f"\nWrote {out_file}")


if __name__ == "__main__":
    main()
