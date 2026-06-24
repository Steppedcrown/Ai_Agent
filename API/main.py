# Run with (from API/ dir): uvicorn main:app --reload
# Docs at:  http://127.0.0.1:8000/docs

from fastapi import FastAPI
from routers import bosses_router

app = FastAPI(title="Elden Ring API")

app.include_router(bosses_router)
