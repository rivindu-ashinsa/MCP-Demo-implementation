import asyncio
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langchain_groq import ChatGroq
from mcp_use import MCPAgent, MCPClient
from posthog import flush

# app/main.py lives in app/, so the project root is one level up.
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

SERVER_CONFIG = PROJECT_ROOT / "server.json"
SUMMARY_PROMPT_FILE = PROJECT_ROOT / "prompts" / "one_page_summary_prompt.txt"
REPORT_PROMPT_FILE = PROJECT_ROOT / "prompts" / "employee_summary_prompt.txt"
STATIC_DIR = PROJECT_ROOT / "static"
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

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
    llm = ChatGroq(groq_api_key=groq_api_key, model="openai/gpt-oss-safeguard-20b")
    
    # SYSTEM LOOP PROTECTION: Define clear behavioral instructions for the agent
    system_instruction = (
        "You are a helpful HR assistant. Crucial Rule: If a tool returns an empty result, "
        "null, or indicates a resource/employee was not found, DO NOT call the same tool "
        "with the same arguments again. Immediately stop and inform the user that the "
        "requested information or employee could not be found."
    )
    
    # We pass the instruction to the agent. If MCPAgent supports system_prompt, use it.
    # Otherwise, we will inject it directly into the execution messages below.
    mcp_agent = MCPAgent(
        client=mcp_client, 
        llm=llm, 
        max_steps=10, 
        memory_enabled=True
    )



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


# Keywords that indicate this message is asking for a report/PDF, so we only
# inject the strict report-formatting instructions when actually relevant —
# not on every unrelated query like "leave balances" or "how many departments".
REPORT_TRIGGER_WORDS = ("report", "pdf", "summary report", "one-pager", "printable")





@app.post("/chat")
async def chat(request: ChatRequest) -> dict:
    if not mcp_agent:
        raise HTTPException(status_code=500, detail="MCP agent is not initialized")

    try:
        message_lower = request.message.lower()
        
        # Guardrails injected directly into the user message context to force LLM compliance
        loop_guardrail = (
            "[CRITICAL INSTRUCTION: If any search tool yields no results, "
            "do not repeat the search. Respond directly stating nothing was found.]\n\n"
        )
        full_message = f"{loop_guardrail}{request.message}"

        if any(word in message_lower for word in REPORT_TRIGGER_WORDS) and REPORT_PROMPT_FILE.exists():
            instructions = REPORT_PROMPT_FILE.read_text(encoding="utf-8").strip()
            full_message = f"{loop_guardrail}{instructions}\n\nUser request: {request.message}"

        response = await mcp_agent.run(full_message)
        return {"assistant": response}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/summary")
async def summary(request: SummaryRequest) -> dict:
    if not mcp_agent:
        raise HTTPException(status_code=500, detail="MCP agent is not initialized")

    if not SUMMARY_PROMPT_FILE.exists():
        raise HTTPException(status_code=500, detail=f"Prompt file not found at {SUMMARY_PROMPT_FILE}")

    prompt = SUMMARY_PROMPT_FILE.read_text(encoding="utf-8").strip()
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


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))