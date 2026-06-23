"""
report_prompts.py

MCP prompt for generating a one-page employee summary PDF report.
Registered as a proper @mcp.prompt() so MCP-aware clients can discover
and invoke it directly, rather than relying on free-text instructions
glued into the chat message.
"""


def register(mcp):
    @mcp.prompt()
    def employee_summary_report(emp_id: str) -> str:
        """
        Generate a one-page PDF summary report for a specific employee.

        Args:
            emp_id: The numeric ID of the employee to generate a report for.
        """
        return f"""You are generating a one-page summary report for employee ID {emp_id}.

Follow these steps exactly:

1. Call `generate_employee_summary_report_tool` exactly once with emp_id={emp_id}.
2. As soon as that tool returns a result containing `report_url`, STOP calling tools. Do not call any other tool afterward (including save_summary_report_tool, list_reports_tool, or any analytics tool) — the report is already complete and saved to disk by that single call.
3. Reply to the user with exactly this format, nothing else:

Report generated for [employee name]. Download: [report_url]

Replace [employee name] and [report_url] with the real values from the tool result. Copy the report_url character-for-character — do not paraphrase it, describe it, or mention the filename instead. The user's interface only renders a download button when the literal report_url string appears in your reply, so omitting or rewording it breaks the feature.
"""