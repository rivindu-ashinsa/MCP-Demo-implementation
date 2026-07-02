from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services import employee_service
from routers.deps import get_current_user, require_hr, user_context

router = APIRouter(prefix="/api/employees", tags=["employees"])


class CreateEmployeeRequest(BaseModel):
    name: str = Field(min_length=1)
    department: str | None = None
    leave_balance: int = 0


@router.get("")
def list_employees(user: dict = Depends(get_current_user)) -> list[dict]:
    """HR gets every employee in their company; members get only themselves."""
    with user_context(user):
        return employee_service.list_employees()


@router.get("/{employee_id}")
def get_employee(employee_id: int, user: dict = Depends(get_current_user)) -> dict:
    with user_context(user):
        try:
            return employee_service.get_employee(employee_id)
        except employee_service.ForbiddenError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        except employee_service.NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


@router.post("")
def create_employee(request: CreateEmployeeRequest, user: dict = Depends(get_current_user)) -> dict:
    """HR-only. Adds an employee and provisions their login in one step,
    returning the generated username/password so HR can hand it over."""
    require_hr(user)
    with user_context(user):
        return employee_service.create_employee(
            name=request.name,
            department=request.department,
            leave_balance=request.leave_balance,
        )