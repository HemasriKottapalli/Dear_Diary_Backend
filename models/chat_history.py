from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from db.base import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)  # UUID for grouping conversation
    
    role = Column(String(50), nullable=False)  # "user" or "assistant"
    message = Column(Text, nullable=False)
    
    # Optional: store which entries were shown as suggestions
    suggested_entry_ids = Column(Text, nullable=True)  # JSON array as string, e.g., "[1,2,3]"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)