import sqlite3
import uuid
from datetime import datetime, timezone

from mcp_memory.models import Memory

DB_PATH = "momories.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            memory_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_memory(title: str, content: str, tags: list[str] | None = None) -> Memory:
    memory_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    tags = tags or []

    conn = _connect()
    conn.execute(
        "INSERT INTO memories (memory_id, title, content, tags, created_at) VALUES (?, ?, ?, ?, ?)",
        (memory_id, title, content, ",".join(tags), created_at),
    )
    conn.commit()
    conn.close()
    return Memory(
        memory_id=memory_id,
        title=title,
        content=content,
        tags=tags,
        created_at=datetime.fromisoformat(created_at),
    )


def fetch_memory(memory_id: str) -> Memory | None:
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM memories WHERE memory_id = ?", (memory_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return _row_to_memory(row)


def search_memories(query: str) -> list[Memory]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM memories WHERE title LIKE ? OR content LIKE ? OR tags LIKE ?",
        (f"%{query}%", f"%{query}%", f"%{query}%"),
    ).fetchall()
    conn.close()

    return [_row_to_memory(row) for row in rows]


def _row_to_memory(row: sqlite3.Row) -> Memory:
    tags_raw = row["tags"]
    return Memory(
        memory_id=row["memory_id"],
        title=row["title"],
        content=row["content"],
        tags=tags_raw.split(",") if tags_raw else [],
        created_at=row["created_at"],
    )
