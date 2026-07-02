from fastapi import APIRouter, Depends

from services import employee_service
from routers.deps import get_current_user, require_hr, user_context

router = APIRouter(prefix="/api/departments", tags=["departments"])


@router.get("/headcounts")
def department_headcounts(user: dict = Depends(get_current_user)) -> dict:
    require_hr(user)
    with user_context(user):
        return employee_service.department_headcounts()