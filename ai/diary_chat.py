import json
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

from ai.llm import get_llm
from models.diary_chunk import DiaryChunk
from models.chat_history import ChatHistory

_embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

DIARY_CHAT_PROMPT = """You are a personal diary assistant. Your ONLY job is to help the user find and understand their diary entries.

Recent Diary Entries Found:
{context}

User Question: {question}

Previous messages (for context only): {chat_history}

CRITICAL RULES:
1. Focus ONLY on answering the current question using the diary entries above
2. DO NOT summarize previous conversation unless explicitly asked
3. If user asks for specific emotions/topics, ONLY mention entries that match (e.g., "happy" → only happy entries)
4. If the question is casual (hi, thanks, how are you), respond briefly and warmly
5. If asking about specific memories/feelings, quote or reference the diary entries directly
6. Keep responses concise - 2-3 sentences maximum unless more detail is needed

After your answer, write EXACTLY one line:
SHOW_SUGGESTIONS: YES (if you mentioned specific diary entries the user should read)
SHOW_SUGGESTIONS: NO (if casual chat or no relevant entries found)

Answer:"""


RELEVANCE_THRESHOLD = 0.30  # Increased for better precision


def _embed(text: str):
    return _embedding_model.encode(text).tolist()


def _get_chat_history(db: Session, user_id: int, session_id: str, limit: int = 5):
    """Retrieve recent chat history for context (reduced limit)"""
    two_hours_ago = datetime.utcnow() - timedelta(hours=2)
    
    messages = db.query(ChatHistory).filter(
        ChatHistory.user_id == user_id,
        ChatHistory.session_id == session_id,
        ChatHistory.created_at >= two_hours_ago
    ).order_by(
        ChatHistory.created_at.desc()
    ).limit(limit).all()
    
    # Reverse to get chronological order
    messages.reverse()
    
    return [
        f"{msg.role.capitalize()}: {msg.message}"
        for msg in messages
    ]


def _cleanup_old_chats(db: Session):
    """Remove chat history older than 2 hours"""
    two_hours_ago = datetime.utcnow() - timedelta(hours=2)
    db.query(ChatHistory).filter(
        ChatHistory.created_at < two_hours_ago
    ).delete()


def _save_message(db: Session, user_id: int, session_id: str, role: str, message: str, suggested_ids=None):
    """Save a message to chat history"""
    chat_entry = ChatHistory(
        user_id=user_id,
        session_id=session_id,
        role=role,
        message=message,
        suggested_entry_ids=json.dumps(suggested_ids) if suggested_ids else None
    )
    db.add(chat_entry)


def chat_with_diary(db: Session, user_id: int, session_id: str, question: str):
    """
    Main chat function with intelligent suggestion detection
    
    Args:
        db: Database session
        user_id: Current user ID
        session_id: Session identifier for grouping conversations
        question: User's question/message
        
    Returns:
        dict with 'answer', 'show_suggestions', and 'related_entry_ids'
    """
    # Cleanup old chats periodically (you could also run this as a scheduled job)
    _cleanup_old_chats(db)
    
    # Get chat history for context
    chat_history = _get_chat_history(db, user_id, session_id)
    chat_context = "\n".join(chat_history) if chat_history else "No previous conversation."
    
    # Retrieve all user's diary chunks
    chunks = db.query(DiaryChunk).filter(
        DiaryChunk.owner_id == user_id
    ).all()
    
    if not chunks:
        answer = "You don't have any diary entries yet. Start writing to build your personal memory!"
        _save_message(db, user_id, session_id, "user", question)
        _save_message(db, user_id, session_id, "assistant", answer)
        db.commit()
        
        return {
            "answer": answer,
            "show_suggestions": False,
            "related_entry_ids": []
        }
    
    # Embed the question and find relevant chunks
    question_embedding = _embed(question)
    vectors = np.array([json.loads(c.embedding) for c in chunks])
    scores = cosine_similarity([question_embedding], vectors)[0]
    
    # Filter by relevance threshold and rank
    relevant_chunks_with_scores = [
        (chunk, score) for chunk, score in zip(chunks, scores)
        if score >= RELEVANCE_THRESHOLD
    ]
    
    # Sort by score and take top 8 (increased for better coverage)
    relevant_chunks_with_scores.sort(key=lambda x: x[1], reverse=True)
    top_chunks = relevant_chunks_with_scores[:8]
    
    # Prepare context from relevant chunks
    if top_chunks:
        context = "\n\n".join([
            f"Entry {i+1} (Match: {score:.0%}):\n{chunk.chunk_text}"
            for i, (chunk, score) in enumerate(top_chunks)
        ])
    else:
        context = "No relevant diary entries found."
    
    # Call LLM with full context (with retry logic)
    llm = get_llm()
    prompt = DIARY_CHAT_PROMPT.format(
        chat_history=chat_context,
        context=context,
        question=question
    )
    
    # Retry up to 3 times if HuggingFace API fails
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = llm.invoke(prompt)
            full_response = response.content.strip()
            break
        except Exception as e:
            if attempt == max_retries - 1:
                # Last attempt failed, return friendly error
                answer = "I'm having trouble connecting to my AI brain right now. Please try again in a moment!"
                _save_message(db, user_id, session_id, "user", question)
                _save_message(db, user_id, session_id, "assistant", answer)
                db.commit()
                
                return {
                    "answer": answer,
                    "show_suggestions": False,
                    "related_entry_ids": []
                }
            # Wait a bit before retrying
            import time
            time.sleep(1)
    
    # Parse the response to extract answer and suggestion decision
    answer, show_suggestions = _parse_llm_response(full_response)
    
    # Get entry IDs for suggestions
    related_entry_ids = []
    if show_suggestions and top_chunks:
        related_entry_ids = list({chunk.entry_id for chunk, _ in top_chunks})
    
    # Save conversation to database
    _save_message(db, user_id, session_id, "user", question)
    _save_message(db, user_id, session_id, "assistant", answer, related_entry_ids if show_suggestions else None)
    db.commit()
    
    return {
        "answer": answer,
        "show_suggestions": show_suggestions,
        "related_entry_ids": related_entry_ids
    }


def _parse_llm_response(response: str):
    """Parse LLM response to extract answer and suggestion decision"""
    lines = response.split("\n")
    
    # Look for the SHOW_SUGGESTIONS line
    show_suggestions = False
    answer_lines = []
    
    for line in lines:
        line_upper = line.strip().upper()
        if "SHOW_SUGGESTIONS:" in line_upper:
            # Extract YES/NO
            if "YES" in line_upper:
                show_suggestions = True
            elif "NO" in line_upper:
                show_suggestions = False
        else:
            # This is part of the answer
            answer_lines.append(line)
    
    # Join answer lines and clean up
    answer = "\n".join(answer_lines).strip()
    
    # Remove any trailing delimiter artifacts
    answer = answer.replace("SHOW_SUGGESTIONS:", "").strip()
    
    return answer, show_suggestions