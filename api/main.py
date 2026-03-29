import os
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

# --- MODULE RESOLUTION ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database import supabase
    from telegram_logic import stream_telegram_file, client, ensure_connected, CHANNEL_ID
except ImportError:
    from api.database import supabase
    from api.telegram_logic import stream_telegram_file, client, ensure_connected, CHANNEL_ID

app = FastAPI(title="Merchive Engine")

# --- PAGE ROUTING ---
# We must define these so Railway knows which file to show for each URL

@app.get("/")
async def read_index():
    return FileResponse("public/index.html")

@app.get("/login")
async def read_login():
    return FileResponse("public/login.html")

@app.get("/admin")
async def read_admin():
    # Note: You should eventually add logic here to check if the user is logged in
    return FileResponse("public/admin.html")

@app.get("/player")
async def read_player():
    return FileResponse("public/player.html")

# --- API CORE ---

@app.get("/api/video/stream/{message_id}")
async def video_stream(message_id: str, request: Request):
    try:
        await ensure_connected()
        m_id = int(message_id)
        target = int(CHANNEL_ID) if str(CHANNEL_ID).startswith('-100') else CHANNEL_ID
        
        message = await client.get_messages(target, ids=m_id)
        if not message or not message.media:
            raise HTTPException(status_code=404)

        file_size = message.media.document.size
        range_header = request.headers.get("range")

        start = 0
        if range_header:
            range_str = range_header.replace("bytes=", "")
            start = int(range_str.split("-")[0])
        
        chunk_size = 2 * 1024 * 1024 
        end = min(start + chunk_size, file_size - 1)
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
        return HTTPException(status_code=500)

@app.get("/api/videos/list")
async def list_videos():
    response = supabase.table("videos").select("*").order("created_at", desc=True).execute()
    return {"status": "success", "data": response.data}

# --- STATIC ASSETS ---
# This serves your CSS and JS files from /public/css and /public/js
app.mount("/public", StaticFiles(directory="public"), name="public")
