from services.employee_service import (
    add_employee,
    delete_employee,
    get_employee,
    list_employees,
    save_employees,
    search_employee,
    update_employee,
)


def register(mcp):
    @mcp.tool()
    def get_employee_tool(emp_id: int):
        return get_employee(emp_id)

    @mcp.tool()
    def list_employees_tool():
        return list_employees()

    @mcp.tool()
    def search_employee_tool(name: str):
        return search_employee(name)

    @mcp.tool()
    def add_employee_tool(employee: dict):
        return add_employee(employee)

    @mcp.tool()
    def update_employee_tool(emp_id: int, updates: dict):
        return update_employee(emp_id, updates)

    @mcp.tool()
    def delete_employee_tool(emp_id: int):
        return delete_employee(emp_id)