from services.employee_service import (
    ForbiddenError,
    NotFoundError,
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
        """Look up a single employee by their numeric ID. Returns their full record (name, department, leave_balance), an {"error": ...} dict if not permitted, or null if not found."""
        try:
            return get_employee(emp_id)
        except ForbiddenError as exc:
            return {"error": str(exc)}
        except NotFoundError:
            return None

    @mcp.tool()
    def list_employees_tool():
        """List every employee in the company. Use this when the user asks for all employees, a headcount, or any bulk view across all employees. Non-HR users will only ever see their own record here — that's expected, not a bug."""
        return list_employees()

    @mcp.tool()
    def search_employee_tool(name: str):
        """Search for employees whose name contains the given text (case-insensitive). Use this when the user gives a name instead of an ID and you need to resolve it."""
        return search_employee(name)

    @mcp.tool()
    def add_employee_tool(employee: dict):
        """Create a new employee record. Expects a dict with fields like name, department, and leave_balance. Assigns a new ID automatically. HR accounts only — returns {"error": ...} otherwise."""
        try:
            return add_employee(employee)
        except ForbiddenError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def update_employee_tool(emp_id: int, updates: dict):
        """Update one or more fields on an existing employee, identified by emp_id. `updates` is a dict of only the fields to change. HR accounts only — returns {"error": ...} otherwise."""
        try:
            return update_employee(emp_id, updates)
        except ForbiddenError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def delete_employee_tool(emp_id: int):
        """Permanently remove an employee record by ID. Returns true if deleted, false if no matching employee was found, or {"error": ...} if not permitted. HR accounts only."""
        try:
            return delete_employee(emp_id)
        except ForbiddenError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def list_all_leave_balances_tool():
        """Returns the leave balance for every employee in one call: a list of {id, name, leave_balance}. Use this whenever the user asks for leave balances in bulk (e.g. "leave balances of employees", "who has the most leave left") instead of calling get_employee_tool in a loop. Non-HR users only see their own entry here."""
        employees = list_employees()
        return [{"id": e["id"], "name": e["name"], "leave_balance": e.get("leave_balance")} for e in employees]