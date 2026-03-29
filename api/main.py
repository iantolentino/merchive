import os
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from loguru import logger

# --- INTERNAL IMPORTS ---
try:
    from api.database import supabase
    from api.models import LoginRequest, TokenResponse
    from api.auth import ADMIN_SECRET, create_access_token, verify_admin
    from api.telegram_logic import stream_telegram_file, client, ensure_connected, CHANNEL_ID
except ImportError:
    from database import supabase
    from models import LoginRequest, TokenResponse
    from auth import ADMIN_SECRET, create_access_token, verify_admin
    from telegram_logic import stream_telegram_file, client, ensure_connected, CHANNEL_ID

# --- SETUP ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_PATH = os.path.join(BASE_DIR, "public")

class VideoCreate(BaseModel):
    title: str
    category: str
    tg_file_ids: List[str]
    subtitle_url: Optional[str] = None
    is_private: bool = False

app = FastAPI(title="Project Vesta // MC")

@app.on_event("startup")
async def startup_event():
    await ensure_connected()
    logger.info("✅ VESTA CORE: ONLINE")

# --- STREAMING FIX ---
@app.get("/api/video/stream/{message_id}")
async def video_stream(message_id: str, request: Request):
    try:
        await ensure_connected()
        m_id = int(message_id)
        target = int(CHANNEL_ID) if str(CHANNEL_ID).startswith('-100') else CHANNEL_ID
        
        message = await client.get_messages(target, ids=m_id)
        if not message or not message.media:
            raise HTTPException(status_code=404, detail="File not found")

        file_size = message.media.document.size
        range_header = request.headers.get("range")

        # Handle the Byte-Range Request
        if range_header:
            range_str = range_header.replace("bytes=", "")
            parts = range_str.split("-")
            start = int(parts[0])
            
            # Requesting 1MB at a time keeps the connection "fresh"
            chunk_size = 1024 * 1024 
            end = int(parts[1]) if (len(parts) > 1 and parts[1]) else min(start + chunk_size, file_size - 1)
            content_length = (end - start) + 1
            
            return StreamingResponse(
                stream_telegram_file(m_id, offset=start, limit=content_length),
                status_code=206,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(content_length),
                    "Content-Type": "video/mp4",
                }
            )

        # Full stream fallback
        return StreamingResponse(
            stream_telegram_file(m_id),
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
                "Content-Type": "video/mp4",
            }
        )
    except Exception as e:
        logger.error(f"Stream Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- ROUTES ---
@app.get("/api/videos/list")
async def list_videos():
    response = supabase.table("videos").select("*").execute()
    return {"status": "success", "data": response.data}

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    if req.password != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"role": "admin"})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(PUBLIC_PATH, "index.html"))

if os.path.exists(PUBLIC_PATH):
    app.mount("/static", StaticFiles(directory=PUBLIC_PATH), name="static")