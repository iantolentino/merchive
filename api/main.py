import os
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from loguru import logger
from dotenv import load_dotenv
from pathlib import Path

# --- PATH SETUP & ENV VARS ---
# Added absolute path calculation to ensure Railway finds the correct 'public' folder
BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"

dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)

ADMIN_SECRET = os.getenv("ADMIN_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET") 

# --- MODULE RESOLUTION ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database import supabase
    from telegram_logic import stream_telegram_file, client, ensure_connected, CHANNEL_ID
except ImportError:
    from api.database import supabase
    from api.telegram_logic import stream_telegram_file, client, ensure_connected, CHANNEL_ID

app = FastAPI(title="Merchive Engine")

# --- DATA MODELS ---
class LoginRequest(BaseModel):
    password: str

class VideoRequest(BaseModel):
    title: str
    category: str
    tg_file_ids: list
    is_private: bool

# --- PAGE ROUTING (With Cache-Busting Headers) ---
@app.get("/")
async def read_index():
    # Cache-Control headers force the browser to check for new versions
    return FileResponse(
        str(PUBLIC_DIR / "index.html"),
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
    )

@app.get("/login")
async def read_login():
    return FileResponse(str(PUBLIC_DIR / "login.html"))

@app.get("/admin")
async def read_admin():
    return FileResponse(str(PUBLIC_DIR / "admin.html"))

@app.get("/player")
async def read_player():
    return FileResponse(str(PUBLIC_DIR / "player.html"))

# --- API CORE & AUTH ---
@app.post("/api/auth/login")
async def login(req: LoginRequest):
    if req.password == ADMIN_SECRET: 
        return {"access_token": "authorized_admin_token"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/api/videos/add")
async def add_video(req: VideoRequest, request: Request):
    token = request.headers.get('Authorization')
    if not token or token != "Bearer authorized_admin_token":
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    data = {
        "title": req.title,
        "category": req.category,
        "tg_file_ids": req.tg_file_ids,
        "is_private": req.is_private
    }
    response = supabase.table("videos").insert(data).execute()
    return {"status": "success", "data": response.data}

@app.get("/api/videos/list")
async def list_videos():
    response = supabase.table("videos").select("*").order("created_at", desc=True).execute()
    return {"status": "success", "data": response.data}

@app.get("/api/video/stream/{message_id}")
async def video_stream(message_id: str, request: Request):
    try:
        await ensure_connected()
        m_id = int(message_id)
        target = int(CHANNEL_ID) if str(CHANNEL_ID).startswith('-100') else CHANNEL_ID
        
        message = await client.get_messages(target, ids=m_id)
        if not message or not message.media:
            raise HTTPException(status_code=404, detail="Video not found")

        file_size = message.media.document.size
        range_header = request.headers.get("range")

        start = 0
        end = file_size - 1

        if range_header:
            range_str = range_header.replace("bytes=", "")
            parts = range_str.split("-")
            start = int(parts[0]) if parts[0] else 0
            if len(parts) > 1 and parts[1]:
                end = int(parts[1])

        chunk_size = 2 * 1024 * 1024 
        end = min(start + chunk_size - 1, end, file_size - 1)
        
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
    except Exception as e:
        logger.error(f"Stream Fail: {e}")
        return HTTPException(status_code=500, detail="Internal Server Error")

# --- STATIC ASSETS ---
# Using the calculated PUBLIC_DIR ensures the mount always points to the right place
app.mount("/public", StaticFiles(directory=str(PUBLIC_DIR)), name="public")