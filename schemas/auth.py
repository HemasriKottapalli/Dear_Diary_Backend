from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str = Field(
        ..., 
        pattern=r"^[A-Za-z0-9_\.]+$", 
        description="Username may contain letters, numbers, underscores, dots, but no spaces."
    )

class Login(BaseModel):
    identifier: str   # accepts email or username
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    sub: Optional[str] = None