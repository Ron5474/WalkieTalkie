"""Recover a JSON object from messy LLM output (CoT blocks, markdown fences, prose)."""
import json


def extract_json_object(raw: str) -> dict:
    content = (raw or "").strip()
    if "<final_answer>" in content and "</final_answer>" in content:
        content = content.split("<final_answer>")[-1].split("</final_answer>")[0].strip()
    elif "</planning>" in content:
        content = content.split("</planning>")[-1].strip()
    if content.startswith("```json"):
        content = content[7:-3]
    if content.startswith("```"):
        content = content[3:-3]
    start_idx = content.find("{")
    end_idx = content.rfind("}")
    if start_idx != -1 and end_idx != -1:
        content = content[start_idx : end_idx + 1]
    return json.loads(content)
