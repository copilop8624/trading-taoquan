MCP Helper for local ChatGPT actions

This helper provides a controlled interface for running tests, reading/writing files, and making commits from the local workspace.

Files:
- `scripts/mcp_agent.py`: CLI helper. Writes audit entries to `mcp_audit.log`.

Security model:
- Operates only inside the repository root: `C:\Users\aio\OneDrive\Desktop\DATA TRADINGVIEW\backtest\BTC`.
- Does not access external system paths or secret stores.
- Git push is not performed by default; commits are local unless you add a separate push step and provide a token.

Usage examples:

Run tests:

```powershell
.venv_new\Scripts\python.exe scripts\mcp_agent.py run-tests
```

Read a file:

```powershell
.venv_new\Scripts\python.exe scripts\mcp_agent.py read-file templates\dashboard.html
```

Write a file (provide content in a temporary file):

```powershell
.venv_new\Scripts\python.exe scripts\mcp_agent.py write-file myfile.txt --content-file tmp.txt
```

Commit changes locally:

```powershell
.venv_new\Scripts\python.exe scripts\mcp_agent.py git-commit "Describe changes" --branch feature/mcp
```

Audit log:
- `mcp_audit.log` will contain JSON lines describing actions performed by the helper.
