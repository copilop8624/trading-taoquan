How to run the demo client and where outputs go

Start Flask server
- Activate your virtualenv and start the server from the repository root:

```powershell
# from repo root
.\.venv_new\Scripts\python.exe web_app.py
```

Run the HTTP simulation client
- The client uploads `sample_trades_TEST.csv` to the running Flask server and triggers `/simulate`.

```powershell
$Env:SIM_BASE_URL = 'http://127.0.0.1:5000'
.\.venv_new\Scripts\python.exe .\scripts\run_simulation_http_client.py
```

Where outputs are stored
- Each run creates a timestamped subfolder under:
  - `screenshots/<YYYY-MM-DD_HHMMSS>/` — contains `simulate_cumulative.png`
  - `reports/<YYYY-MM-DD_HHMMSS>/` — contains `simulate_result.json` and `simulate_report.txt`

Notes
- The README assumes a Windows PowerShell environment and a venv located at `./.venv_new/`.
- The scripts do not modify `web_app.py` or any core simulation logic; they only call the existing endpoints.
