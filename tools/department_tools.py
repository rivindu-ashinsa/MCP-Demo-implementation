from services.department_service import (
    get_department,
    list_departments,
    update_employee_department,
)


def register(mcp):

    @mcp.tool()
    def get_department_tool(emp_id: int):
        """Get the department name for a single employee, identified by their numeric ID."""
        return get_department(emp_id)

    @mcp.tool()
    def list_departments_tool():
        """List the names of every department in the company. Use this when the user asks what departments exist or wants a simple list of department names (not headcounts)."""
        return list_departments()

    @mcp.tool()
    def update_department_tool(emp_id: int, department: str):
        """Move an employee to a different department. Identify the employee by emp_id and pass the new department name as a string."""
        return update_employee_department(emp_id, department)