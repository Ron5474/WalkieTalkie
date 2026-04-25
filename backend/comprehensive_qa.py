import asyncio
import os
import sys
import yaml
from langchain_core.messages import HumanMessage
from agent_runner import run_chat_turn

# Selected Query IDs for testing
TEST_QUERY_IDS = ["san01", "san10", "san11", "san18", "san08"]

async def run_comprehensive_qa():
    # Ensure current dir is backend
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Load queries
    with open("../evaluation/queries.yaml", "r") as f:
        data = yaml.safe_load(f)
    
    queries = {q["id"]: q for q in data["queries"] if q["id"] in TEST_QUERY_IDS}
    
    print("====================================================")
    print("COMPREHENSIVE MULTI-MODEL QA TEST")
    print("====================================================")

    for tier in ["small", "large"]:
        print(f"\n\n{'#'*60}")
        print(f"### MODEL TIER: {tier.upper()}")
        print(f"{'#'*60}")
        
        for q_id in TEST_QUERY_IDS:
            q = queries[q_id]
            text = q["text"]
            city = q["city"]
            
            print(f"\n--- [QUERY {q_id}] ---")
            print(f"QUESTION: {text}")
            print(f"CITY: {city}")
            print("STEPS:")
            print("  1. Context Building: Retrieving user profile and local history vector DB.")
            print("  2. System Prompt: Applying Local Friend Persona + Calibrated Confidence rules.")
            print("  3. Inference: Processing through OpenRouter API.")
            print("  4. Tool Use: Monitoring for search_web or get_weather triggers.")
            print("  5. Reflection: Self-correcting for factual humility.")
            
            human = HumanMessage(content=f"Backend context: user_id=test_user; focus_city={city}.\n\n{text}")
            
            try:
                answer, elapsed = run_chat_turn(
                    [human],
                    tier=tier,
                    user_id="test_user",
                    city=city,
                    latitude=None,
                    longitude=None
                )
                print(f"  6. Done! Elapsed Time: {elapsed:.2f}s")
                print("\n[USER OUTPUT]:")
                print("vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv")
                print(answer)
                print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
            except Exception as e:
                print(f"  [ERROR]: {e}")

if __name__ == "__main__":
    asyncio.run(run_comprehensive_qa())
