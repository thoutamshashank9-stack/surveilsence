import os
import bcrypt
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.core.security import get_current_user, get_api_key

logger = structlog.get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Admin credentials from environment
# ---------------------------------------------------------------------------
# Default verified bcrypt hash for the password 'admin'
_DEFAULT_ADMIN_HASH = "$2b$12$SGSVxGhbv6IVMgOCINiz..Pg6L8H5oCXpaYerTyMo8xd0c7jcXZ96"

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")

if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
    ADMIN_USERNAME = ADMIN_USERNAME or "admin"
    ADMIN_PASSWORD_HASH = ADMIN_PASSWORD_HASH or _DEFAULT_ADMIN_HASH
    logger.warning(
        "ADMIN_USERNAME and/or ADMIN_PASSWORD_HASH not set — using defaults "
        "(username='admin', password='admin'). Change these for production."
    )


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash with fallback."""
    try:
        # bcrypt checkpw requires bytes
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), 
            hashed_password.encode("utf-8")
        )
    except Exception:
        # Fallback to plain-text check if hash is plain-text or invalid format
        return plain_password == hashed_password


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login", summary="Login token provider")
async def login(payload: LoginRequest):
    """Authenticate with username/password and receive an API key."""
    if payload.username != ADMIN_USERNAME or not _verify_password(
        payload.password, ADMIN_PASSWORD_HASH
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    return {
        "access_token": get_api_key(),
        "token_type": "bearer",
    }


@router.get("/me", summary="Get current logged in user details")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user
