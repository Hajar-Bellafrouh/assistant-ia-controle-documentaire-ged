"""
Étape 4 — API REST (FastAPI).

Rôle :
- Exposer l'assistant RAG via une API HTTP simple
- Charger l'assistant une seule fois au démarrage (pas à chaque requête)

Lancement :
    uvicorn src.api:app --reload --port 8000

Documentation interactive : http://localhost:8000/docs
"""

import sys
from pathlib import Path

# S'assure que le dossier src/ est bien dans le chemin de recherche Python,
# quel que soit l'endroit d'où l'API est lancée (ex: `uvicorn src.api:app`
# depuis la racine du projet, qui n'ajoute que la racine à sys.path, pas src/).
sys.path.append(str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from rag_chain import RagAssistant
from database import save_feedback, get_feedback_stats

from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Assistant documentaire GED — GDS GED Services",
    description="API du Module 1 : assistant RAG pour les opérateurs GED.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en local ; à restreindre si déployé un jour
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chargé une seule fois au démarrage du serveur (évite de recharger le modèle
# et l'index à chaque question).
assistant: RagAssistant | None = None


@app.on_event("startup")
def load_assistant() -> None:
    global assistant
    print("[api] Chargement de l'assistant RAG...")
    assistant = RagAssistant()
    print("[api] Assistant prêt.")


class ChatMessage(BaseModel):
    role: str  # "user" ou "assistant"
    content: str


class QuestionRequest(BaseModel):
    question: str
    history: list[ChatMessage] | None = None


class SourceItem(BaseModel):
    source: str
    extrait: str


class AnswerResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceItem]


@app.get("/health")
def health() -> dict:
    if assistant is None:
        return {"status": "ok", "assistant_charge": False}
    try:
        nb_chunks = assistant.vectorstore.index.ntotal
    except Exception:
        nb_chunks = None
    return {
        "status": "ok",
        "assistant_charge": True,
        "modele": assistant.llm.model,
        "nombre_chunks": nb_chunks,
    }


@app.post("/ask", response_model=AnswerResponse)
def ask(request: QuestionRequest) -> AnswerResponse:
    if assistant is None:
        raise HTTPException(status_code=503, detail="Assistant non initialisé.")
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide.")

    history = [{"role": m.role, "content": m.content} for m in (request.history or [])]
    result = assistant.ask(request.question, chat_history=history)
    return AnswerResponse(**result)


@app.post("/ask/stream")
def ask_stream(request: QuestionRequest):
    """Variante en flux (streaming) : renvoie d'abord les sources (une ligne JSON),
    puis la réponse morceau par morceau, au format NDJSON (une ligne = un événement).
    Permet d'afficher la réponse au fil de sa génération côté interface, pour une
    perception de vitesse nettement meilleure."""
    if assistant is None:
        raise HTTPException(status_code=503, detail="Assistant non initialisé.")
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide.")

    history = [{"role": m.role, "content": m.content} for m in (request.history or [])]

    def event_generator():
        for event in assistant.ask_stream(request.question, chat_history=history):
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


class FeedbackRequest(BaseModel):
    question: str
    answer: str
    feedback: str  # "up" ou "down"


@app.post("/feedback")
def feedback(request: FeedbackRequest) -> dict:
    if request.feedback not in ("up", "down"):
        raise HTTPException(status_code=400, detail="feedback doit être 'up' ou 'down'.")
    save_feedback(request.question, request.answer, request.feedback)
    return {"status": "ok"}


@app.get("/feedback/stats")
def feedback_stats() -> dict:
    return get_feedback_stats()
