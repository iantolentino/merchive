from pydantic import BaseModel

class LoginRequest(BaseModel):
    """Schema for the Admin login payload."""
    password: str

class TokenResponse(BaseModel):
    """Schema for the JWT response."""
    access_token: str
    token_type: str