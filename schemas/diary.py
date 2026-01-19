from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DiaryBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: Optional[str] = None
    mood: Optional[str] = Field(default='neutral', max_length=50)  # NEW FIELD

class DiaryCreate(DiaryBase):
    pass

class DiaryUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = None
    mood: Optional[str] = Field(None, max_length=50)  # NEW FIELD

class DiaryOut(DiaryBase):
    id: int
    owner_id: int
    mood: Optional[str] = None  # NEW FIELD (explicitly include in response)
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True