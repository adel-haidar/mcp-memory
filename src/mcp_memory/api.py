from mcp_memory.repository import save_memory
from fastapi import FastAPI, UploadFile
import os
import hashlib
import datetime

app = FastAPI()

UPLOAD_DIR = "/home/ec2-user/mcp-memory/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/file")
async def upload_file(file: UploadFile):
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
