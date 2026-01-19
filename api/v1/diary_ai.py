from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid

from utilities import get_db, get_current_user
from models.user import User
from ai.diary_chat import chat_with_diary
from ai.weekly_summary import generate_weekly_summary

router = APIRouter(prefix="/diary/ai", tags=["diary-ai"])


# Pydantic models for request/response validation
class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None  # Optional: frontend can maintain session, or we generate


class ChatResponse(BaseModel):
    answer: str
    show_suggestions: bool
    related_entry_ids: list[int]
    session_id: str  # Return it so frontend can track


class WeeklySummaryResponse(BaseModel):
    summary: str


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Chat with your diary using natural language.
    Maintains conversation context for 2 hours.
    Intelligently decides when to show entry suggestions.
    
    Requires Bearer token in Authorization header.
    """
    # Generate session_id if not provided
    session_id = payload.session_id or str(uuid.uuid4())
    
    result = chat_with_diary(
        db=db,
        user_id=current_user.id,
        session_id=session_id,
        question=payload.question
    )
    
    return {
        **result,
        "session_id": session_id
    }


@router.post("/weekly-summary", response_model=WeeklySummaryResponse)
def weekly_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a weekly summary of diary entries for the authenticated user.
    Requires Bearer token in Authorization header.
    """
    summary = generate_weekly_summary(db, current_user.id)
    return {"summary": summary}


# Keep old endpoint for backward compatibility (optional)
# You can remove this later once you're sure the new /chat works
"""
@router.post("/ask", response_model=AskDiaryResponse)
def ask_diary_endpoint(
    payload: AskDiaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ai.diary_qa import ask_diary
    result = ask_diary(db, current_user.id, payload.question)
    return result
"""