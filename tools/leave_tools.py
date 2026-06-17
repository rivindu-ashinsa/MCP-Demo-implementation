from services.leave_service import * 


def register(mcp):

    @mcp.tool()
    def get_leave_balance_tool(emp_id: int):
        return get_leave_balance(emp_id)
    

    @mcp.tool()
    def apply_leave_tool(emp_id: int, days: int):
        return apply_leave(emp_id, days)