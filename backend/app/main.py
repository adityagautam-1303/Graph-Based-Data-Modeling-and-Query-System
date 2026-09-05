"""FastAPI backend for Order-to-Cash Graph & Chat."""
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

from .graph_service import build_graph
from .sql_agent import query_natural_language

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="Order to Cash - Graph & Chat API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    history: Optional[list] = None


class ChatResponse(BaseModel):
    answer: str
    sql: Optional[str] = None
    data: Optional[list] = None
    highlighted_nodes: Optional[list] = None


class GraphQuery(BaseModel):
    focus_entity: Optional[str] = None
    focus_id: Optional[str] = None
    limit: Optional[int] = 50000


@app.get("/api/graph")
def get_graph(focus_entity: Optional[str] = None, focus_id: Optional[str] = None, limit: int = 50000):
    """Return graph nodes and edges. Optionally filter by focus entity."""
    try:
        data = build_graph(limit=limit, focus_entity=focus_entity, focus_id=focus_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Natural language query -> SQL -> data-backed answer."""
    try:
        result = query_natural_language(req.message, history=req.history)
        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])
        return ChatResponse(
            answer=result.get("answer") or "No answer generated.",
            sql=result.get("sql"),
            data=result.get("data"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def root():
    """Root endpoint for status check."""
    return {"status": "ok", "message": "Order to Cash Graph & Chat API is running", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/cron")
def cron_keep_alive():
    """Endpoint for cron jobs to keep the backend service active."""
    return {"status": "ok"}

