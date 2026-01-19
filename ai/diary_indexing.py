import json
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from models.diary_chunk import DiaryChunk

# Load once
_embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


def _chunk_text(text: str, max_chars: int = 500):
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, current = [], ""

    for p in paragraphs:
        if len(current) + len(p) <= max_chars:
            current += " " + p
        else:
            chunks.append(current.strip())
            current = p

    if current:
        chunks.append(current.strip())

    return chunks


def _embed(text: str):
    return _embedding_model.encode(text).tolist()


def index_diary_entry(db: Session, entry, user_id: int):
    # Delete old chunks (safe for create + update)
    db.query(DiaryChunk).filter(
        DiaryChunk.entry_id == entry.id
    ).delete()

    chunks = _chunk_text(entry.content)

    for i, chunk in enumerate(chunks):
        embedding = _embed(chunk)
        db.add(DiaryChunk(
            entry_id=entry.id,
            owner_id=user_id,
            chunk_text=chunk,
            embedding=json.dumps(embedding),
            chunk_index=i
        ))
