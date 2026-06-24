import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, city, health, itinerary

_LOG_LEVEL = (os.getenv("APP_LOG_LEVEL") or "DEBUG").upper()
logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.DEBUG),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(itinerary.router)
app.include_router(auth.router)
app.include_router(city.router)
app.include_router(health.router)
