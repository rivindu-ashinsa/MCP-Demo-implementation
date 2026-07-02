from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from posthog import flush

from services.agent import get_agent
from core.context import set_context, reset_context
from routers.deps import get_current_user

router = APIRouter(tags=["chat"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SUMMARY_PROMPT_FILE = PROJECT_ROOT / "prompts" / "one_page_summary_prompt.txt"
REPORT_PROMPT_FILE = PROJECT_ROOT / "prompts" / "employee_summary_prompt.txt"

REPORT_TRIGGER_WORDS = ("report", "pdf", "summary report", "one-pager", "printable")
LOOP_GUARDRAIL = (
    "[CRITICAL INSTRUCTION: If any search tool yields no results, "
    "do not repeat the search. Respond directly stating nothing was found.]\n\n"
)


class ChatRequest(BaseModel):
    message: str


class SummaryRequest(BaseModel):
    subject: str
    context: Optional[str] = None


def _is_report_request(message_lower: str) -> bool:
    return any(word in message_lower for word in REPORT_TRIGGER_WORDS)


def _scoped(user: dict):
    return set_context(
        company_id=user["company_id"],
        role=user["role"],
        employee_id=user.get("employee_id"),
        username=user["username"],
    )


@router.post("/chat")
async def chat(request: ChatRequest, user: dict = Depends(get_current_user)) -> dict:
    agent = get_agent()
    token = _scoped(user)
    try:
        message_lower = request.message.lower()

        if _is_report_request(message_lower) and REPORT_PROMPT_FILE.exists():
            instructions = REPORT_PROMPT_FILE.read_text(encoding="utf-8").strip()
            full_message = f"{LOOP_GUARDRAIL}{instructions}\n\nUser request: {request.message}"
        else:
            full_message = f"{LOOP_GUARDRAIL}{request.message}"

        response = await agent.run(full_message)
        flush()
        return {"assistant": response}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        reset_context(token)


@router.post("/summary")
async def summary(request: SummaryRequest, user: dict = Depends(get_current_user)) -> dict:
    agent = get_agent()

    if not SUMMARY_PROMPT_FILE.exists():
        raise HTTPException(status_code=500, detail=f"Prompt file not found at {SUMMARY_PROMPT_FILE}")

    prompt = SUMMARY_PROMPT_FILE.read_text(encoding="utf-8").strip()
    context = (
        request.context
        or "Use the available employee, department, leave, and company policy data to build the report."
    )
    body = f"{prompt}\n\nSubject: {request.subject}\n\nContext: {context}"

    token = _scoped(user)
    try:
        response = await agent.run(body)
        flush()
        return {"summary": response}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        reset_context(token)