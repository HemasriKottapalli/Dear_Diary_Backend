# config.py  -- minimal, dotenv-based config (no pydantic needed)
import os
from pathlib import Path
from dotenv import load_dotenv

# Locate .env in the project root (where main.py is)
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24))
    DATABASE_URL: str = os.getenv("DATABASE_URL")  # Must be set in .env

settings = Settings()
