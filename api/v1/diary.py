from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from utilities import get_db, get_current_user
from schemas.diary import DiaryCreate, DiaryOut, DiaryUpdate
from models.diary import DiaryEntry
from models.user import User
from ai.diary_indexing import index_diary_entry


router = APIRouter(prefix="/diary", tags=["diary"])

@router.post("/", response_model=DiaryOut, status_code=status.HTTP_201_CREATED)
def create_entry(payload: DiaryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry = DiaryEntry(
        owner_id=current_user.id,
        title=payload.title,
        content=payload.content,
        mood=payload.mood  # ADD THIS LINE
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    # diary indexing
    index_diary_entry(db, entry, current_user.id)
    db.commit()

    return entry

@router.get("/", response_model=List[DiaryOut])
def list_entries(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    entries = (
        db.query(DiaryEntry)
        .filter(DiaryEntry.owner_id == current_user.id)
        .order_by(DiaryEntry.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return entries

@router.get("/{entry_id}", response_model=DiaryOut)
def get_entry(entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry = (
        db.query(DiaryEntry)
        .filter(DiaryEntry.id == entry_id, DiaryEntry.owner_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry

@router.put("/{entry_id}", response_model=DiaryOut)
def update_entry(entry_id: int, payload: DiaryUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry = (
        db.query(DiaryEntry)
        .filter(DiaryEntry.id == entry_id, DiaryEntry.owner_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Track if we need to re-index
    needs_reindex = False

    if payload.title is not None:
        entry.title = payload.title
    if payload.content is not None:
        entry.content = payload.content
        needs_reindex = True  # Re-index if content changes
    if payload.mood is not None:  # ADD THIS BLOCK
        entry.mood = payload.mood

    # Only re-index if content changed
    if needs_reindex:
        index_diary_entry(db, entry, current_user.id)

    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry = (
        db.query(DiaryEntry)
        .filter(DiaryEntry.id == entry_id, DiaryEntry.owner_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    db.delete(entry)
    db.commit()
    return None