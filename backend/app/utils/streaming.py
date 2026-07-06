"""NDJSON streaming helper.

NOTE: this animates an already-computed string word-by-word (Ollama-style chunk
shape the frontend expects). It is not true token streaming from the model.
"""
import asyncio
import json


async def stream_response(text: str):
    words = text.split(" ")
    for word in words:
        chunk = json.dumps({"message": {"content": word + " "}})
        yield chunk + "\n"
        await asyncio.sleep(0.02)
