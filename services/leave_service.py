from services.employee_service import get_employee, save_employees, load_employees


def get_leave_balance(emp_id: int):
    employee = get_employee(emp_id)

    if not employee:
        return None

    return employee["leave_balance"]


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

    # 3. Validation checks
    if not employee:
        print(f"Employee {emp_id} not found.")
        return None

    if employee["leave_balance"] < days:
        print("Insufficient leave balance.")
        return None

    employee["leave_balance"] -= days
    
    save_employees(employees)
    return employee
