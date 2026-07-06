"""
Leave request workflow: a member submits a request (start/end date + an
optional reason), it sits as 'pending', and HR approves or rejects it.
Approving is the only thing that actually touches leave_balance — the
balance isn't reserved while a request is pending, so it's possible (by
design, for this demo's scope) for two overlapping requests to both look
approvable until one of them actually gets approved and drops the balance
out from under the other. decide_leave_request() re-checks the balance at
approval time specifically to catch that case rather than trusting the
number that was true when the request was submitted.
"""
from datetime import date, datetime, timezone

from db.session import session_scope
from db.models import Employee, LeaveRequest
from repositories.employee_repository import EmployeeRepository
from repositories.leave_request_repository import LeaveRequestRepository
from services.employee_service import get_employee, ForbiddenError, NotFoundError
from core.context import get_company_id, get_role, get_employee_id, get_username


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a date in YYYY-MM-DD format, got {value!r}.")


def _to_dict(req: LeaveRequest, employee_name: str | None = None) -> dict:
    return {
        "id": req.id,
        "employee_id": req.employee_id,
        "employee_name": employee_name,
        "start_date": req.start_date.isoformat(),
        "end_date": req.end_date.isoformat(),
        "days": req.days,
        "reason": req.reason,
        "status": req.status,
        "requested_at": req.requested_at.isoformat(),
        "decided_at": req.decided_at.isoformat() if req.decided_at else None,
        "decided_by": req.decided_by,
    }


def get_leave_balance(emp_id: int | None = None) -> dict:
    """Returns {employee_id, name, leave_balance}. Members always get their
    own balance, regardless of what emp_id (if any) was passed in — HR
    accounts must supply a real emp_id. Reuses employee_service.get_employee
    rather than re-implementing its self-vs-other access check here."""
    if get_role() != "hr":
        emp_id = get_employee_id()
        if emp_id is None:
            raise ForbiddenError("Your account has no employee record.")
    elif emp_id is None:
        raise ValueError("HR accounts must specify which employee's balance to check.")

    employee = get_employee(emp_id)
    return {"employee_id": employee["id"], "name": employee["name"], "leave_balance": employee["leave_balance"]}


def request_leave(start_date: str, end_date: str, reason: str | None = None) -> dict:
    """Member-only: submits a leave request for the currently logged-in
    employee. HR accounts have no employee record (per the separate-admin-
    login decision), so there's nothing for them to request leave against."""
    employee_id = get_employee_id()
    if employee_id is None:
        raise ForbiddenError("Only employee accounts can request leave.")

    start = _parse_date(start_date, "start_date")
    end = _parse_date(end_date, "end_date")
    if end < start:
        raise ValueError("end_date can't be before start_date.")

    days = (end - start).days + 1

    with session_scope() as db:
        company_id = get_company_id()
        emp_repo = EmployeeRepository(db, company_id)
        employee = emp_repo.get_by_pk(Employee.id, employee_id)
        if employee is None:
            raise NotFoundError("Your employee record could not be found.")

        if days > employee.leave_balance:
            raise ValueError(
                f"That's {days} day(s), but your current balance is {employee.leave_balance}. "
                "Request fewer days, or wait for your balance to be topped up."
            )

        leave_repo = LeaveRequestRepository(db, company_id)
        leave_request = leave_repo.add(
            LeaveRequest(
                employee_id=employee_id,
                start_date=start,
                end_date=end,
                days=days,
                reason=(reason or "").strip() or None,
                status="pending",
            )
        )
        db.flush()
        return _to_dict(leave_request, employee_name=employee.name)


def list_leave_requests(status: str | None = None) -> list[dict]:
    """HR sees every request in the company (optionally filtered by status).
    Members see only their own requests, regardless of any status filter
    they pass — filtering by other employees' requests isn't something a
    member can do."""
    with session_scope() as db:
        company_id = get_company_id()
        leave_repo = LeaveRequestRepository(db, company_id)
        emp_repo = EmployeeRepository(db, company_id)

        if get_role() == "hr":
            requests = leave_repo.get_by_status(status) if status else leave_repo.get_all()
        else:
            requests = leave_repo.get_for_employee(get_employee_id())

        # One extra query per distinct employee, not per row — fine at demo scale.
        name_cache: dict[int, str] = {}
        results = []
        for req in requests:
            if req.employee_id not in name_cache:
                emp = emp_repo.get_by_pk(Employee.id, req.employee_id)
                name_cache[req.employee_id] = emp.name if emp else "Unknown"
            results.append(_to_dict(req, employee_name=name_cache[req.employee_id]))
        return results


def decide_leave_request(request_id: int, approve: bool) -> dict:
    """HR-only: approves or rejects a pending request. Approving deducts
    `days` from the employee's leave_balance; rejecting leaves it untouched."""
    if get_role() != "hr":
        raise ForbiddenError("Only HR can approve or reject leave requests.")

    with session_scope() as db:
        company_id = get_company_id()
        leave_repo = LeaveRequestRepository(db, company_id)
        emp_repo = EmployeeRepository(db, company_id)

        leave_request = leave_repo.get_by_pk(LeaveRequest.id, request_id)
        if leave_request is None:
            raise NotFoundError(f"No leave request with id {request_id} in this company.")

        if leave_request.status != "pending":
            raise ValueError(f"This request was already {leave_request.status}.")

        employee = emp_repo.get_by_pk(Employee.id, leave_request.employee_id)
        if employee is None:
            raise NotFoundError("The employee this request belongs to no longer exists.")

        if approve:
            if employee.leave_balance < leave_request.days:
                raise ValueError(
                    f"{employee.name} only has {employee.leave_balance} day(s) left, "
                    f"but this request is for {leave_request.days}. Reject it, or have "
                    "them submit a shorter request."
                )
            employee.leave_balance -= leave_request.days
            leave_request.status = "approved"
        else:
            leave_request.status = "rejected"

        leave_request.decided_at = _utcnow()
        leave_request.decided_by = get_username()
        db.flush()

        return _to_dict(leave_request, employee_name=employee.name)