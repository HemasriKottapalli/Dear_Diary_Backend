from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ai.llm import get_llm
from models.diary import DiaryEntry

WEEKLY_SUMMARY_PROMPT = """
You are a quiet writing guide.

Based on the diary entries below, write ONE short sentence
that points the user toward something specific they could
continue writing about.

Rules:
- Not a question
- Not a conversation
- Reference something concrete from the entries
- Calm, natural tone
- Feels like a thought, not a reply

Diary entries:
{entries}
"""


# -------- DB FETCH (repo logic) --------
def fetch_last_week_entries(db: Session, user_id: int) -> list[str]:
    start_date = datetime.utcnow() - timedelta(days=7)

    diaries = (
        db.query(DiaryEntry)
        .filter(DiaryEntry.owner_id == user_id)
        .filter(DiaryEntry.created_at >= start_date)
        .order_by(DiaryEntry.created_at.asc())
        .all()
    )

    return [d.content for d in diaries]

# -------- AI SERVICE --------
def generate_weekly_summary(db: Session, user_id: int) -> str:
    entries = fetch_last_week_entries(db, user_id)
    llm = get_llm()

    # Case 1: No entries
    if not entries:
        return (
            "This week looks quiet. Even a few lines about how you’re feeling "
            "can be a great place to start. Want to write something now?"
        )

    # Case 2: Only one entry
    if len(entries) == 1:
        prompt = f"""
        You are a gentle writing assistant.

        Reflect briefly on the following diary entry.
        Encourage the user to expand their thoughts without pressure.

        Diary entry:
        {entries[0]}
        """
        return llm.invoke(prompt).content

    # Case 3: Two or more entries
    joined_entries = "\n\n".join(entries)
    prompt = WEEKLY_SUMMARY_PROMPT.format(entries=joined_entries)
    return llm.invoke(prompt).content
