import os
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

ADMIN_SECRET = os.getenv("ADMIN_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=24)) -> str:
    """Generates a JWT token valid for 24 hours."""
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def verify_admin(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """Dependency to verify the JWT token and ensure the user is an Admin."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        role: str = payload.get("role")
        if role != "admin":
            logger.warning("Unauthorized access attempt: Role is not admin.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Expired token used.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        logger.error("Invalid token used.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")