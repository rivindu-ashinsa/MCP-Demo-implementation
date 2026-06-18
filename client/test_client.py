import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():

    # absolute path to server.py (IMPORTANT)
    server_path = Path(__file__).parent.parent / "server.py"

    if not server_path.exists():
        raise FileNotFoundError(f"Server not found at {server_path}")

    # IMPORTANT: use same python as venv
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
    )

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):

            async with ClientSession(read_stream, write_stream) as session:

                await session.initialize()

                print("\n=== TOOLS ===")
                tools = await session.list_tools()
                for tool in tools:
                    print(tool)
                # print(tools)

                # print("\n=== CALL TOOL ===")
                # result = await session.call_tool(
                #     "get_employee_tool",
                #     {"emp_id": 1}
                # )

                # print(result)

    except Exception as e:
        print("\nCLIENT ERROR:", repr(e))


if __name__ == "__main__":
    asyncio.run(main())