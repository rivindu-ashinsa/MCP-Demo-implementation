from contextlib import contextmanager

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.auth_service import decode_access_token, TokenError
from core.context import set_context, reset_context

# `auto_error=False` so we can raise our own 401 with a consistent message
# shape instead of FastAPI's default. Registering this as a Security scheme
# (rather than reading the header manually) is what makes /docs show a lock
# icon next to every protected route and a proper "Authorize" button where
# you paste the token once for the whole session.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """FastAPI dependency: validates the bearer token and returns its claims."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

    try:
        return decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


def get_bearer_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    """For routes (like chat) that need to forward the raw token onward —
    e.g. to the MCP server as a header — rather than just reading its
    claims locally. Still validates it first, so a malformed/expired token
    fails fast with a 401 instead of being forwarded to fail somewhere else."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

    try:
        decode_access_token(credentials.credentials)  # validate, discard claims
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    return credentials.credentials


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