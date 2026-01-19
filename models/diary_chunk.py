from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, func
from db.base import Base

class DiaryChunk(Base):
    __tablename__ = "diary_chunks"

    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey("diary_entries.id", ondelete="CASCADE"))
    owner_id = Column(Integer, index=True)

    chunk_text = Column(Text, nullable=False)
    embedding = Column(Text, nullable=False)  # JSON string
    chunk_index = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
