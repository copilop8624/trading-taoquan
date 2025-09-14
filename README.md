<<<<<<< HEAD
Backtest Toolkit
=================

This small toolkit automates candle updates, tradelist merging and running simple simulations.

Requirements
------------
- Python 3.8+
- See `requirements.txt` (pandas, numpy, ccxt, pyyaml, requests, tqdm)

Quick start
-----------
1. Create a virtualenv and install requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Edit `config.json` to list symbols/timeframes and directories.

3. Run full workflow:

```powershell
python -m src.run_backtest --config config.json
```

How it works
------------
- On startup the tool updates candle CSVs by appending only missing candles using the Binance API (via `ccxt`).
- Uploaded tradelists are merged into `tradelists/<strategy>_<symbol>.csv`, appending only new trades by timestamp+side.
- Simulation results are saved to `results/<symbol>_<timeframe>_<strategy>_<timestamp>.csv`.

Extending
---------
- Replace `src/simulator.py` with your real backtesting engine.
- Add more symbols/timeframes in `config.json`.

Demo & CI
---------

This repo also includes a lightweight Flask demo (`web_app.py`) and a small HTTP client that runs Version3 realistic simulations and writes reproducible artifacts. Artifacts are written to `screenshots/<tag>/` and `reports/<tag>/` and are excluded from git via `.gitignore`.

To run the demo locally (example, PowerShell):

```powershell
.\.venv_new\Scripts\Activate.ps1
Start-Process -FilePath .\.venv_new\Scripts\python.exe -ArgumentList 'web_app.py' -WorkingDirectory (Resolve-Path .).Path -PassThru
.\.venv_new\Scripts\python.exe .\scripts\run_simulation_http_client.py -t demo_run --record-env
```

A GitHub Actions workflow is added at `.github/workflows/smoke_test.yml` to run the smoke test on push using Python 3.10 and cache pip dependencies.
=======
# trading-taoquan
>>>>>>> origin/main
