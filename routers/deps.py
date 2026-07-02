from contextlib import contextmanager
from typing import Optional

from fastapi import Header, HTTPException

from services.auth_service import decode_access_token, TokenError
from core.context import set_context, reset_context


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """FastAPI dependency: validates the bearer token and returns its claims."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

    token = authorization.split(" ", 1)[1]
    try:
        return decode_access_token(token)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


def require_hr(user: dict) -> None:
    if user["role"] != "hr":
        raise HTTPException(status_code=403, detail="This action requires an HR account.")


@contextmanager
def user_context(user: dict):
    """Wraps a block of code with the tenant/role context derived from the
    current user's JWT claims, so anything under services/ or repositories/
    that reads core.context is automatically scoped correctly."""
    token = set_context(
        company_id=user["company_id"],
        role=user["role"],
        employee_id=user.get("employee_id"),
        username=user["username"],
    )
    try:
        yield
    finally:
        reset_context(token)