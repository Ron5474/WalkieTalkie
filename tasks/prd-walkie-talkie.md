# Product Requirements Document: Walkie-Talkie Virtual Assistant

## 1. Introduction/Overview
The **Context-Aware Walking Assistant (Walkie-Talkie)** is an LLM-based Virtual Assistant crafted primarily for budget-conscious student travelers. Unlike standard mapping apps, it functions as an "Urban Anthropologist." It bridges the gap between static maps and expensive guided tours by using a dual LLM architecture, offering immersive audio storytelling, visual landmark identification, logical budget routing, and a personal travel ledger. 

## 2. Goals
* Provide an authentic, layered walking tour experience by utilizing a user's location to deliver contextual stories about specific local neighborhoods.
* Enable multimodal, on-the-fly discovery for travelers who want to know the meaning behind street art or structural landmarks.
* Optimize the student travel experience with real-time budget, visa, and logistics strategies.
* Demonstrate technical prowess in combining multi-tool chaining, prompt caching, and small/large model orchestration.

## 3. User Stories
* As a curious traveler, I want to take a photo of a street mural and have the assistant explain the cultural message behind it, so I can understand the local community.
* As an explorer, I want the app to know my location along a route and occasionally give me a spontaneous historical story about an unmarked building nearby.
* As someone unfamiliar with the city, I want the app to suggest thematic walking tours (e.g., "Industrial History of Dogpatch") and then provide step-by-step live guidance to each stop.
* As a budget student, I want to ask for a walking route connecting points *A* and *B*, and receive culturally unique stops on the way, alongside an option for a local meal depending on the time of day.
* As a frequent visitor to a city, I want the app to save the places I have already visited to a local database ledger so I can cover other places the next time I visit the place.

## 4. Functional Requirements
1. **Dynamic Web Scraper & Itinerary Synthesizer**: The application must autonomously query the web for top search results (5-10 blogs/history sites) for a destination to map out both major tourist attractions and local hidden gems. It must bifurcate this data retrieval: 
    * **Static History**: One-time background scrape for unchangeable local history and monuments.
    * **Dynamic Live Context**: Real-time web search/scrape for weather, festivals, and local events strictly based on the user's selected travel dates.
    * It must generate personalized itineraries matching these contexts to user profiles.
2. **The Proactive Tour Guide & Navigator**: The app must be able to suggest complete, multi-stop walking tours based on user interests or budget. It will use a Navigation API (e.g. Google Maps/OSM) to provide step-by-step live guidance from point to point, acting as the tour guide.
    * *Proactive Mode*: As a travel agent, the system must proactively suggest the best times to visit locations or propose activities if the tourist is uncertain what to do.
3. **App State Modules (Planning vs. On-Trip)**: The UI must adapt to the user's current phase. In "Pre-Trip", it acts as a planner. In "On-Holiday", it opens directly to a daily "Plan of Action" list.
    * *Pre-Trip Parameters*: The interface must allow users to define Trip Duration (Days) and Budget parameters prior to generation.
    * *Tabbed Output UI*: The planning view must synthesize results into distinct interactive tabs: (1) All possible points of interest, (2) Must Eats near the POIs, and (3) A Day-by-Day structured Itinerary.
4. **Dynamic Re-Routing & Deduplication**: The generated itinerary must be fluid. As the user checks off or inputs that they have "covered" a place, the remainder of the day's itinerary must intelligently update. The LLM engine must strictly guarantee that points of interest are never repeated across different days or tabs.
5. **The "Walk With Me" Narrator**: The app must use a simulated or real Geolocation API. If a user is near a defined story-point coordinate, the system should trigger an anecdotal audio/text story. The narration persona must be highly engaging (cracking jokes, accessible to children) and intelligently weave in current, unbiased political and local context to mimic an authentic human guide.
4. **Visual "Explorer" Eye**: The assistant must accept and process user-uploaded images to identify landmarks, menus, or murals.
    * *Fallback Logic*: If the multimodal LLM fails to identify the image content, it must automatically use a Web Search Tool. 
    * *Ultimate Fallback*: If the web search *also* fails, the VA must let the user know and intelligently pivot to providing a generalized historical anecdote about the neighborhood they are currently standing in.
5. **Student Budget & Strategy Agent**: The assistant must be able to use tools to fetch real-time constraint data (e.g., the 2026 $250 Visa Integrity Fee, or live transit routing times vs costs). 
6. **Personal "Travel Ledger"**: The application must incorporate a Relational SQL DB to track a user's "Explorer Profile," tracking which hidden gems they have already discovered to tailor future recommendations.
7. **Logic Routing (Multi-LLM Orchestration)**: The system must use a routing mechanism to send heavy logical/spatial tracking tasks to a "Thinker" Large Model (e.g. Llama-3.1-8B) and simpler, creative storytelling tasks to a "Speedster" Small Model (e.g. Phi-3.5-mini).

## 5. Non-Goals (Out of Scope)
* **Immediate Global Expansion**: At launch, the application will explicitly only support 9 specific cities: San Francisco, Boston, New York, San Diego, Kyoto, Tokyo, London, Kolkata, and Mumbai. It will not attempt to map every point on the globe until the MVP is successful.
* **Direct Booking Engines**: The app will compute costs and optimize budgets, but it will not act as a booking or transaction engine for flights and hostels.

## 6. Design Considerations
* **Hands-Free "Walkie-Talkie" Vibe**: The user interface should lean heavily into audio feedback and concise text. The user should be looking at the city, not staring at their phone for paragraphs of history.
* **Image Side-Panels**: Uploaded images should smoothly open side-panels or chat cards outlining the specific "why it is significant" decoder rings for murals/buildings.

## 7. Technical Considerations
* **Vector & Relational Storage**: Requires a Vector DB (like ChromaDB or Pinecone) for querying unstructured historical anecdotes and an SQL DB for the user Travel Ledger.
* **Tool Chaining**: The system relies heavily on Prompt Chaining and Web Search wrappers (Tavily/Google Search) to enrich LLM hallucination-prone areas (like weather or event dates in 2026).
* **Prompt Caching**: Due to the heavy 500-word system prompt ("Urban Anthropologist" persona), KV Prefix Caching must be aggressively utilized to keep interaction response times snappy.

## 8. Success Metrics
* **Technical Performance (Primary)**: Achieving a Time to First Token (TTFT) of **< 0.5 seconds**, primarily driven by successful implementation of Prompt Caching optimizations.
* **Algorithm Accuracy (Primary)**: Maintaining a high success rate on the multimodal Visual "Explorer" feature for classifying landmarks accurately (or transparently utilizing the fallback mechanisms).

## 9. Open Questions
* What are the physical constraints of running the dual-model setup locally vs. via Google Colab in terms of prompt-caching configurations?
