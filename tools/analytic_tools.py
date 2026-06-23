
from services.analytic_service import *


def register(mcp):
    """Register analytic tools on the given MCP registry.

    Args:
        mcp: Registry object that provides a `tool()` decorator. Example:
            register(mcp) where `mcp.tool()` is used to decorate functions.
    """

    @mcp.tool()
    def employee_count_tool():
        """Tool to get employee count.

        Returns:
            The result of employee_count() from services.analytic_service.

        Sample usage:
            result = employee_count_tool()
        """
        return employee_count()

    @mcp.tool()
    def department_summary_tool():
        """Tool to get department summary.

        Returns:
            The result of department_summary() from services.analytic_service.

        Sample usage:
            summary = department_summary_tool()
        """
        return department_summary()

    @mcp.tool()
    def list_reports_tool():
        """Tool to return saved summary reports."""
        return list_reports()

    @mcp.tool()
    def save_summary_report_tool(title: str, summary: str):
        """Tool to save a summary report."""
        return save_summary_report(title, summary)
