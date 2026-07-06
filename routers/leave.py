from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from services import leave_service
from routers.deps import get_current_user, require_hr, user_context

router = APIRouter(prefix="/api/leave", tags=["leave"])


class CreateLeaveRequest(BaseModel):
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    reason: Optional[str] = None


class LeaveDecision(BaseModel):
    approve: bool


@router.post("/requests")
def create_leave_request(body: CreateLeaveRequest, user: dict = Depends(get_current_user)) -> dict:
    """Member-only in practice: HR accounts have no employee record, so
    leave_service raises ForbiddenError for them — enforced there, not here,
    same defense-in-depth pattern as the rest of the service layer."""
    with user_context(user):
        try:
            return leave_service.request_leave(body.start_date, body.end_date, body.reason)
        except leave_service.ForbiddenError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        except leave_service.NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@router.get("/requests")
def list_leave_requests(
    status: Optional[str] = Query(None, description="Filter by 'pending' | 'approved' | 'rejected' (HR only; ignored for members)"),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with user_context(user):
        return leave_service.list_leave_requests(status)


@router.patch("/requests/{request_id}")
def decide_leave_request(request_id: int, body: LeaveDecision, user: dict = Depends(get_current_user)) -> dict:
    require_hr(user)
    with user_context(user):
        try:
            return leave_service.decide_leave_request(request_id, body.approve)
        except leave_service.NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))