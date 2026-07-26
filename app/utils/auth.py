import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.api_key import ApiKey

KEY_PREFIX = "mmk_"


def generate_key() -> tuple[str, str, str]:
    """
    Generates a new API key.

    Returns (raw_key, key_hash, key_prefix). Only key_hash is persisted —
    raw_key is returned to the caller exactly once and never stored.
    """
    raw_key = f"{KEY_PREFIX}{secrets.token_hex(16)}"
    key_hash = hash_key(raw_key)
    key_prefix = raw_key[: len(KEY_PREFIX) + 8]
    return raw_key, key_hash, key_prefix


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def require_api_key(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> ApiKey | None:
    """
    FastAPI dependency gating the API behind a bearer API key.

    Disabled under the test suite (see app/config.py's disable_auth) so the
    existing tests don't need an Authorization header on every request.
    """
    if settings.disable_auth:
        return None

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")

    raw_key = authorization.removeprefix("Bearer ").strip()
    key_hash = hash_key(raw_key)

    api_key = (
        db.query(ApiKey)
        .filter(ApiKey.key_hash == key_hash, ApiKey.revoked_at.is_(None))
        .first()
    )
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return api_key
