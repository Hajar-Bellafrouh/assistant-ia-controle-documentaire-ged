"""
Module de stockage des retours utilisateurs (feedback 👍/👎).

Rôle :
- Créer/gérer une base SQLite légère stockant chaque retour donné sur une réponse
- Permettre un suivi objectif de la qualité perçue de l'assistant dans le temps

Base stockée dans feedback.db à la racine du projet (ignorée par git, voir
.gitignore — c'est une donnée d'usage locale, pas du code).
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "feedback.db"


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            feedback TEXT NOT NULL CHECK (feedback IN ('up', 'down')),
            created_at TEXT NOT NULL
        )
        """
    )
    return conn


def save_feedback(question: str, answer: str, feedback: str) -> None:
    """Enregistre un retour utilisateur (feedback = 'up' ou 'down')."""
    conn = _get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO feedback (question, answer, feedback, created_at) "
                "VALUES (?, ?, ?, ?)",
                (question, answer, feedback, datetime.now(timezone.utc).isoformat()),
            )
    finally:
        conn.close()


def get_feedback_stats() -> dict:
    """Retourne le nombre total de 👍 et de 👎 enregistrés."""
    conn = _get_connection()
    try:
        cur = conn.execute("SELECT feedback, COUNT(*) FROM feedback GROUP BY feedback")
        rows = dict(cur.fetchall())
    finally:
        conn.close()
    return {"up": rows.get("up", 0), "down": rows.get("down", 0)}


def get_negative_feedback(limit: int = 50) -> list[dict]:
    """Retourne les derniers retours négatifs (👎), utile pour identifier les
    questions à améliorer en priorité (corpus, prompt...)."""
    conn = _get_connection()
    try:
        cur = conn.execute(
            "SELECT question, answer, created_at FROM feedback "
            "WHERE feedback = 'down' ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {"question": q, "answer": a, "created_at": c} for q, a, c in rows
    ]
