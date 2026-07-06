from services.employee_service import ForbiddenError, NotFoundError
from services.leave_service import (
    get_leave_balance,
    request_leave,
    list_leave_requests,
    decide_leave_request,
)


def register(mcp):
    @mcp.tool()
    def get_leave_balance_tool(emp_id: int | None = None):
        """Get an employee's remaining leave balance. If the caller is a member account, this always returns their own balance regardless of emp_id. HR accounts must supply emp_id — resolve a name to an id first with search_employee_tool if needed."""
        try:
            return get_leave_balance(emp_id)
        except ForbiddenError as exc:
            return {"error": str(exc)}
        except NotFoundError:
            return None

    @mcp.tool()
    def request_leave_tool(start_date: str, end_date: str, reason: str = ""):
        """Submit a leave request for the current user, from start_date to end_date (both YYYY-MM-DD, inclusive), with an optional reason. Only works for employee (member) accounts requesting their own leave — HR accounts have no employee record to request leave against. The request is created as 'pending' and does not affect the leave balance until HR approves it."""
        try:
            return request_leave(start_date, end_date, reason)
        except (ForbiddenError, ValueError) as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def list_leave_requests_tool(status: str | None = None):
        """List leave requests. HR sees every request in the company, optionally filtered by status ('pending', 'approved', or 'rejected'); omit status to see all of them. Members always see only their own requests, regardless of any status filter."""
        return list_leave_requests(status)

    @mcp.tool()
    def decide_leave_request_tool(request_id: int, approve: bool):
        """Approve or reject a pending leave request by its id. HR accounts only. Approving deducts the requested number of days from that employee's leave balance (failing if they no longer have enough); rejecting leaves their balance untouched. Use list_leave_requests_tool first if you need to find a request's id. Returns {"error": ...} if not permitted, if the request was already decided, or if the balance is now insufficient."""
        try:
            return decide_leave_request(request_id, approve)
        except (ForbiddenError, NotFoundError, ValueError) as exc:
            return {"error": str(exc)}