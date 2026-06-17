from services.employee_service import *

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
    
    