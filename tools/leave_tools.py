from services.leave_service import get_leave_balance, apply_leave


def register(mcp):

    @mcp.tool()
    def get_leave_balance_tool(emp_id: int):
        """Get the remaining leave balance (in days) for a single employee, identified by their numeric ID. For leave balances of multiple/all employees at once, use list_all_leave_balances_tool instead."""
        return get_leave_balance(emp_id)

    @mcp.tool()
    def apply_leave_tool(emp_id: int, days: int):
        """Deduct a number of leave days from an employee's balance, identified by emp_id. Use this when the user says an employee is taking leave or applying for leave."""
        return apply_leave(emp_id, days)