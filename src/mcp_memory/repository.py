import uuid
import os
import psycopg2
import json
import boto3
from datetime import datetime, timezone
from psycopg2.extras import RealDictCursor
from typing import Any, Mapping

from mcp_memory.models import Memory

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
_bedrock = boto3.client("bedrock-runtime", region_name="eu-central-1")


def _connect():
    conn = psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    return conn


def _get_embedding(text: str) -> list[float]:
    response = _bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps({"inputText": text}),
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def init_db() -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            memory_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL,
            embedding vector(1024)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def save_memory(title: str, content: str, tags: list[str] | None = None) -> Memory:
    memory_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)
    tags = tags or []
    text = f"{title}\n{content}"
    embedding = _get_embedding(text)
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO memories (memory_id, title, content, tags, created_at, embedding)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (memory_id, title, content, ",".join(tags), created_at, str(embedding)),
    )
    conn.commit()
    cur.close()
    conn.close()

    return Memory(
        memory_id=memory_id,
        title=title,
        content=content,
        tags=tags,
        created_at=created_at,
    )


def fetch_memory(memory_id: str) -> Memory | None:
    conn = _connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM memories WHERE memory_id = %s", (memory_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        return None

    return _row_to_memory(row)


def search_memories(query: str) -> list[Memory]:
    embedding = _get_embedding(query)

    conn = _connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """SELECT *, embedding <=> %s AS distance
           FROM memories
           ORDER BY distance
           LIMIT 5""",
        (str(embedding),),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [_row_to_memory(row) for row in rows]


def _row_to_memory(row: Mapping[str, Any]) -> Memory:
    tags_raw = row["tags"]
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
    return Memory(
        memory_id=row["memory_id"],
        title=row["title"],
        content=row["content"],
        tags=tags,
        created_at=row["created_at"],
    )
