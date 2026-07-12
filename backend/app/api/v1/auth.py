import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

import structlog

from app.core.security import get_current_user, get_api_key

logger = structlog.get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Bcrypt helper — graceful fallback if passlib/bcrypt not installed
# ---------------------------------------------------------------------------
_BCRYPT_AVAILABLE = False
try:
    from passlib.context import CryptContext

    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    _BCRYPT_AVAILABLE = True
except ImportError:
    try:
        import bcrypt as _bcrypt_mod  # noqa: F401
        from passlib.context import CryptContext

        _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        _BCRYPT_AVAILABLE = True
    except ImportError:
        logger.warning(
            "Neither passlib[bcrypt] nor bcrypt is installed — "
            "password verification will fall back to plain-text comparison. "
            "This is NOT safe for production."
        )

# ---------------------------------------------------------------------------
# Admin credentials from environment
# ---------------------------------------------------------------------------
# Default bcrypt hash for the password 'admin'
_DEFAULT_ADMIN_HASH = "$2b$12$LJ3m4ys3Lk0TSwHjmz0r5uKrhHf0E5JqFqBk1Q3sE7WJ0yMBqKWHm"

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")

if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
    ADMIN_USERNAME = ADMIN_USERNAME or "admin"
    # When no hash is provided, default password is "admin"
    ADMIN_PASSWORD_HASH = ADMIN_PASSWORD_HASH or _DEFAULT_ADMIN_HASH
    logger.warning(
        "ADMIN_USERNAME and/or ADMIN_PASSWORD_HASH not set — using defaults "
        "(username='admin', password='admin'). Change these for production."
    )


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored hash."""
    if _BCRYPT_AVAILABLE:
        try:
            return _pwd_ctx.verify(plain_password, hashed_password)
        except Exception:
            # Hash may be invalid / corrupted
            return False
    else:
        # Fallback: plain-text comparison (NOT safe for production)
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
