# Run with (from API/ dir): ..\\.venv\Scripts\uvicorn main:app --reload
# Docs at:  http://127.0.0.1:8000/docs

from fastapi import FastAPI
from routers import make_router

app = FastAPI(title="Elden Ring API")

# --- Register routes ---
# Each entry needs a matching JSON file in data/<model>.json

app.include_router(make_router("bosses"))
# app.include_router(make_router("weapons"))
# app.include_router(make_router("armors"))
