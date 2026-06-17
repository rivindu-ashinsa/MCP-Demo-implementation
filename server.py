
from mcp.server.fastmcp import FastMCP
from tools import employee_tools, department_tools, analytic_tools, leave_tools


mcp = FastMCP("Employee Management MCP - DEMO ")

employee_tools.register(mcp)
department_tools.register(mcp)
analytic_tools.register(mcp)
leave_tools.register(mcp)


if __name__ == "__main__":
    mcp.run()