from services.department_service import (
    get_department,
    list_departments
)


def register(mcp):

    @mcp.tool()
    def get_department_tool(emp_id: int):
        return get_department(emp_id)

    @mcp.tool()
    def list_departments_tool():
        return list_departments()