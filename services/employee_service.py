import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent  # go up from services/ to project root
EMPLOYEE_FILE = BASE_DIR / "data" / "employees.json"


def load_employees():
    with open(EMPLOYEE_FILE, "r") as f:
        return json.load(f)


def get_employee(emp_id: int):
    employees = load_employees()

    for employee in employees:
        if employee["id"] == emp_id:
            return employee

    return None


def list_employees():
    return load_employees()


def search_employee(name: str):
    employees = load_employees()

    return [
        emp
        for emp in employees
        if name.lower() in emp["name"].lower()
    ]


def save_employees(employees):
    with open(EMPLOYEE_FILE, "w") as f:
        json.dump(employees, f, indent=2)


def add_employee(employee: dict):
    employees = load_employees()
    new_id = max((emp["id"] for emp in employees), default=0) + 1
    employee["id"] = new_id
    employees.append(employee)
    save_employees(employees)
    return employee


def update_employee(emp_id: int, updates: dict):
    employees = load_employees()

    for employee in employees:
        if employee["id"] == emp_id:
            employee.update(updates)
            save_employees(employees)
            return employee

    return None


def delete_employee(emp_id: int):
    employees = load_employees()
    new_employees = [emp for emp in employees if emp["id"] != emp_id]

    if len(new_employees) == len(employees):
        return False

    save_employees(new_employees)
    return True