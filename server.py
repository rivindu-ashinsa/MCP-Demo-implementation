
from mcp.server.fastmcp import FastMCP
from tools import (employee_tools, department_tools, analytic_tools, leave_tools)


from resources.company_docs import (
    leave_policy,
    company_policy
)

mcp = FastMCP("Employee Management MCP - DEMO ")

employee_tools.register(mcp)
department_tools.register(mcp)
analytic_tools.register(mcp)
leave_tools.register(mcp)


    

@mcp.resource("company://leave-policy")
def leave_policy_resource():
    return leave_policy()


@mcp.resource("company://company-policy")
def company_policy_resource():
    return company_policy()



if __name__ == "__main__":
    mcp.run()