"""
report_tools.py

MCP tool that generates a fixed-layout, one-page Employee Summary PDF
and returns a URL the frontend can use to download it.
"""

from services.employee_service import get_employee
from services.report_service import generate_employee_summary

# Must match how app/main.py mounts/serves the reports directory.
REPORT_URL_PREFIX = "/reports"


def register(mcp):
    @mcp.tool()
    def generate_employee_summary_report_tool(emp_id: int):
        """
        Generate a one-page PDF summary report for a single employee
        (contact info + leave balance) and return a download URL.

        Always use this tool when the user asks for a summary report,
        PDF, or printable profile for a specific employee.
        """
        employee = get_employee(emp_id)
        if employee is None:
            return {"error": f"No employee found with id {emp_id}"}

        # leave_balance lives directly on the employee record in this dataset
        leave_info = {"leave_balance": employee.get("leave_balance")}

        pdf_path = generate_employee_summary(employee, leave_info)

        return {
            "message": f"Generated summary report for {employee.get('name', 'employee #' + str(emp_id))}.",
            "report_url": f"{REPORT_URL_PREFIX}/{pdf_path.name}",
            "filename": pdf_path.name,
        }