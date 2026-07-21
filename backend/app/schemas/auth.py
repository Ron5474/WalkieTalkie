from typing import Optional

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None
    budget: Optional[int] = None
    dietary: Optional[str] = None
    country: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UpdateProfileRequest(BaseModel):
    budget: Optional[int] = None
    dietary: Optional[str] = None
    country: Optional[str] = None


class VisitedPlaceRequest(BaseModel):
    city: str
    place_name: str


class CityWarmupRequest(BaseModel):
    city: str
