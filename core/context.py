"""
Request-scoped context.

Why this exists: MCP tools are invoked by the LLM based on their declared
schema — you can't cleanly add a hidden "company_id" parameter that the LLM
is trusted to fill in correctly (an LLM should never be the security
boundary). Instead, the FastAPI request handler sets this context *before*
calling the agent, every service function reads from it, and the LLM never
sees or controls it at all.

Usage in a request handler:

    token = set_context(company_id=1, role="member", employee_id=7, username="john.doe")
    try:
        ...do work / call mcp_agent.run(...)...
    finally:
        reset_context(token)

Usage in a service function:

    from core.context import get_company_id, get_role, get_employee_id

    def list_employees():
        company_id = get_company_id()
        if get_role() == "member":
            ...filter to get_employee_id()...
"""
from contextvars import ContextVar
from typing import NamedTuple, Optional


class RequestContext(NamedTuple):
    company_id: int
    role: str  # "hr" | "member"
    employee_id: Optional[int]
    username: str


_ctx: ContextVar[Optional[RequestContext]] = ContextVar("_ctx", default=None)


def set_context(company_id: int, role: str, employee_id: Optional[int], username: str):
    return _ctx.set(RequestContext(company_id, role, employee_id, username))


def reset_context(token) -> None:
    _ctx.reset(token)


def _require() -> RequestContext:
    ctx = _ctx.get()
    if ctx is None:
        raise RuntimeError(
            "No request context set. Every route that touches tenant data "
            "must call set_context(...) before doing any DB work."
        )
    return ctx


def get_company_id() -> int:
    return _require().company_id


def get_role() -> str:
    return _require().role


def get_employee_id() -> Optional[int]:
    return _require().employee_id


def get_username() -> str:
    return _require().username


def is_hr() -> bool:
    return _require().role == "hr"