import json
from collections import Counter
from pathlib import Path

from services.employee_service import list_employees

BASE_DIR = Path(__file__).resolve().parent.parent
REPORT_FILE = BASE_DIR / "data" / "reports.json"


def _load_reports():
    if not REPORT_FILE.exists():
        return []

    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_reports(reports):
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2)


def employee_count():
    return len(list_employees())


def department_summary():
    employees = list_employees()

    counts = Counter(
        employee["department"]
        for employee in employees
    )

    return dict(counts)


def list_reports():
    return _load_reports()


def save_summary_report(title: str, summary: str):
    reports = _load_reports()
    report = {"title": title, "summary": summary}
    reports.append(report)
    _save_reports(reports)
    return report