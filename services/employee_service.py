import json
from pathlib import Path

EMPLOYEE_FILE = Path("data/employees.json")


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