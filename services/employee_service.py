"""
All reads/writes here are scoped to the current tenant (company_id) and,
for members, to their own employee row — via core.context, which is set
from the verified JWT in the router layer (or from the MCP chat/summary
handlers before the agent runs). Callers never pass company_id/role
explicitly, and can't accidentally forget to filter.

Each function opens its own short-lived DB session via session_scope()
so this module works the same whether it's called from a FastAPI route
(which already has a request-scoped session) or from an MCP tool
(which doesn't).
"""
from db.session import session_scope
from db.models import Employee, User
from repositories.employee_repository import EmployeeRepository
from repositories.user_repository import UserRepository
from services.auth_service import hash_password
from services.credentials import slugify, unique_username
from core.context import get_company_id, get_role, get_employee_id


class NotFoundError(Exception):
    pass


class ForbiddenError(Exception):
    pass


def _to_dict(emp: Employee) -> dict:
    return {
        "id": emp.id,
        "local_id": emp.local_id,
        "name": emp.name,
        "department": emp.department,
        "leave_balance": emp.leave_balance,
    }


def list_employees() -> list[dict]:
    """HR sees every employee in their company. Members see only themselves."""
    with session_scope() as db:
        repo = EmployeeRepository(db, get_company_id())

        if get_role() == "hr":
            employees = repo.get_all()
        else:
            emp_id = get_employee_id()
            match = repo.get_by_pk(Employee.id, emp_id) if emp_id else None
            employees = [match] if match else []

        return [_to_dict(e) for e in employees]


def get_employee(employee_id: int) -> dict:
    if get_role() != "hr" and employee_id != get_employee_id():
        raise ForbiddenError("You can only view your own record.")

    with session_scope() as db:
        repo = EmployeeRepository(db, get_company_id())
        emp = repo.get_by_pk(Employee.id, employee_id)
        if emp is None:
            raise NotFoundError(f"No employee with id {employee_id} in this company.")
        return _to_dict(emp)


def find_employee_by_name(name: str) -> dict | None:
    """Used by chat/MCP tools for natural-language lookups like 'find John Doe'."""
    with session_scope() as db:
        repo = EmployeeRepository(db, get_company_id())
        emp = repo.get_by_name(name)
        if emp is None:
            return None

        if get_role() != "hr" and emp.id != get_employee_id():
            raise ForbiddenError("You can only look up your own record.")

        return _to_dict(emp)


def department_headcounts() -> dict:
    """HR-only aggregate. Members get an empty result rather than an error."""
    if get_role() != "hr":
        return {}

    with session_scope() as db:
        repo = EmployeeRepository(db, get_company_id())
        return repo.department_headcounts()


def update_leave_balance(employee_id: int, new_balance: int) -> dict:
    if get_role() != "hr":
        raise ForbiddenError("Only HR can update leave balances.")

    with session_scope() as db:
        repo = EmployeeRepository(db, get_company_id())
        emp = repo.get_by_pk(Employee.id, employee_id)
        if emp is None:
            raise NotFoundError(f"No employee with id {employee_id} in this company.")
        repo.update_leave_balance(emp, new_balance)
        db.flush()
        return _to_dict(emp)


def create_employee(name: str, department: str | None, leave_balance: int = 0) -> dict:
    """HR-only: adds a new employee AND provisions a login for them
    (username = a slug of their name, seed password = their new local id —
    same scheme the JSON migration used, so it stays predictable)."""
    if get_role() != "hr":
        raise ForbiddenError("Only HR can add employees.")

    with session_scope() as db:
        company_id = get_company_id()
        emp_repo = EmployeeRepository(db, company_id)
        user_repo = UserRepository(db, company_id)

        local_id = emp_repo.next_local_id()
        employee = emp_repo.add(
            Employee(local_id=local_id, name=name.strip(), department=department, leave_balance=leave_balance)
        )
        db.flush()  # populate employee.id before using it below

        username = unique_username(user_repo, slugify(name))
        password = str(local_id)
        user_repo.add(
            User(
                username=username,
                password_hash=hash_password(password),
                role="member",
                employee_id=employee.id,
            )
        )
        db.flush()

        result = _to_dict(employee)
        result["generated_login"] = {"username": username, "password": password}
        return result


# ---------------------------------------------------------------------------
# Backward-compatible helpers used by the existing MCP tool modules
# ---------------------------------------------------------------------------


def load_employees() -> list[dict]:
    return list_employees()


def save_employees(employees: list[dict]) -> None:
    if get_role() != "hr":
        raise ForbiddenError("Only HR can bulk-update employees.")

    with session_scope() as db:
        repo = EmployeeRepository(db, get_company_id())
        for payload in employees:
            emp_id = payload.get("id")
            if emp_id is None:
                continue

            employee = repo.get_by_pk(Employee.id, emp_id)
            if employee is None:
                continue

            if "local_id" in payload:
                employee.local_id = payload["local_id"]
            if "name" in payload:
                employee.name = payload["name"]
            if "department" in payload:
                employee.department = payload["department"]
            if "leave_balance" in payload:
                employee.leave_balance = payload["leave_balance"]


def search_employee(name: str) -> list[dict]:
    needle = name.strip().lower()
    if not needle:
        return []
    return [employee for employee in list_employees() if needle in employee["name"].lower()]


def add_employee(employee: dict) -> dict:
    return create_employee(
        name=employee.get("name", "").strip(),
        department=employee.get("department"),
        leave_balance=int(employee.get("leave_balance", 0) or 0),
    )


def update_employee(emp_id: int, updates: dict) -> dict | None:
    if get_role() != "hr":
        raise ForbiddenError("Only HR can update employees.")

    with session_scope() as db:
        repo = EmployeeRepository(db, get_company_id())
        employee = repo.get_by_pk(Employee.id, emp_id)
        if employee is None:
            return None

        if "name" in updates:
            employee.name = updates["name"]
        if "department" in updates:
            employee.department = updates["department"]
        if "leave_balance" in updates:
            employee.leave_balance = updates["leave_balance"]

        db.flush()
        return _to_dict(employee)


def delete_employee(emp_id: int) -> bool:
    if get_role() != "hr":
        raise ForbiddenError("Only HR can delete employees.")

    with session_scope() as db:
        repo = EmployeeRepository(db, get_company_id())
        employee = repo.get_by_pk(Employee.id, emp_id)
        if employee is None:
            return False

        repo.delete(employee)
        return True