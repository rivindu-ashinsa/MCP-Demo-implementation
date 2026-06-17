from services.analytic_service import *

def register(mcp):
    @mcp.tool()
    def employee_count_tool():
        return employee_count() 
    
    @mcp.tool()
    def department_summary_tool():
        return department_summary()