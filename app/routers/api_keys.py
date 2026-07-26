from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.api_key import ApiKey
from app.schemas.api_key import ApiKeyCreateRequest, ApiKeyCreatedResponse, ApiKeyResponse
from app.utils.auth import generate_key, require_api_key

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


@router.post("", response_model=ApiKeyCreatedResponse, status_code=201)
def create_api_key(
    request: ApiKeyCreateRequest,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    """
    Create a new API key.

    Bootstrap rule: if no active key exists yet, this endpoint is open —
    that's how a fresh self-hosted instance mints its first key. Once at
    least one active key exists, further creation requires a valid key.
    """
    has_active_key = db.query(ApiKey).filter(ApiKey.revoked_at.is_(None)).first() is not None
    if has_active_key:
        require_api_key(authorization=authorization, db=db)

    raw_key, key_hash, key_prefix = generate_key()
    api_key = ApiKey(name=request.name, key_hash=key_hash, key_prefix=key_prefix)
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return ApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,
        key_prefix=api_key.key_prefix,
        created_at=api_key.created_at,
    )


@router.get("", response_model=list[ApiKeyResponse], dependencies=[Depends(require_api_key)])
def list_api_keys(db: Session = Depends(get_db)):
    return db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()


@router.delete("/{key_id}", response_model=ApiKeyResponse, dependencies=[Depends(require_api_key)])
def revoke_api_key(key_id: str, db: Session = Depends(get_db)):
    from datetime import datetime, timezone

    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.revoked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(api_key)
    return api_key
