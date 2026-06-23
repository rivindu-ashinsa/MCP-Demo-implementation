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
┌──────────────┐      HTTP       ┌──────────────────┐      stdio       ┌────────────────────┐
│  Chat UI     │ ───────────────▶│  FastAPI backend  │ ───────────────▶│  MCP server         │
│ (static/)    │ ◀─────────────── │  (app/main.py)    │ ◀───────────────│  (mcp_server/)      │
└──────────────┘   JSON / PDF     └──────────────────┘    tool calls    └────────────────────┘
                                          │                                       │
                                          ▼                                       ▼
                                   Groq LLM (LangChain)                  services/ + tools/
                                   plans which tool(s)                   employee, department,
                                   to call                               leave, report logic
```

1. The browser sends a chat message to `POST /chat`.
2. FastAPI hands the message to an `MCPAgent` (from [`mcp_use`](https://github.com/mcp-use/mcp-use)), backed by a Groq LLM (`llama-3.1-8b-instant` via `langchain_groq`).
3. The agent connects over **stdio** to the MCP server (`mcp_server/server.py`), which exposes tools for employees, departments, leave, and PDF report generation.
4. The agent decides which tool(s) to call, the MCP server runs them against the JSON data file, and the result is returned as a chat reply — including a download link when a PDF report is generated.

---

## Project structure

```
MCP-DEMO/
├── app/
│   └── main.py                  # FastAPI app: /chat, /summary, /health, static + report file serving
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
├── static/                      # Frontend — plain HTML/CSS/JS, no build step
│   ├── index.html
│   ├── style.css
│   └── chat.js
│
├── client/
│   └── test_client.py           # Standalone script for testing the MCP server directly
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

### 3. Verify the MCP server starts cleanly (optional but recommended)

```bash
uv run --with mcp[cli] mcp run mcp_server/server.py
```

If this exits immediately or throws an import error, fix that before starting the backend — the FastAPI app will fail in the same way, just with a less direct error message.

### 4. Run the backend

```bash
uv run uvicorn app.main:app --reload
```

### 5. Open the app

Go to **http://localhost:8000/** in your browser. The chat UI is served directly by FastAPI — no separate frontend server needed.

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

Plain HTML/CSS/JS — no framework, no build step, no bundler. Markdown-style formatting from the LLM (`**bold**`, `` `code` ``, `[text](url)`) is rendered via a small in-house parser in `chat.js` rather than raw-displayed.

---

## Known limitations

- **Small/fast LLM (`llama-3.1-8b-instant`)** trades reliability for speed. It handles single, clearly-scoped tool calls well, but can struggle with multi-step planning or precise output formatting (e.g. transcribing a URL exactly). Where this matters — like the report download link — prefer extracting structured data server-side over trusting the model to repeat it verbatim.
- **`data/employees.json` is a flat file**, not a real database — fine for a demo, not for concurrent writes for production use.
- **No authentication** on any endpoint.

---

## Troubleshooting

**MCP server won't start / `/chat` returns 500 immediately on startup:**
Run `uv run --with mcp[cli] mcp run mcp_server/server.py` directly to see the real traceback — FastAPI's logs often just say "the underlying process closed the connection during initialization" without the actual cause.

**A generated PDF 404s when opened:**
Check that `REPORTS_DIR` in `app/main.py` and `BASE_DIR` in `services/report_service.py` resolve to the *same* folder. Both should point at the project root's `reports/` directory, not a subfolder.

**The agent loops through unrelated tools before answering:**
Usually means the LLM doesn't have a clear single-tool path to the answer. Check whether a bulk/aggregate tool exists for the request type, and make sure tool docstrings are specific enough to discourage wandering into unrelated tools.