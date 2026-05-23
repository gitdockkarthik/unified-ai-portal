import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

from database import engine, Base
from agents.cur.routes import router as cur_router
from agents.alerts.routes import router as alerts_router

app = FastAPI(title="Unified AI Portal", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

app.include_router(cur_router)
app.include_router(alerts_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "unified-ai-portal"}


@app.get("/api/agents")
async def list_agents():
    from database import AsyncSessionLocal
    from models import Agent
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Agent).order_by(Agent.id))
        agents = result.scalars().all()
        return [
            {"id": a.id, "name": a.name, "slug": a.slug, "description": a.description,
             "icon": a.icon, "status": a.status}
            for a in agents
        ]


# Serve frontend static files if present
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(frontend_path, "index.html"))
