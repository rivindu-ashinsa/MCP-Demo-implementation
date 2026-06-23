from services.employee_service import list_employees, update_employee


def list_departments():
    employees = list_employees()

    departments = {
        employee["department"]
        for employee in employees
        if "department" in employee
    }

    return list(departments)


def get_department(emp_id: int):
    employees = list_employees()

    for employee in employees:
        if employee["id"] == emp_id:
            return employee["department"]

    return None


def update_employee_department(emp_id: int, department: str):
    return update_employee(emp_id, {"department": department})
