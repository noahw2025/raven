import hmac
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Cookie, Depends, HTTPException, Request
from .config import get_settings
from .db import db


def issue(user_id: str) -> str:
    s = get_settings()
    return jwt.encode({"sub":user_id,"exp":datetime.now(timezone.utc)+timedelta(hours=12)},s.raven_jwt_secret,algorithm="HS256")


def valid_password(value: str) -> bool:
    return hmac.compare_digest(value.encode(),get_settings().raven_admin_password.encode())


async def current_user(request: Request, raven_session: str | None = Cookie(default=None)) -> str:
    settings = get_settings()
    if not settings.raven_require_login:
        user_id = await db.pool.fetchval("SELECT id FROM users WHERE username='owner'")
        if not user_id:
            raise HTTPException(503,"Owner profile unavailable")
        if request.method not in {"GET","HEAD","OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin.rstrip("/") != settings.raven_public_origin.rstrip("/"):
                raise HTTPException(403,"Origin not allowed")
        return str(user_id)
    if not raven_session:
        raise HTTPException(401,"Authentication required")
    try:
        user_id = jwt.decode(raven_session,settings.raven_jwt_secret,algorithms=["HS256"])["sub"]
    except jwt.PyJWTError:
        raise HTTPException(401,"Session expired")
    # Same-origin mutation guard complements SameSite cookies.
    if request.method not in {"GET","HEAD","OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != settings.raven_public_origin.rstrip("/"):
            raise HTTPException(403,"Origin not allowed")
    return user_id


User = Depends(current_user)
