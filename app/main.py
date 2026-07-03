import asyncio
import os
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from db.session import init_db, seed_default_accounts
from services.agent import initialize_agent, shutdown_agent
from routers import auth, employees, departments, chat

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_ROOT / "static"
FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
MCP_SERVER_AUTOSTART = os.getenv("MCP_SERVER_AUTOSTART", "true").lower() == "true"
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8765"))
MCP_SERVER_SCRIPT = PROJECT_ROOT / "mcp_server" / "server.py"


async def _wait_for_mcp_server(timeout_seconds: float = 10.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while True:
        try:
            reader, writer = await asyncio.open_connection(MCP_SERVER_HOST, MCP_SERVER_PORT)
        except OSError:
            if asyncio.get_running_loop().time() >= deadline:
                raise RuntimeError(
                    f"MCP server did not start listening on {MCP_SERVER_HOST}:{MCP_SERVER_PORT}"
                )
            await asyncio.sleep(0.2)
            continue

        writer.close()
        await writer.wait_closed()
        return


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_default_accounts()

    mcp_server_process = None
    if MCP_SERVER_AUTOSTART:
        mcp_server_process = subprocess.Popen(
            [sys.executable, str(MCP_SERVER_SCRIPT)],
            cwd=str(PROJECT_ROOT),
        )
        await _wait_for_mcp_server()

    await asyncio.to_thread(initialize_agent)
    yield
    await shutdown_agent()

    if mcp_server_process is not None and mcp_server_process.returncode is None:
        mcp_server_process.terminate()
        await asyncio.to_thread(mcp_server_process.wait)


app = FastAPI(
    title="Personnel Desk",
    description="Multi-tenant HR assistant: JWT auth + role-scoped data + MCP chat agent.",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(departments.router)
app.include_router(chat.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
if FRONTEND_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS_DIR)), name="frontend-assets")
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")


@app.get("/")
async def index():
    if FRONTEND_INDEX_FILE.exists():
        return FileResponse(str(FRONTEND_INDEX_FILE))
    return FileResponse(str(STATIC_DIR / "index.html"))