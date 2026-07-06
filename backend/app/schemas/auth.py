from typing import Optional

from pydantic import BaseModel


class SignInRequest(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    budget: Optional[int] = None
    dietary: Optional[str] = None
    country: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    session_token: str
    budget: Optional[int] = None
    dietary: Optional[str] = None
    country: Optional[str] = None


class VisitedPlaceRequest(BaseModel):
    session_token: str
    city: str
    place_name: str


class LogoutRequest(BaseModel):
    session_token: str


class CityWarmupRequest(BaseModel):
    city: str
