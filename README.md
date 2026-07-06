# Personnel Desk — MCP Employee Management Demo

A small HR assistant that lets you ask natural-language questions about employees, departments, and leave balances, and generate one-page PDF summary reports — backed by an [MCP](https://modelcontextprotocol.io/) server and a Groq-powered LangChain agent, with a lightweight web chat UI.

```
"how many departments are there?"        → 2 (Engineering, HR)
"leave balance for emp 1"                → 5 days
"generate summary report for emp 1"      → downloadable PDF
```

---

## How it works

```
┌──────────────┐      HTTP       ┌──────────────────┐      HTTP       ┌────────────────────┐
│  Chat UI     │ ───────────────▶│  FastAPI backend  │ ───────────────▶│  MCP server         │
│(frontend/)   │ ◀─────────────── │  (app/main.py)    │ ◀───────────────│  (mcp_server/)      │
└──────────────┘   JSON / PDF     └──────────────────┘    tool calls    └────────────────────┘
                                          │                                       │
                                          ▼                                       ▼
                                   Groq LLM (LangChain)                  services/ + tools/
                                   plans which tool(s)                   employee, department,
                                   to call                               leave, report logic
```

1. The browser sends a chat message to `POST /chat`.
2. FastAPI hands the message to an `MCPAgent` (from [`mcp_use`](https://github.com/mcp-use/mcp-use)), backed by a Groq LLM (`openai/gpt-oss-safeguard-20b` via `langchain_groq`).
3. The agent connects over **HTTP** to the MCP server (`mcp_server/server.py`), which is automatically started by FastAPI's lifespan handler on app startup (controlled by `MCP_SERVER_AUTOSTART` env var).
4. The agent forwards the user's JWT bearer token to the MCP server, which uses `TenantContextMiddleware` to scope all tool calls to the authenticated user's company and role.
5. The MCP server runs the appropriate tools against the data/database, and the result is returned as a chat reply — including a download link when a PDF report is generated.

---

## Project structure

```
MCP-DEMO/
├── app/
│   └── main.py                  # FastAPI app: /chat, /summary, /health, static + report file serving
│
├── db/
│   ├── base.py
│   ├── models.py
│   └── session.py               # Database setup, sessions, and seed helpers
│
├── mcp_server/
│   └── server.py                # MCP server entrypoint — registers all tools, prompts, resources
│
├── services/                    # Plain Python — no MCP/agent code, just data logic
│   ├── employee_service.py      # CRUD over data/employees.json
│   ├── department_service.py    # Department lookups + reassignment
│   ├── leave_service.py         # Leave balance + leave application
│   ├── analytic_service.py      # Aggregate stats (headcounts, summaries)
│   └── report_service.py        # Fixed-layout one-page PDF generator (reportlab)
│
├── tools/                       # MCP tool wrappers — one @mcp.tool() per service function
│   ├── employee_tools.py
│   ├── department_tools.py
│   ├── leave_tools.py
│   ├── analytic_tools.py
│   └── report_tools.py
│
├── prompts/
│   ├── one_page_summary_prompt.txt   # Used by /summary endpoint
│   ├── employee_summary_prompt.txt   # Strict reply-format instructions for PDF report requests
│   └── report_prompts.py             # @mcp.prompt() — MCP-native prompt registration
│
├── resources/
│   └── company_docs.py          # @mcp.resource() — leave policy & company policy text
│
├── data/
│   └── employees.json           # The "database" — flat JSON file
│
├── reports/                     # Generated PDF reports land here at runtime (gitignored)
│
├── repositories/                # Repository layer for database-backed access
│   ├── base.py
│   ├── company_repository.py
│   ├── employee_repository.py
│   └── user_repository.py
│
├── frontend/                    # Svelte + Vite frontend source
│   ├── index.html
│   ├── package.json
│   ├── svelte.config.js
│   ├── vite.config.js
│   └── src/
│       ├── App.svelte
│       ├── main.js
│       └── lib/
│           ├── auth.js
│           ├── ChatPanel.svelte
│           ├── Dashboard.svelte
│           ├── Login.svelte
│           └── Register.svelte

├── static/                      # Legacy fallback frontend assets
│   ├── index.html
│   ├── style.css
│   └── chat.js
│
├── server/                      # Server-side helpers and runtime support
│
├── server.json                  # MCP client config (points at mcp_server/server.py)
├── pyproject.toml
├── .env                         # GROQ_API_KEY (not committed)
└── .gitignore
```

---

## Setup

### Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- A [Groq API key](https://console.groq.com/keys)

### 1. Install dependencies

```bash
cd MCP-DEMO
uv sync
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Run the backend

```bash
uv run uvicorn app.main:app --reload
```

The FastAPI app will automatically start the MCP server on `127.0.0.1:8765` during startup (controlled by `MCP_SERVER_AUTOSTART=true` in `.env`). To disable autostart and run the MCP server separately in another terminal:

```bash
# Terminal 1: Backend only (autostart disabled)
MCP_SERVER_AUTOSTART=false uv run uvicorn app.main:app --reload

# Terminal 2: MCP server (manual)
uv run python mcp_server/server.py
```

### 4. Open the app

Go to **http://localhost:8000/** in your browser. The chat UI is served directly by FastAPI — no separate frontend server needed.

### 5. Frontend development (optional)

The main UI now lives in `frontend/` as a Svelte app.

```bash
cd frontend
npm install
npm run dev
```

For production or to serve the Svelte build through FastAPI, run:

```bash
cd frontend
npm run build
```

FastAPI will serve `frontend/dist/` from `/` when that build output exists.

---

## Available tools

| Tool | Description |
|---|---|
| `get_employee_tool` | Look up one employee by ID |
| `list_employees_tool` | List all employees |
| `search_employee_tool` | Find employees by name (partial match) |
| `add_employee_tool` | Create a new employee |
| `update_employee_tool` | Update fields on an existing employee |
| `delete_employee_tool` | Remove an employee |
| `list_all_leave_balances_tool` | Leave balances for every employee in one call |
| `get_department_tool` | Department name for one employee |
| `list_departments_tool` | List all department names |
| `update_department_tool` | Move an employee to a different department |
| `get_leave_balance_tool` | Leave balance for one employee |
| `apply_leave_tool` | Deduct leave days from an employee's balance |
| `department_summary_tool` | Headcount per department |
| `employee_count_tool` | Total employee count |
| `generate_employee_summary_report_tool` | Generate a one-page PDF report for one employee, returns a download URL |

Tool docstrings are written specifically to help the LLM choose the right tool — particularly to prevent bulk requests ("leave balances of employees") from being mishandled one-at-a-time or hallucinated.

---

## PDF report generation

Reports are built with `reportlab`'s `Canvas` API using **fixed absolute coordinates**, not flowing text — every report has identical structure (header, identity block, leave section, footer) regardless of content. Long values are truncated with an ellipsis rather than allowed to overflow or reshape the layout.

- Generated files are saved to `reports/` at the project root.
- `app/main.py` mounts that folder at `/reports`, so a generated file `employee_summary_1_<timestamp>.pdf` is reachable at `http://localhost:8000/reports/employee_summary_1_<timestamp>.pdf`.
- The chat UI detects a `/reports/*.pdf` path in the assistant's reply and renders a **Download report (PDF)** button instead of showing the raw path.

To change the report template, edit the coordinates and styles in `services/report_service.py`. Every report generated afterward will reflect the new layout — there's no per-report variation.

---

## Frontend

The active UI is a Svelte component in `frontend/src/App.svelte`. It still uses the same lightweight markdown-safe rendering rules as the original chat UI, but the markup, behavior, and styles now live together in the component instead of separate HTML/CSS/JS files.

---

## Known limitations

- **Small/fast LLM (`llama-3.1-8b-instant`)** trades reliability for speed. It handles single, clearly-scoped tool calls well, but can struggle with multi-step planning or precise output formatting (e.g. transcribing a URL exactly). Where this matters — like the report download link — prefer extracting structured data server-side over trusting the model to repeat it verbatim.
- **`data/employees.json` is a flat file**, not a real database — fine for a demo, not for concurrent writes for production use.
- **No authentication** on any endpoint.

---

## Troubleshooting

**MCP server won't start / `/chat` returns 500 immediately on startup:**
The MCP server is started automatically as a subprocess by FastAPI during lifespan startup. Check the console logs from `uvicorn app.main:app --reload` for any errors from the MCP process. If you see connection errors, verify that port 8765 is available and not already in use. You can also set `MCP_SERVER_AUTOSTART=false` and run the server manually in a separate terminal to see more detailed error output:
```bash
python mcp_server/server.py
```

**A generated PDF 404s when opened:**
Check that `REPORTS_DIR` in `app/main.py` and `BASE_DIR` in `services/report_service.py` resolve to the *same* folder. Both should point at the project root's `reports/` directory, not a subfolder.

**The agent loops through unrelated tools before answering:**
Usually means the LLM doesn't have a clear single-tool path to the answer. Check whether a bulk/aggregate tool exists for the request type, and make sure tool docstrings are specific enough to discourage wandering into unrelated tools.