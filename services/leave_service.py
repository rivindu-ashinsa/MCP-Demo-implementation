from services.employee_service import get_employee, save_employees, load_employees


def get_leave_balance(emp_id: int):
    employee = get_employee(emp_id)

    if not employee:
        return None

    return employee.get("leave_balance")


def apply_leave(emp_id: int, days: int):
    """
    1. Check employee exists
    2. Check sufficient balance
    3. Deduct leave
    4. Save changes
    """
    employees = load_employees()

    employee = None
    for emp in employees:
        if emp["id"] == emp_id:
            employee = emp
            break

    if not employee:
        return None

    if employee.get("leave_balance", 0) < days:
        return None

    employee["leave_balance"] = employee.get("leave_balance", 0) - days
    save_employees(employees)
    return employee


def set_leave_balance(emp_id: int, balance: int):
    employees = load_employees()

    employee = None
    for emp in employees:
        if emp["id"] == emp_id:
            employee = emp
            break

    if not employee:
        return None

    employee["leave_balance"] = balance
    save_employees(employees)
    return employee
