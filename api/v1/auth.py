from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
import re

from utilities import get_db
from models.user import User
from schemas.auth import Login, UserCreate, Token
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


@router.post("/register", response_model=Token)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    email_normal = payload.email.strip().lower()
    username_normal = payload.username.strip().lower()

    if not re.fullmatch(r"[A-Za-z0-9_\.]+", username_normal):
        raise HTTPException(
            status_code=400,
            detail="Invalid username format. Only letters, numbers, underscore, and dot allowed."
        )

    # Check email
    existing = db.query(User).filter(User.email == email_normal).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check username
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
    return {
        "access_token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    }


@router.post("/login", response_model=Token)
def login(payload: Login, db: Session = Depends(get_db)):
    identifier = payload.identifier.strip().lower()
    password = payload.password

    user = db.query(User).filter(
        (User.email == identifier) | (User.username == identifier)
    ).first()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    token = create_access_token(str(user.id))
    return {
        "access_token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    }