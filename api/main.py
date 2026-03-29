import os
import asyncio
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
    # IMPORTING CHANNEL_ID HERE FIXES THE NAMEERROR
    from api.telegram_logic import stream_telegram_file, client, ensure_connected, CHANNEL_ID
except ImportError:
    from database import supabase
    from models import LoginRequest, TokenResponse
    from auth import ADMIN_SECRET, create_access_token, verify_admin
    from telegram_logic import stream_telegram_file, client, ensure_connected, CHANNEL_ID

BASE_DIR = os.getcwd()
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
    try:
        await ensure_connected()
        logger.info(f"✅ TELEGRAM_CONNECTION: SUCCESS (Channel: {CHANNEL_ID})")
    except Exception as e:
        logger.error(f"❌ STARTUP_ERROR: {e}")

# --- PUBLIC LIST & STREAM ---
@app.get("/api/videos/list")
async def list_videos():
    try:
        response = supabase.table("videos").select("id, title, tg_file_ids, category, subtitle_url").execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        logger.error(f"LIST_ERROR: {e}")
        return {"status": "error", "data": []}

@app.get("/api/video/stream/{message_id}")
async def video_stream(message_id: str, request: Request):
    try:
        await ensure_connected()
        target = int(CHANNEL_ID) if str(CHANNEL_ID).startswith('-100') else CHANNEL_ID
        message = await client.get_messages(target, ids=int(message_id))
        
        if not message or not message.media:
            raise HTTPException(status_code=404, detail="Video not found")

        file_size = message.media.document.size
        range_header = request.headers.get("range")

        # HANDLE RANGE REQUESTS (Status 206)
        if range_header:
            range_str = range_header.replace("bytes=", "")
            parts = range_str.split("-")
            start = int(parts[0])
            # Set a chunk size (2MB) so Vercel doesn't time out on long downloads
            chunk_size = 2 * 1024 * 1024 
            end = int(parts[1]) if (len(parts) > 1 and parts[1]) else min(start + chunk_size, file_size - 1)
            
            content_length = (end - start) + 1
            
            return StreamingResponse(
                stream_telegram_file(message_id, offset=start, limit=content_length),
                status_code=206,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(content_length),
                    "Content-Type": "video/mp4",
                }
            )

        # FULL STREAM FALLBACK (Status 200)
        return StreamingResponse(
            stream_telegram_file(message_id),
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
                "Content-Type": "video/mp4",
            }
        )
    except Exception as e:
        logger.error(f"STREAM_INIT_ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- PAGE ROUTES ---
@app.get("/")
async def read_index():
    return FileResponse(os.path.join(PUBLIC_PATH, "index.html"))

@app.get("/login")
async def get_login_page():
    return FileResponse(os.path.join(PUBLIC_PATH, "login.html"))

@app.get("/admin")
async def get_admin_page():
    return FileResponse(os.path.join(PUBLIC_PATH, "admin.html"))

if os.path.exists(PUBLIC_PATH):
    app.mount("/static", StaticFiles(directory=PUBLIC_PATH), name="static")