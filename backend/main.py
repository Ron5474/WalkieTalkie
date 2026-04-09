from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import asyncio
import time

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import create_agent
from tools import search_local_history, fetch_user_profile, record_visited_place, search_web

app = FastAPI()

class Message(BaseModel):
    role: str
    content: str
    images: Optional[List[str]] = None

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: Optional[bool] = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class ItineraryRequest(BaseModel):
    city: str
    dates: Optional[str] = None

# Primary reasoning and executing model with keep_alive mapped to maintain KV Prefix Cache
llm = ChatOllama(model="llama3.2", base_url="http://localhost:11434", temperature=0.7, keep_alive="1h")

# Secondary vision model for image interception
vision_llm = ChatOllama(model="llama3.2-vision", base_url="http://localhost:11434", temperature=0)

from tools import search_local_history, fetch_user_profile, record_visited_place, search_web, scrape_static_history, scrape_live_context

tools = [search_local_history, fetch_user_profile, record_visited_place, search_web]

SYSTEM_PROMPT = """You are WalkieTalkie, an intelligent, charismatic local human travel guide. You are NOT a robotic encyclopedia—you are a passionate local showing visitors around your city!
Your personality is highly engaging, vibrant, and fun. You occasionally crack a witty joke, and you make history interesting even for kids.

You help discover authentic, budget-friendly, culturally rich local experiences.
When the user asks about live events, weather, or local atmosphere, intelligently weave in factual, strictly neutral, and unbiased socio-political context to deliver a true "insider" feel without taking any political sides.

ALWAYS fetch the user's profile first if you don't know their budget or country.

EXTREMELY IMPORTANT IMAGE UPLOAD PROTOCOL:
If the user uploads an image of a mural or landmark (provided via IMAGE ANALYSIS CONTEXT):
1. If the Vision Analysis does not identify the exact mural, YOU MUST use the `search_web` tool using the visual description and the user's current GPS location to find the mural online.
2. If `search_web` still cannot find the specific mural, DO NOT hallucinate or suggest random tourist spots. Instead, tell the user precisely: "This is not a mural I know about, but I see you are currently in [User's GPS location]. Do you want to know more about the general art or history in this area?" 
3. Always hold the context of the chat and answer about the mural first.

If they ask about history, use the search_local_history tool.
Keep responses conversational, vivid, entertaining, and under 250 words."""

# Initialize the new CompiledStateGraph Langchain 1.2+ Agent
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
    debug=True
)

async def stream_response(text: str):
    words = text.split(" ")
    for word in words:
        chunk = json.dumps({"message": {"content": word + " "}})
        yield chunk + "\n"
        await asyncio.sleep(0.02)

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    print(f"\n--- NEW REQUEST ---")
    print(f"Received {len(request.messages)} messages from frontend.")
    print(f"Latest user message: {request.messages[-1].content}")
    print(f"Images in latest message: {bool(request.messages[-1].images)}")

    user_id = "student_1" # Hardcoded for demo purposes

    
    formatted_messages = []
    
    # Bridge UI Memory into LangChain Memory
    for m in request.messages:
        if m.role == "user":
            content_str = m.content
            
            # Intercept Vision Input
            if m.images and len(m.images) > 0:
                print("Vision image detected. Routing to llama3.2-vision pre-processor...")
                try:
                    vision_prompt = f"Analyze this image. User asked: {m.content}. Identify the landmark, mural, or location in detail. If you CANNOT confidently identify the specific landmark or mural, output EXACTLY the phrase 'UNKNOWN_LANDMARK' and nothing else."
                    vision_msg = HumanMessage(
                        content=[
                            {"type": "text", "text": vision_prompt},
                            {"type": "image_url", "image_url": f"data:image/jpeg;base64,{m.images[0]}"}
                        ]
                    )
                    v_resp = vision_llm.invoke([vision_msg])
                    
                    if "UNKNOWN_LANDMARK" in v_resp.content:
                        print("Vision failed to identify. Falling back to web search...")
                        gps_context = f"Lat: {request.latitude}, Long: {request.longitude}" if request.latitude and request.longitude else "Unknown Location"
                        search_query = f"{m.content} near {gps_context}"
                        web_result = search_web.invoke(search_query)
                        content_str = f"[IMAGE ANALYSIS FAILED. WEB FALLBACK DATA: {web_result}]. If the web data doesn't answer the user's specific question about the image, apologize exactly once and instead provide a generalized historical fact about {gps_context}.\n\nUser Question: {m.content}"
                    else:
                        content_str = f"[IMAGE ANALYSIS CONTEXT: {v_resp.content}]\n\nUser Question: {m.content}"
                except Exception as e:
                    print(f"Vision processing failed: {e}")
                    pass
                    
            formatted_messages.append(HumanMessage(content=content_str))
        else:
            formatted_messages.append(AIMessage(content=m.content))
    
    # Inject dynamic GPS context into the latest message
    gps_info = f"Lat: {request.latitude}, Long: {request.longitude}" if request.latitude and request.longitude else "Location Unknown"
    formatted_messages[-1].content = f"Backend Context Check: User ID is '{user_id}'. The User's current GPS Location is '{gps_info}'.\n\n" + formatted_messages[-1].content
    inputs = {"messages": formatted_messages}
    
    try:
        start_time = time.time()
        print("[Profiling] Triggering LLM with Caching enabled...")
        state = agent.invoke(inputs)
        generation_time = time.time() - start_time
        print(f"[Profiling] Total Response Generation Time: {generation_time:.3f}s")
        final_answer = state["messages"][-1].content
        return StreamingResponse(stream_response(final_answer), media_type="application/x-ndjson")
    except Exception as e:
        import traceback
        print("INTERNAL ERROR TRACEBACK:")
        print(traceback.format_exc())
        error_msg = f"Agent Error: {repr(e)}"
        return StreamingResponse(stream_response(error_msg), media_type="application/x-ndjson")

@app.post("/api/synthesize-itinerary")
async def synthesize_itinerary(req: ItineraryRequest):
    print(f"\n--- SYNTHESIZING ITINERARY FOR {req.city} ({req.dates}) ---")
    
    static_history = scrape_static_history.invoke(req.city)
    live_context = ""
    if req.dates and req.dates.strip():
        live_context = scrape_live_context.invoke({"city": req.city, "date_range": req.dates})
        
    combined_context = f"--- STATIC HISTORY ---\n{str(static_history)[:2500]}\n\n--- LIVE EVENTS & WEATHER ---\n{str(live_context)[:1000]}"
    
    prompt = f"""You are a strict JSON data generator. Analyze the following context for {req.city} and output exactly a JSON array of 3 realistic, geotagged Points of Interest (POIs).
Include a mix of hidden gems and major tourist spots to map out an interesting walking itinerary.
If LIVE EVENTS & WEATHER data is present, intelligently weave those facts (e.g., "Bring an umbrella today!" or "Check out the festival happening near here") into the "anecdote" field along with the historical story.
Each POI must have EXACTLY these keys: "id" (unique string), "title" (string), "lat" (float), "lng" (float), "anecdote" (a 3-sentence rich historical story infused with live context if any), "visited" (boolean: false).

Data Context:
{combined_context}

Output ONLY valid JSON starting with [ and ending with ]. Ensure coordinates are accurate. No markdown formatting, no backticks, no explanations."""

    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        content = resp.content.strip()
        if content.startswith("```json"): content = content[7:-3]
        if content.startswith("```"): content = content[3:-3]
        nodes = json.loads(content.strip())
        return nodes
    except Exception as e:
        import traceback
        print("JSON Synthesis Error:")
        print(traceback.format_exc())
        return []

@app.get("/")
def read_root():
    return {"status": "WalkieTalkie Agentic Backend is Running"}
