from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.core.security import get_current_user, DEV_API_KEY

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login", summary="Login token provider")
async def login(payload: LoginRequest):
    """accepts any login in dev mode, returns the dev access token."""
    return {
        "access_token": DEV_API_KEY,
        "token_type": "bearer"
    }

@router.get("/me", summary="Get current logged in user details")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user
