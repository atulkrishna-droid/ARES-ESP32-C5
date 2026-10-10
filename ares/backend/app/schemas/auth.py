"""Authentication and Token Pydantic Schemas."""
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    display_name: Optional[str] = None
    role: Optional[str] = "ANALYST"


class UserLoginRequest(BaseModel):
    username_or_email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    username: str
    roles: List[str]
    permissions: List[str]


class TokenRefreshRequest(BaseModel):
    refresh_token: str
