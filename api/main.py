from fastapi import FastAPI, HTTPException, Depends
from loguru import logger
from api.database import supabase
from api.models import LoginRequest, TokenResponse
from api.auth import ADMIN_SECRET, create_access_token, verify_admin
from fastapi.responses import StreamingResponse, FileResponse
from api.telegram_logic import stream_telegram_file
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List

# --- Models ---
class VideoCreate(BaseModel):
    title: str
    category: str
    tg_file_ids: List[str]
    is_private: bool = False

# --- Initialize FastAPI ---
app = FastAPI(title="Project Vesta API", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Project Vesta API...")

# --- Authentication Routes ---

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Validates the admin secret and returns a JWT."""
    if req.password != ADMIN_SECRET:
        logger.warning("Failed login attempt: Incorrect Admin Secret.")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={"role": "admin"})
    logger.info("Admin logged in successfully.")
    return {"access_token": token, "token_type": "bearer"}

# --- Video Data Routes (CRUD) ---

@app.get("/api/videos/list")
async def list_videos(admin_data: dict = Depends(verify_admin)):
    """Fetches all video metadata from Supabase."""
    try:
        response = supabase.table("videos").select("id, title, tg_file_ids, category").execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        logger.error(f"Supabase Query Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/videos/add")
async def add_video(video: VideoCreate, admin_data: dict = Depends(verify_admin)):
    """Adds a new video entry to Supabase."""
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
        logger.error(f"Failed to add video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/videos/{video_id}")
async def delete_video(video_id: str, admin_data: dict = Depends(verify_admin)):
    """Removes a video entry from Supabase."""
    try:
        supabase.table("videos").delete().eq("id", video_id).execute()
        return {"status": "success", "message": "Video deleted"}
    except Exception as e:
        logger.error(f"Failed to delete video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Streaming Routes ---

@app.get("/api/video/stream/{message_id}")
async def video_stream(message_id: str):
    """Streams video chunks directly from Telegram to the browser."""
    async def file_generator():
        async for chunk in stream_telegram_file(message_id):
            yield chunk

    return StreamingResponse(
        file_generator(),
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Type": "video/mp4",
            "Content-Disposition": "inline",
            "Cache-Control": "no-cache",
        }
    )

# --- System & Page Routes ---

@app.get("/api/system/db-check")
async def check_db(admin_data: dict = Depends(verify_admin)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database client not initialized.")
    try:
        response = supabase.table("videos").select("id").limit(1).execute()
        return {"status": "success", "message": "Connected to Supabase", "data": response.data}
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection error.")

@app.get("/admin")
async def get_admin_page():
    """Serves the Admin Panel."""
    return FileResponse("public/admin.html")

@app.get("/login")
async def get_login_page():
    """Serves the Login Page."""
    return FileResponse("public/login.html")

@app.get("/")
async def read_index():
    """Serves the main Archive Gallery."""
    return FileResponse("public/index.html")

# --- Static Files (MUST BE LAST) ---
app.mount("/", StaticFiles(directory="public"), name="static")