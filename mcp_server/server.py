import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_request
from fastmcp.exceptions import ToolError

from tools import (employee_tools, department_tools, analytic_tools, leave_tools, report_tools)
from prompts import report_prompts

from resources.company_docs import (
    leave_policy,
    company_policy
)

from services.auth_service import decode_access_token, TokenError
from core.context import set_context, reset_context

MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8765"))


class TenantContextMiddleware(Middleware):
    """
    Every tool call arrives over HTTP from services/agent.py, carrying the
    same JWT the main FastAPI app already issued and verified once. This
    middleware decodes it again here (this is a separate process — nothing
    from the FastAPI process's memory, including core.context, crosses the
    boundary automatically) and sets core.context for exactly the duration
    of this one tool call, so employee_service and friends stay correctly
    scoped no matter which process is calling them.

    Reads the token off the Authorization header via get_http_request().
    NOTE: this deliberately does NOT use fastmcp's get_http_headers()
    shorthand — it's known to return empty/stale results inside
    on_call_tool on some fastmcp versions (see jlowin/fastmcp #1291, #817,
    #1233). Going through the Request object directly is more reliable.
    Do not switch this to a URL query parameter instead — that puts the
    JWT in plaintext in any access/proxy log that ever gets added in front
    of this server.

    No token, or an invalid/expired one -> the tool never runs at all.
    """

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        request = get_http_request()
        auth_header = request.headers.get("authorization", "")

        if not auth_header.lower().startswith("bearer "):
            raise ToolError("Missing bearer token on MCP request.")

        token = auth_header.split(" ", 1)[1]
        try:
            claims = decode_access_token(token)
        except TokenError as exc:
            raise ToolError(str(exc))

        ctx_token = set_context(
            company_id=claims["company_id"],
            role=claims["role"],
            employee_id=claims.get("employee_id"),
            username=claims["username"],
        )
        try:
            return await call_next(context)
        finally:
            reset_context(ctx_token)


mcp = FastMCP("Employee Management MCP - DEMO")
mcp.add_middleware(TenantContextMiddleware())

employee_tools.register(mcp)
department_tools.register(mcp)
analytic_tools.register(mcp)
leave_tools.register(mcp)
report_tools.register(mcp)
report_prompts.register(mcp)


@mcp.resource("company://leave-policy")
def leave_policy_resource():
    """includes all the information about default leave balances"""
    return leave_policy()


@mcp.resource("company://company-policy")
def company_policy_resource():
    """includes all the information about company policies"""
    return company_policy()


if __name__ == "__main__":
    mcp.run(transport="http", host=MCP_SERVER_HOST, port=MCP_SERVER_PORT)