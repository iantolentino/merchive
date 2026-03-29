import os
import asyncio
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
from loguru import logger

# --- INTERNAL IMPORTS ---
# Vercel needs the 'api.' prefix when running as a deployed function
try:
    from api.database import supabase
    from api.models import LoginRequest, TokenResponse
    from api.auth import ADMIN_SECRET, create_access_token, verify_admin
    from api.telegram_logic import stream_telegram_file, client, ensure_connected
except ImportError:
    # Fallback for local development
    from database import supabase
    from models import LoginRequest, TokenResponse
    from auth import ADMIN_SECRET, create_access_token, verify_admin
    from telegram_logic import stream_telegram_file, client, ensure_connected

# --- SETUP PATHS ---
# os.getcwd() is the most reliable way to find the root on Vercel
BASE_DIR = os.getcwd()
PUBLIC_PATH = os.path.join(BASE_DIR, "public")

class VideoCreate(BaseModel):
    title: str
    category: str
    tg_file_ids: List[str]
    subtitle_url: str = None
    is_private: bool = False

app = FastAPI(title="Project Vesta // MC")

@app.on_event("startup")
async def startup_event():
    try:
        # Calls the function from telegram_logic.py
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
    try:
        response = supabase.table("videos").select("id, title, tg_file_ids, category").execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        logger.error(f"LIST_ERROR: {e}")
        return {"status": "error", "data": []}

@app.get("/api/video/stream/{message_id}")
async def video_stream(message_id: str, request: Request):
    try:
        # Re-verify connection for the stream request
        await ensure_connected()

        async def file_generator():
            # 1. Heartbeat: Keeps Vercel connection alive during initial Telegram handshake
            yield b"" 
            
            try:
                async for chunk in stream_telegram_file(message_id):
                    if chunk:
                        yield chunk
            except Exception as e:
                logger.error(f"Stream Generator Error: {e}")

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
        raise HTTPException(status_code=500, detail="Stream Connection Failed")

# --- PAGE ROUTES ---
@app.get("/")
async def read_index():
    path = os.path.join(PUBLIC_PATH, "index.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "index.html not found", "checked_path": path}

@app.get("/login")
async def get_login_page():
    return FileResponse(os.path.join(PUBLIC_PATH, "login.html"))

@app.get("/admin")
async def get_admin_page():
    return FileResponse(os.path.join(PUBLIC_PATH, "admin.html"))

# Mount static files (for your /css and /js folders)
if os.path.exists(PUBLIC_PATH):
    app.mount("/static", StaticFiles(directory=PUBLIC_PATH), name="static")