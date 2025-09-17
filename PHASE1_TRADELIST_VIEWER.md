# Phase 1: Tradelist Viewer

This document describes the stable features implemented for the Tradelist Viewer and how to install, run, and try the viewer locally.

## What is stable (features)
- **Backend `/upload_tradelist` endpoint:** accepts CSV uploads with form fields `symbol`, `strategy`, `date_parse_mode`, and `drop_incomplete`. Always returns a JSON payload containing `success`, `rows_added`, `final_count`, `preview` (head rows), `labels` (may include nulls), `cumulative`, `drawdown`, `winrate`, `warnings` (list), and `strategy` (echoed back; defaults to `"default"`).
- **Preview rendering:** the dashboard shows an inline preview table of uploaded rows (preserves missing values and non-numeric cells in the preview exactly as received).
- **Chart.js rendering:** previewed series (cumulative/drawdown/winrate) are rendered using Chart.js. Missing timestamps are represented as null points so the chart correctly skips them.
- **Warnings & validation:** the backend detects common issues (e.g., non-numeric `pnl` values, missing timestamps) and returns warnings which are displayed in the UI.
- **LocalStorage persistence:** per-symbol+strategy upload options are saved using keys `parseMode_<symbol>_<strategy>` and `dropIncomplete_<symbol>_<strategy>`. Reset clears these keys for the current symbol/strategy.

## Remaining polish items (optional / future work)
- Add/clean UX for the 'Dropped from chart' marker in the preview table (more descriptive badge and tooltip).
- Chart tooltip improvements to highlight which points were dropped due to missing timestamps.
- Improve preview table formatting and column width responsiveness for large rows.
- Add per-symbol UI to manage saved defaults (list saved strategies and defaults per symbol).
- Stabilize and enable automated Playwright UI tests (fixture currently launches the server but `pytest-playwright` must be installed and Playwright browsers installed). See below for test instructions.

## Install & Run (Windows + venv)
1. Create and activate the virtual environment (if not already present):

```powershell
python -m venv .venv_new
. .\.venv_new\Scripts\Activate.ps1
```

2. Install Python dependencies:

```powershell
. .venv_new\Scripts\python.exe -m pip install -r requirements.txt
```

3. Run the app (development):

```powershell
. .venv_new\Scripts\python.exe web_app.py --port 8000
```

4. Open the dashboard in your browser:

```
http://127.0.0.1:8000/dashboard
```

## Sample usage
- Use the permanent upload form near the top of the dashboard.
- Example CSV: `sample_trades_TEST.csv` (placed at repository root) contains rows with a missing timestamp and a non-numeric `pnl` cell to demonstrate warnings and dropped-from-chart handling.
- After upload the UI will show preview rows, warnings, and a Chart.js visualization. If `drop_incomplete` is enabled the chart will omit rows missing valid timestamps and the preview shows a 'Dropped from chart' marker.

## Running automated UI test (optional)
To run the Playwright test, install the pytest-playwright plugin and browsers in your project venv:

```powershell
. .venv_new\Scripts\python.exe -m pip install pytest-playwright
. .venv_new\Scripts\python.exe -m playwright install chromium
```

Then run the single UI test:

```powershell
. .venv_new\Scripts\python.exe -m pytest tests/test_ui_upload.py -k test_permanent_upload_form -q
```

If the Playwright fixtures are unavailable, install `pytest-playwright` as above. The test starts the server automatically and saves a screenshot at `tests/screenshots/upload_result_demo.png` on success.

## Notes & Troubleshooting
- If server startup prints Unicode characters and fails on Windows console, make sure the environment uses UTF-8. The test fixture sets `PYTHONIOENCODING=utf-8` when launching the server subprocess. You can also run PowerShell with UTF-8 enabled or set the environment variable in the shell.
- If the dev server port `8000` is in use, change the `--port` argument and open the corresponding URL.

---
Phase 1 is considered complete for the Viewer; next steps are optional UX polish and enabling CI-run Playwright tests.
