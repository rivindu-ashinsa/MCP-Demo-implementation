from services.department_service import (
    get_department,
    list_departments,
    update_employee_department,
)


def register(mcp):

    @mcp.tool()
    def get_department_tool(emp_id: int):
        return get_department(emp_id)

    @mcp.tool()
    def list_departments_tool():
        return list_departments()

    @mcp.tool()
    def update_department_tool(emp_id: int, department: str):
        return update_employee_department(emp_id, department)