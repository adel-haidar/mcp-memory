from mcp_memory.repository import save_memory
from mcp_memory.auth import (
    create_auth_code,
    exchange_code,
    refresh_access_token,
    register_client,
    validate_token,
)
from mcp_memory.models import RegisterRequest
from fastapi import FastAPI, UploadFile, Form, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
import os
import hashlib
import datetime

app = FastAPI()

UPLOAD_DIR = "/home/ec2-user/mcp-memory/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def require_auth(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    token = auth[7:]
    client_id = validate_token(token)
    if not client_id:
        raise HTTPException(status_code=401, detail="invalid token")
    return client_id


@app.get("/.well-known/oauth-protected-resource")
async def get_well_known():
    return {
        "resource": "https://adel-intelligence.com",
        "authorization_servers": ["https://adel-intelligence.com"],
    }


@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server():
    return {
        "issuer": "https://adel-intelligence.com",
        "authorization_endpoint": "https://adel-intelligence.com/oauth/authorize",
        "token_endpoint": "https://adel-intelligence.com/oauth/token",
        "registration_endpoint": "https://adel-intelligence.com/oauth/register",
        "code_challenge_methods_supported": ["S256"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
    }


@app.post("/oauth/register")
async def register(body: RegisterRequest):
    result = register_client(
        client_name=body.client_name, redirect_uris=body.redirect_uris
    )
    return {"client_id": result["client_id"], "client_secret": result["client_secret"]}


@app.get("/oauth/authorize")
async def authorize(
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    code_challenge_method: str,
    state: str = "",
):
    code = create_auth_code(
        client_id=client_id,
        code_challenge=code_challenge,
        redirect_uri=redirect_uri,
    )
    return RedirectResponse(url=f"{redirect_uri}?code={code}&state={state}")


@app.post("/oauth/token")
async def token(
    grant_type: str = Form(),
    code: str = Form(""),
    code_verifier: str = Form(""),
    client_id: str = Form(""),
    client_secret: str = Form(""),
    refresh_token: str = Form(""),
):
    if grant_type == "authorization_code":
        result = exchange_code(
            code=code, code_verifier=code_verifier, client_id=client_id
        )
    elif grant_type == "refresh_token":
        result = refresh_access_token(refresh_token=refresh_token, client_id=client_id)
    else:
        raise HTTPException(status_code=400, detail="unsupported_grant_type")

    if not result:
        raise HTTPException(status_code=400, detail="invalid_grant")

    return result


@app.post("/file")
async def upload_file(file: UploadFile, client_id: str = Depends(require_auth)):
    content = await file.read()

    if not content:
        return {"error": "Empty file"}

    file_hash = hashlib.sha256(content).hexdigest()[:12]
    timestamp = datetime.datetime.now().isoformat()
    filename = f"{file_hash}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    saved = save_memory(
        title=f"Uploaded file: {file.filename}",
        content=(
            f"File uploaded at {timestamp}. "
            f"Path: {filepath}. Size: {len(content)} bytes. "
            f"Hash: {file_hash}."
        ),
        tags=["file-upload", file.filename.split(".")[-1]],
    )

    return {
        "status": "ok",
        "memory_id": saved.memory_id,
        "filename": filename,
        "size": len(content),
    }
