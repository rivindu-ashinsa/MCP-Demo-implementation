"""
Password hashing (bcrypt) and JWT issue/verify.

Requires: pip install pyjwt bcrypt --break-system-packages

Set a real JWT_SECRET in .env before this goes anywhere near production —
the fallback below is only so the demo runs out of the box.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
TOKEN_TTL_HOURS = 8


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    *, company_id: int, company_name: str, username: str, role: str, employee_id: Optional[int]
) -> str:
    payload = {
        "company_id": company_id,
        "company_name": company_name,
        "username": username,
        "role": role,
        "employee_id": employee_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


class TokenError(Exception):
    pass


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise TokenError("Session expired — please log in again.")
    except jwt.InvalidTokenError:
        raise TokenError("Invalid session token.")