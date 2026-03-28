import os
from fastapi import FastAPI, HTTPException, Depends
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

# --- Setup Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_PATH = os.path.join(BASE_DIR, "public")

class VideoCreate(BaseModel):
    title: str
    category: str
    tg_file_ids: List[str]
    is_private: bool = False

app = FastAPI(title="Project Vesta // MC")

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing MC Dashboard (Bot Mode)...")
    try:
        if not client.is_connected():
            await client.start(bot_token=BOT_TOKEN)
        logger.info("✅ TELEGRAM_BOT: ONLINE.")
    except Exception as e:
        logger.error(f"❌ STARTUP_ERROR: {e}")

# --- AUTH ROUTES ---
@app.post("/api/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    if req.password != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"role": "admin"})
    return {"access_token": token, "token_type": "bearer"}

# --- ADMIN CRUD ROUTES ---
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
async def video_stream(message_id: str):
    async def file_generator():
        async for chunk in stream_telegram_file(message_id):
            yield chunk
    return StreamingResponse(file_generator(), media_type="video/mp4")

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