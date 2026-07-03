import os
from typing import Optional

from langchain_groq import ChatGroq
from mcp_use import MCPAgent, MCPClient

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8765/mcp")

SYSTEM_INSTRUCTION = (
    "You are a helpful HR assistant. "
    "Crucial Rule: If a tool returns an empty result, null, or indicates a resource/employee "
    "was not found, DO NOT call the same tool with the same arguments again. "
    "Immediately stop and inform the user that the requested information or employee "
    "could not be found. "
    "Every tool call you make is automatically restricted to the current user's company and, "
    "for non-HR users, to their own employee record — you do not need to and should never ask "
    "the user which company or employee id to filter by."
)

_llm: Optional[ChatGroq] = None


def initialize_agent() -> None:
    """
    Validates config and builds the (stateless, shareable) LLM client at
    startup. Unlike before, this does NOT build a shared MCPClient/MCPAgent
    — those are now built fresh per request in run_with_identity(), because
    each one needs to carry a *different* user's bearer token to the MCP
    server as an HTTP header. A single shared client can't vary that per
    concurrent request, which was the root cause of both the "no request
    context set" crash and the earlier cross-user chat-memory concern.
    """
    global _llm

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")

    _llm = ChatGroq(groq_api_key=groq_api_key, model="openai/gpt-oss-safeguard-20b")


async def shutdown_agent() -> None:
    global _llm

    _llm = None


def _get_llm() -> ChatGroq:
    if _llm is None:
        raise RuntimeError("LLM is not initialized")
    return _llm


async def run_with_identity(token: str, message: str) -> str:
    """
    Builds a short-lived MCPClient/MCPAgent scoped to exactly one request,
    with `token` forwarded as the Authorization header on the connection to
    the MCP server. That header is what mcp_server/server.py's
    TenantContextMiddleware reads to scope every tool call this agent makes.

    memory_enabled is intentionally False: this client is thrown away after
    one message, so there is nothing to remember, and — more importantly —
    nothing that could leak into the next user's turn.
    """
    # print(f"DEBUG token repr: {token!r}")   # <-- add this line

    config = {
        "mcpServers": {
            "server": {
                "transport": "http",
                "url": f"{MCP_SERVER_URL}?token={token}",
                "auth": None,
            }
        }
    }

    client = MCPClient.from_dict(config)
    try:
        agent = MCPAgent(
            client=client,
            llm=_get_llm(),
            max_steps=10,
            memory_enabled=False,
            system_prompt=SYSTEM_INSTRUCTION,
        )
        return await agent.run(message)
    finally:
        if getattr(client, "sessions", None):
            await client.close_all_sessions()