from fastapi import Header, HTTPException, status
from app.core.exceptions import AuthError

DEV_API_KEY = "dev-secret-key-12345"

async def get_current_user(x_api_key: str = Header(..., description="API Access Token")) -> dict:
    if x_api_key != DEV_API_KEY:
        raise AuthError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            error_code="UNAUTHORIZED"
        )
    return {"id": "admin", "username": "administrator", "role": "admin"}
