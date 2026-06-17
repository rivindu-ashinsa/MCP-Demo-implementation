from services.employee_service import list_employees


def list_departments():
    employees = list_employees()

    departments = {
        employee["department"]
        for employee in employees
    }

    return list(departments)


def get_department(emp_id: int):
    employees = list_employees()

    for employee in employees:
        if employee["id"] == emp_id:
            return employee["department"]

    return None
