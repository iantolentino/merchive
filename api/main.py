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
    from api.telegram_logic import stream_telegram_file, client, ensure_connected, CHANNEL_ID
except ImportError:
    from database import supabase
    from models import LoginRequest, TokenResponse
    from auth import ADMIN_SECRET, create_access_token, verify_admin
    from telegram_logic import stream_telegram_file, client, ensure_connected, CHANNEL_ID

# --- SETUP PATHS ---
# Using path detection that works for both Vercel and Railway
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
    try:
        await ensure_connected()
        logger.info("✅ TELEGRAM_CONNECTION: SUCCESS")
    except Exception as e:
        logger.error(f"❌ STARTUP_ERROR: {e}")

# --- AUTH & ADMIN ROUTES ---
@app.post("/api/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    if req.password != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"role": "admin"})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/api/videos/add")
async def add_video(video: VideoCreate, admin_data: dict = Depends(verify_admin)):
    try:
        data = {
            "title": video.title,
            "category": video.category,
            "tg_file_ids": video.tg_file_ids,
            "is_private": video.is_private,
            "subtitle_url": video.subtitle_url
        }
        response = supabase.table("videos").insert(data).execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        logger.error(f"ADD_VIDEO_FAILED: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/videos/{video_id}")
async def delete_video(video_id: str, admin_data: dict = Depends(verify_admin)):
    try:
        supabase.table("videos").delete().eq("id", video_id).execute()
        return {"status": "success", "message": "DELETED"}
    except Exception as e:
        logger.error(f"DELETE_FAILED: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- PUBLIC LIST & STREAM ---
@app.get("/api/videos/list")
async def list_videos():
    try:
        response = supabase.table("videos").select("*").execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        logger.error(f"LIST_ERROR: {e}")
        return {"status": "error", "data": []}

@app.get("/api/video/stream/{message_id}")
async def video_stream(message_id: str, request: Request):
    try:
        await ensure_connected()
        
        # 1. Clean ID and get Metadata
        m_id = int(message_id)
        target = int(CHANNEL_ID) if str(CHANNEL_ID).startswith('-100') else CHANNEL_ID
        message = await client.get_messages(target, ids=m_id)
        
        if not message or not message.media:
            raise HTTPException(status_code=404, detail="Video not found")

        file_size = message.media.document.size
        range_header = request.headers.get("range")

        # 2. Byte-Range Handling (The Fix for Smooth Playback & Seeking)
        if range_header:
            range_str = range_header.replace("bytes=", "")
            parts = range_str.split("-")
            start = int(parts[0])
            
            # Chunking prevents connection timeouts
            chunk_size = 1024 * 1024 # 1MB chunks
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
                    "Cache-Control": "no-cache",
                }
            )

        # 3. Standard Stream (Fallback)
        return StreamingResponse(
            stream_telegram_file(m_id),
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
                "Content-Type": "video/mp4",
                "Connection": "keep-alive",
            }
        )
    except Exception as e:
        logger.error(f"STREAM_ERROR for {message_id}: {e}")
        raise HTTPException(status_code=500, detail="Streaming connection failed")

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

# Mount static files (for your /css and /js folders)
if os.path.exists(PUBLIC_PATH):
    app.mount("/static", StaticFiles(directory=PUBLIC_PATH), name="static")