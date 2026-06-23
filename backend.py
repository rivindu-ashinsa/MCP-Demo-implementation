import asyncio
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_groq import ChatGroq
from mcp_use import MCPAgent, MCPClient
from posthog import flush

BASE_DIR = Path(__file__).resolve().parent
SERVER_CONFIG = BASE_DIR / "server.json"
PROMPT_FILE = BASE_DIR / "prompts" / "one_page_summary_prompt.txt"

app = FastAPI(
    title="MCP Demo Chatbot",
    description="A lightweight FastAPI backend that forwards chat requests to a Groq-powered MCP agent.",
)

mcp_client: Optional[MCPClient] = None
mcp_agent: Optional[MCPAgent] = None


class ChatRequest(BaseModel):
    message: str


class SummaryRequest(BaseModel):
    subject: str
    context: Optional[str] = None


def initialize_agent() -> None:
    global mcp_client, mcp_agent

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")

    if not SERVER_CONFIG.exists():
        raise RuntimeError(f"MCP configuration file not found at {SERVER_CONFIG}")

    mcp_client = MCPClient.from_config_file(str(SERVER_CONFIG))
    llm = ChatGroq(groq_api_key=groq_api_key, model="llama-3.1-8b-instant")
    mcp_agent = MCPAgent(client=mcp_client, llm=llm, max_steps=10, memory_enabled=True)


@app.on_event("startup")
async def startup() -> None:
    await asyncio.to_thread(initialize_agent)


@app.on_event("shutdown")
async def shutdown() -> None:
    global mcp_client
    if mcp_client and getattr(mcp_client, "sessions", None):
        await mcp_client.close_all_sessions()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: ChatRequest) -> dict:
    if not mcp_agent:
        raise HTTPException(status_code=500, detail="MCP agent is not initialized")

    try:
        response = await mcp_agent.run(request.message)
        flush()
        return {"assistant": response}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/summary")
async def summary(request: SummaryRequest) -> dict:
    if not mcp_agent:
        raise HTTPException(status_code=500, detail="MCP agent is not initialized")

    if not PROMPT_FILE.exists():
        raise HTTPException(status_code=500, detail=f"Prompt file not found at {PROMPT_FILE}")

    prompt = PROMPT_FILE.read_text(encoding="utf-8").strip()
    context = request.context or "Use the available employee, department, leave, and company policy data to build the report."
    body = (
        f"{prompt}\n\n"
        f"Subject: {request.subject}\n\n"
        f"Context: {context}"
    )

    try:
        response = await mcp_agent.run(body)
        flush()
        return {"summary": response}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
