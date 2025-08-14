"""
Pydantic schemas for API input and output validation.
These models are used by FastAPI to serialize and deserialize data,
while the NDB models are used for database interaction.
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional

class ApiTokenSchema(BaseModel):
    uid: str
    user_uid: str
    name: str
    token_display: str
    created: datetime
    active: bool
    expires: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserSchema(BaseModel):
    uid: str
    email: EmailStr
    name: str
    created: datetime
    active: bool
    api_tokens: List[str] = []

    class Config:
        from_attributes = True

class TokenCreateRequest(BaseModel):
    name: str
    expires_days: Optional[int] = None
