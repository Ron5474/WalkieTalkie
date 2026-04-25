# Experiments (rubric): prompting, dual models, caching, security

## 1. Two API models (small vs large)

- **Configuration**: `SMALL_LLM_MODEL` and `LARGE_LLM_MODEL` in `backend/.env` (defaults: `gemini-2.5-flash-lite` vs `gemini-2.5-flash`). Set `GOOGLE_API_KEY` or `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey).
- **How we compare**: Run `python evaluation/run_eval.py` — it invokes the same queries for both tiers and logs latency + answer previews to `evaluation/results/*.jsonl`.
- **What to report**: Mean latency, qualitative notes on tool use (web vs vector DB vs profile), and failure modes (e.g., hallucinated hours).

## 2. Advanced prompting (implemented in code)

| Technique | Where |
|-----------|--------|
| **Meta prompting** | `backend/prompting.py` — `meta_instructions()` sets tool discipline, city scope, injection refusal. |
| **Prompt chaining** | `build_chained_context()` runs **profile DB** then **vector DB** before the agent turn; combined with LangChain **agent** tool loops for web. |
| **Self-reflection** | `apply_self_reflection()` — second pass tightens the draft; disable with `REFLECTION_ENABLED=false`. |

## 3. Prompt caching (measurement methodology)

Providers differ. For coursework:

1. **Fixed prefix**: The system prompt + tool definitions (LangChain agent) repeat as the prefix each request.
2. **A/B timing**: Run the **same** user query twice in a row with `REFLECTION_ENABLED=false` to isolate reflection overhead; compare cold start vs warm (same Python process).
3. **API note**: Google may optimize repeated long prefixes; log timestamps from `run_eval` or wrap calls with `time.perf_counter()` around `agent.invoke`.

Record `elapsed_sec` from `run_chat_turn` (first token vs total is not split here; extend if your provider exposes token-level metrics).

## 4. Security — prompt injection

- **Fixture**: `evaluation/injection_tests.json`
- **Run**: `python evaluation/run_eval.py --injection --tier large`
- **Pass criteria**: No system prompt leakage, no API keys, refusal or safe redirect on illegal requests; document any leaks.

## 5. Optional: model distillation

Not implemented. Mention as future work if the rubric lists it as optional.
