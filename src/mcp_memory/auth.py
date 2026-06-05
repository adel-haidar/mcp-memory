import secrets
import base64
import hashlib
import os
from datetime import datetime, timedelta, timezone
from mcp_memory.repository import _connect


SECRET_KEY = os.environ.get("SECRET_KEY", "")


def generate_token() -> str:
    return secrets.token_urlsafe(48)


def generate_client_secret() -> str:
    return secrets.token_urlsafe(32)


def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    digest = hashlib.sha256(code_verifier.encode()).digest()
    computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return computed == code_challenge


def create_oauth_tables():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS oauth_clients (
            client_id TEXT PRIMARY KEY,
            client_secret TEXT,
            redirect_uris TEXT[] NOT NULL,
            client_name TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS oauth_codes (
            code TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            code_challenge TEXT NOT NULL,
            code_challenge_method TEXT DEFAULT 'S256',
            redirect_uri TEXT NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            used BOOLEAN DEFAULT FALSE
        );
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            token TEXT PRIMARY KEY,
            token_type TEXT NOT NULL,
            client_id TEXT NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            refresh_token TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


def register_client(client_name: str, redirect_uris: list[str]) -> dict:
    client_id = secrets.token_urlsafe(16)
    client_secret = generate_client_secret()
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO oauth_clients (client_id, client_secret, redirect_uris, client_name) VALUES (%s, %s, %s, %s)",
        (client_id, client_secret, redirect_uris, client_name),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"client_id": client_id, "client_secret": client_secret}


def create_auth_code(client_id: str, code_challenge: str, redirect_uri: str) -> str:
    code = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO oauth_codes (code, client_id, code_challenge, redirect_uri, expires_at) VALUES (%s, %s, %s, %s, %s)",
        (code, client_id, code_challenge, redirect_uri, expires_at),
    )
    conn.commit()
    cur.close()
    conn.close()
    return code


def exchange_code(code: str, code_verifier: str, client_id: str) -> dict | None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT code_challenge, redirect_uri, expires_at, used FROM oauth_codes WHERE code = %s AND client_id = %s",
        (code, client_id),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return None

    code_challenge, redirect_uri, expires_at, used = row

    if used or datetime.now(timezone.utc) > expires_at:
        cur.close()
        conn.close()
        return None

    if not verify_pkce(code_verifier, code_challenge):
        cur.close()
        conn.close()
        return None

    # Mark code as used
    cur.execute("UPDATE oauth_codes SET used = TRUE WHERE code = %s", (code,))

    # Create tokens
    access_token = generate_token()
    refresh_token = generate_token()
    access_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    refresh_expires = datetime.now(timezone.utc) + timedelta(days=90)

    cur.execute(
        "INSERT INTO oauth_tokens (token, token_type, client_id, expires_at, refresh_token) VALUES (%s, %s, %s, %s, %s)",
        (access_token, "access", client_id, access_expires, refresh_token),
    )
    cur.execute(
        "INSERT INTO oauth_tokens (token, token_type, client_id, expires_at) VALUES (%s, %s, %s, %s)",
        (refresh_token, "refresh", client_id, refresh_expires),
    )
    conn.commit()
    cur.close()
    conn.close()

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": refresh_token,
    }


def refresh_access_token(refresh_token: str, client_id: str) -> dict | None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT expires_at FROM oauth_tokens WHERE token = %s AND token_type = 'refresh' AND client_id = %s",
        (refresh_token, client_id),
    )
    row = cur.fetchone()
    if not row or datetime.now(timezone.utc) > row[0]:
        cur.close()
        conn.close()
        return None

    access_token = generate_token()
    access_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    cur.execute(
        "INSERT INTO oauth_tokens (token, token_type, client_id, expires_at, refresh_token) VALUES (%s, %s, %s, %s, %s)",
        (access_token, "access", client_id, access_expires, refresh_token),
    )
    conn.commit()
    cur.close()
    conn.close()

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": refresh_token,
    }


def validate_token(token: str) -> str | None:
    """Returns client_id if valid, None otherwise."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT client_id, expires_at FROM oauth_tokens WHERE token = %s AND token_type = 'access'",
        (token,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row or datetime.now(timezone.utc) > row[1]:
        return None
    return row[0]
