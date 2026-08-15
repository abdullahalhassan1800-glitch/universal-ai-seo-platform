"""Password hashing and JWT auth helpers."""

from __future__ import annotations

import datetime as dt
import uuid

import bcrypt
import jwt

from .config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: uuid.UUID | str, expires_minutes: int | None = None) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    expire = now + dt.timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "iat": now, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
