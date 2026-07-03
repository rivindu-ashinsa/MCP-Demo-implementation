from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services import employee_service
from routers.deps import get_current_user, require_hr, user_context

router = APIRouter(prefix="/api/employees", tags=["employees"])


class CreateEmployeeRequest(BaseModel):
    name: str = Field(min_length=1)
    department: str | None = None
    leave_balance: int = 0


class UpdateLeaveBalanceRequest(BaseModel):
    leave_balance: int = Field(ge=0)


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


@router.patch("/{employee_id}")
def update_leave_balance(
    employee_id: int, request: UpdateLeaveBalanceRequest, user: dict = Depends(get_current_user)
) -> dict:
    """HR-only. Updates an employee's leave balance. 404s (not 403s) if the
    id belongs to a different company — .scoped() can't distinguish
    "wrong company" from "doesn't exist," which is the point: it never
    confirms another tenant's id is real."""
    require_hr(user)
    with user_context(user):
        try:
            return employee_service.update_leave_balance(employee_id, request.leave_balance)
        except employee_service.NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{employee_id}")
def delete_employee(employee_id: int, user: dict = Depends(get_current_user)) -> dict:
    """HR-only. Permanently removes an employee (and, via the DB's
    ON DELETE CASCADE, their login)."""
    require_hr(user)
    with user_context(user):
        deleted = employee_service.delete_employee(employee_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"No employee with id {employee_id} in this company.")
        return {"deleted": True, "id": employee_id}