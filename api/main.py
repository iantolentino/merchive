import os
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database import supabase
    from telegram_logic import stream_telegram_file, client, ensure_connected, CHANNEL_ID
except ImportError:
    from api.database import supabase
    from api.telegram_logic import stream_telegram_file, client, ensure_connected, CHANNEL_ID

app = FastAPI(title="Merchive Engine")

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

        # DEFAULT START (For Mobile Probes)
        start = 0
        if range_header:
            range_str = range_header.replace("bytes=", "")
            start = int(range_str.split("-")[0])
        
        # 2MB chunks are safer for mobile data stability
        chunk_size = 2 * 1024 * 1024 
        end = min(start + chunk_size, file_size - 1)
        content_length = (end - start) + 1
        
        # CRITICAL HEADERS FOR MOBILE SAFARI
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": "video/mp4",
        }

        return StreamingResponse(
            stream_telegram_file(m_id, offset=start, limit=content_length),
            status_code=206,
            headers=headers
        )
    except Exception as e:
        logger.error(f"Mobile Stream Fail: {e}")
        return HTTPException(status_code=500)

@app.get("/api/videos/list")
async def list_videos():
    response = supabase.table("videos").select("*").order("created_at", desc=True).execute()
    return {"status": "success", "data": response.data}

@app.get("/")
async def read_index():
    public_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    return FileResponse(os.path.join(public_path, "index.html"))

PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
if os.path.exists(PUBLIC_DIR):
    app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")