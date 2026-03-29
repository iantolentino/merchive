import os
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from loguru import logger

# --- PATH & IMPORT FIXES ---
# This line fixes the 'ModuleNotFoundError' on Railway
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database import supabase
    from models import LoginRequest, TokenResponse
    from auth import ADMIN_SECRET, create_access_token, verify_admin
    from telegram_logic import stream_telegram_file, client, ensure_connected, CHANNEL_ID
except ImportError:
    # Fallback for different directory structures
    from api.database import supabase
    from api.models import LoginRequest, TokenResponse
    from api.auth import ADMIN_SECRET, create_access_token, verify_admin
    from api.telegram_logic import stream_telegram_file, client, ensure_connected, CHANNEL_ID

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_PATH = os.path.join(BASE_DIR, "public")

app = FastAPI(title="Project Vesta // Railway")

@app.on_event("startup")
async def startup_event():
    await ensure_connected()
    logger.info("✅ VESTA CORE: ONLINE")

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

        # Byte-Range Logic for smooth seeking and long videos
        if range_header:
            range_str = range_header.replace("bytes=", "")
            parts = range_str.split("-")
            start = int(parts[0])
            
            # Requesting ~1.5MB chunks keeps the connection alive
            chunk_size = 1536 * 1024 
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
        raise HTTPException(status_code=500, detail="Internal Streaming Error")

@app.get("/api/videos/list")
async def list_videos():
    response = supabase.table("videos").select("*").execute()
    return {"status": "success", "data": response.data}

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(PUBLIC_PATH, "index.html"))

if os.path.exists(PUBLIC_PATH):
    app.mount("/static", StaticFiles(directory=PUBLIC_PATH), name="static")