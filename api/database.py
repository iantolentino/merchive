import os
from supabase import create_client, Client
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("CRITICAL: Supabase credentials missing in .env file.")

try:
    # Initialize the Supabase client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Supabase client initialized successfully.")
except Exception as e:
    logger.exception(f"Failed to initialize Supabase client: {e}")
    supabase = None