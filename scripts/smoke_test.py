import os
import subprocess
import time
from pathlib import Path

ROOT = Path('.').resolve()
PY = ROOT / '.venv_new' / 'Scripts' / 'python.exe'
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
