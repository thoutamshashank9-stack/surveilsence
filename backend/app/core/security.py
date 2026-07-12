import os
import hmac
import secrets

from fastapi import Header, HTTPException, status
from app.core.exceptions import AuthError

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# API Key initialisation — read from env or auto-generate a random key
# ---------------------------------------------------------------------------
_env_key = os.environ.get("API_SECRET_KEY", "")

if _env_key:
    _active_api_key: str = _env_key
else:
    _active_api_key = secrets.token_hex(16)  # 32-char hex string
    logger.warning(
        "API_SECRET_KEY not set — a random key has been generated. "
        "Set API_SECRET_KEY in your environment for production use.",
        generated_key=_active_api_key,
    )


def get_api_key() -> str:
    """Return the active API key."""
    return _active_api_key


async def get_current_user(
    x_api_key: str = Header(..., description="API Access Token"),
) -> dict:
    """Validate the supplied API key using a timing-safe comparison."""
    if not hmac.compare_digest(x_api_key, _active_api_key):
        raise AuthError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            error_code="UNAUTHORIZED",
        )
    return {"id": "admin", "username": "administrator", "role": "admin"}
