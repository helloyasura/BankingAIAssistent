import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class SqliteLongTermMemoryStore:
    """File-backed store for session facts and conversation summaries."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS session_summaries (
                    session_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (session_id)
                );
                CREATE TABLE IF NOT EXISTS session_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    fact TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def get_context(self, session_id: str, *, max_facts: int = 5) -> str:
        with self._connect() as conn:
            summary_row = conn.execute(
                "SELECT summary FROM session_summaries WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            facts = conn.execute(
                """
                SELECT fact FROM session_facts
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, max_facts),
            ).fetchall()

        parts: list[str] = []
        if summary_row:
            parts.append(f"Previous conversation summary: {summary_row['summary']}")
        if facts:
            fact_lines = "\n".join(f"- {row['fact']}" for row in reversed(facts))
            parts.append(f"Known session facts:\n{fact_lines}")
        return "\n\n".join(parts)

    def save_summary(self, session_id: str, summary: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO session_summaries (session_id, summary, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    summary = excluded.summary,
                    updated_at = excluded.updated_at
                """,
                (session_id, summary, now),
            )

    def add_fact(self, session_id: str, fact: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO session_facts (session_id, fact, created_at) VALUES (?, ?, ?)",
                (session_id, fact, now),
            )
