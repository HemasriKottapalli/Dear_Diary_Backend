from fastapi import FastAPI
from api.v1.api import api_router
from db import base
from db.session import engine


# create tables (use Alembic in prod)
base.Base.metadata.create_all(bind=engine)


app = FastAPI(title="Diary App")
app.include_router(api_router, prefix="/api")