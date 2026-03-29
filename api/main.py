import os
import asyncio
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
from loguru import logger

# Internal Imports
from api.database import supabase
from api.models import LoginRequest, TokenResponse
from api.auth import ADMIN_SECRET, create_access_token, verify_admin
from api.telegram_logic import stream_telegram_file, client, BOT_TOKEN
from api.telegram_logic import stream_telegram_file, client, ensure_connected

# --- Setup Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_PATH = os.path.join(BASE_DIR, "public")

class VideoCreate(BaseModel):
    title: str
    category: str
    tg_file_ids: List[str]
    is_private: bool = False

app = FastAPI(title="Project Vesta // MC")

# --- BOT CONNECTION HELPER ---
async def ensure_connected():
    """Ensures the Telegram client is alive using the session logic."""
    if not client.is_connected():
        logger.info("Connecting to Telegram via Session...")
        # If SESSION_STRING is present, connect() is enough.
        # If not, it uses the local .session file.
        await client.connect() 
    return True

@app.on_event("startup")
async def startup_event():
    try:
        await ensure_connected()
        logger.info("✅ TELEGRAM_BOT: ONLINE.")
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
            "is_private": video.is_private
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
    response = supabase.table("videos").select("id, title, tg_file_ids, category").execute()
    return {"status": "success", "data": response.data}

@app.get("/api/video/stream/{message_id}")
async def video_stream(message_id: str, request: Request):
    try:
        # 1. Force connection check
        await ensure_connected()

        async def file_generator():
            # 1. Immediate Heartbeat to keep the connection open
            yield b"" 
            
            try:
                # 2. Get the stream
                async for chunk in stream_telegram_file(message_id):
                    if chunk:
                        yield chunk
            except Exception as e:
                logger.error(f"Generator Error: {e}")

        # 3. Add 'Accept-Ranges' to satisfy Chrome/Safari players
        return StreamingResponse(
            file_generator(),
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Type": "video/mp4",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except Exception as e:
        logger.error(f"STREAM_INIT_ERROR for {message_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Stream Error: {str(e)}")

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
