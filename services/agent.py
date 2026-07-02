import os
from pathlib import Path
from typing import Optional

from langchain_groq import ChatGroq
from mcp_use import MCPAgent, MCPClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SERVER_CONFIG = PROJECT_ROOT / "server.json"

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

_client: Optional[MCPClient] = None
_agent: Optional[MCPAgent] = None


def initialize_agent() -> None:
    """Synchronous initializer — call via asyncio.to_thread from the FastAPI lifespan."""
    global _client, _agent

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")

    if not SERVER_CONFIG.exists():
        raise RuntimeError(f"MCP configuration file not found at {SERVER_CONFIG}")

    _client = MCPClient.from_config_file(str(SERVER_CONFIG))
    llm = ChatGroq(groq_api_key=groq_api_key, model="openai/gpt-oss-safeguard-20b")

    _agent = MCPAgent(
        client=_client,
        llm=llm,
        max_steps=10,
        memory_enabled=True,
        system_prompt=SYSTEM_INSTRUCTION,
    )


async def shutdown_agent() -> None:
    global _client
    if _client and getattr(_client, "sessions", None):
        await _client.close_all_sessions()


def get_agent() -> MCPAgent:
    if _agent is None:
        raise RuntimeError("MCP agent is not initialized")
    return _agent