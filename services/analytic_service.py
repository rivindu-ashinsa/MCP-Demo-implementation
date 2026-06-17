from collections import Counter

from services.employee_service import list_employees


def employee_count():
    return len(list_employees())


def department_summary():
    employees = list_employees()

    counts = Counter(
        employee["department"]
        for employee in employees
    )

    return dict(counts)