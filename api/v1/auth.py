from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
import re

from db.session import SessionLocal
from models.user import User
from schemas.auth import Login, UserCreate, Token, TokenData
from config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(subject), "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None

# ---- DB dependency ----

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---- routes ----
@router.post("/register", response_model=Token)
def register(payload: UserCreate, db: Session = Depends(get_db)):

    email_normal = payload.email.strip().lower()
    username_normal = payload.username.strip().lower()

    if not re.fullmatch(r"[A-Za-z0-9_\.]+", username_normal):
        raise HTTPException(
            status_code=400,
            detail="Invalid username format. Only letters, numbers, underscore, and dot allowed."
        )

    # check email
    existing = db.query(User).filter(User.email == email_normal).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # check username
    if db.query(User).filter(User.username == username_normal).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=email_normal,
        username=username_normal,
        hashed_password=hash_password(payload.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id))
    return Token(access_token=token)


@router.post("/login", response_model=Token)
def login(payload: Login, db: Session = Depends(get_db)):
    identifier = payload.identifier.strip().lower()
    password = payload.password

    # Try email first, then username — single DB query using OR is also possible
    user = db.query(User).filter((User.email == identifier) | (User.username == identifier)).first()

    if not user or not verify_password(password, user.hashed_password):
        # don't reveal which part failed
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(str(user.id))
    return Token(access_token=token)

# ---- optional helper to use in protected endpoints ----
def get_current_user(token: str, db: Session) -> User | None:
    payload = decode_access_token(token)
    if not payload:
        return None
    
    sub = payload.get("sub")

    if not sub:
        return None
    
    user = db.query(User).get(int(sub))
    return user