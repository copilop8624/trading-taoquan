import os
import subprocess
import time
from pathlib import Path

ROOT = Path('.').resolve()
# Determine a Python executable to use. Prefer environment override, then system python,
# then fallback to a local `.venv_new` (Windows or Unix layout). This makes the script
# robust in CI where a project virtualenv may not exist.
import shutil

def find_python():
    # Allow explicit override
    env_py = os.environ.get('PYTHON')
    if env_py:
        return env_py
    # Prefer the Python used to run this script (if available)
    try:
        import sys
        if sys.executable:
            return sys.executable
    except Exception:
        pass
    # Fallback to PATH lookup
    for name in ('python', 'python3'):
        p = shutil.which(name)
        if p:
            return p
    # Fallback to .venv_new layout — prefer platform-appropriate layout
    if os.name == 'nt':
        # Windows: Scripts\python.exe
        v_primary = ROOT / '.venv_new' / 'Scripts' / 'python.exe'
        v_secondary = ROOT / '.venv_new' / 'bin' / 'python'
    else:
        # Unix-like: bin/python
        v_primary = ROOT / '.venv_new' / 'bin' / 'python'
        v_secondary = ROOT / '.venv_new' / 'Scripts' / 'python.exe'

    if v_primary.exists():
        return str(v_primary)
    if v_secondary.exists():
        return str(v_secondary)
    raise SystemExit('No python executable found; set PYTHON env or install python')

PY = find_python()
TAG = 'smoke_test'

# Start server
p = subprocess.Popen([str(PY), 'web_app.py'], cwd=str(ROOT))
print('Started server PID', p.pid)

# wait for /health
import requests
for i in range(60):
    try:
        r = requests.get('http://127.0.0.1:5000/health', timeout=2)
        if r.status_code == 200:
            print('Server healthy')
            break
    except Exception:
        time.sleep(1)
else:
    p.terminate()
    raise SystemExit('Server did not become healthy')

# Run client
cmd = [str(PY), str(ROOT / 'scripts' / 'run_simulation_http_client.py'), '-t', TAG, '--record-env']
print('Running client:', ' '.join(cmd))
subprocess.check_call(cmd, cwd=str(ROOT))

# Verify files
screens = ROOT / 'screenshots' / TAG
reports = ROOT / 'reports' / TAG
assert screens.exists() and any(screens.iterdir()), 'No screenshots'
assert reports.exists() and any(reports.iterdir()), 'No reports'
print('Smoke test passed. Files created:')
for f in reports.iterdir():
    print(' -', f)
for f in screens.iterdir():
    print(' -', f)

# cleanup: leave server running (user may want it)
print('Smoke test complete')
