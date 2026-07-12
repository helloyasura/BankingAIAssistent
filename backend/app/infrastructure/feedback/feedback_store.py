import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class FeedbackStore:
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_feedback (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    message_id TEXT,
                    rating INTEGER NOT NULL,
                    comment TEXT,
                    user_id TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    def save(
        self,
        *,
        session_id: str,
        rating: int,
        message_id: str | None = None,
        comment: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        feedback_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_feedback
                (id, session_id, message_id, rating, comment, user_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (feedback_id, session_id, message_id, rating, comment, user_id, now),
            )
        return {
            "id": feedback_id,
            "session_id": session_id,
            "message_id": message_id,
            "rating": rating,
            "comment": comment,
            "created_at": now,
        }
