from fastapi import FastAPI
from api.v1.api import api_router
from db import base
from db.session import engine
from fastapi.middleware.cors import CORSMiddleware


# create tables (use Alembic in prod)
base.Base.metadata.create_all(bind=engine)


app = FastAPI(title="Diary App")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your React app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")