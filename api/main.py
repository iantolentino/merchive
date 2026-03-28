from fastapi import FastAPI, HTTPException, Depends
from loguru import logger
from api.database import supabase
from api.models import LoginRequest, TokenResponse
from api.auth import ADMIN_SECRET, create_access_token, verify_admin
from fastapi.responses import StreamingResponse
from api.telegram_logic import stream_telegram_file

# Initialize FastAPI
app = FastAPI(title="Project Vesta API", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Project Vesta API...")

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Validates the admin secret and returns a JWT."""
    if req.password != ADMIN_SECRET:
        logger.warning("Failed login attempt: Incorrect Admin Secret.")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={"role": "admin"})
    logger.info("Admin logged in successfully.")
    return {"access_token": token, "token_type": "bearer"}

@app.get("/api/system/db-check")
async def check_db(admin_data: dict = Depends(verify_admin)):
    """
    Protected endpoint to test the Supabase DB connection.
    Requires a valid Admin JWT token.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database client not initialized.")
    try:
        # Simple query to check if the videos table is accessible
        response = supabase.table("videos").select("id").limit(1).execute()
        logger.info("Database connection test passed.")
        return {"status": "success", "message": "Connected to Supabase", "data": response.data}
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection error.")
    
    
@app.get("/api/video/stream/{message_id}")
async def video_stream(message_id: str):
    """
    This endpoint acts as the video source for the browser player.
    """
    return StreamingResponse(
        stream_telegram_file(message_id),
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Type": "video/mp4",
        }
    )