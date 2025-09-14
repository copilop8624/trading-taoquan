import os
import sys
import json
import time
from pathlib import Path
import requests

ROOT = Path('.')
SAMPLE = ROOT / 'sample_trades_TEST.csv'
assert SAMPLE.exists(), 'sample CSV missing'

BASE = os.environ.get('SIM_BASE_URL', 'http://127.0.0.1:5000')

def upload_tradelist():
    url = f"{BASE.rstrip('/')}/upload_tradelist"
    with open(SAMPLE, 'rb') as f:
        files = {'file': (SAMPLE.name, f, 'text/csv')}
        data = {'symbol': 'TEST', 'strategy': 'demo', 'date_parse_mode': 'default', 'drop_incomplete': 'on'}
        r = requests.post(url, files=files, data=data, timeout=60)
    r.raise_for_status()
    return r.json()

def call_simulate():
    url = f"{BASE.rstrip('/')}/simulate"
    payload = {
        'symbol': 'TEST',
        'strategy': 'demo',
        'tp_levels': [1,2,5],
        'sl': -2,
        'trailing_stop': 0,
        'break_even_trigger': 0,
        'break_even_sl': 0
    }
    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()

def render_and_report(resp):
    # save JSON
    out_json = ROOT / 'simulate_result.json'
    out_json.write_text(json.dumps(resp, indent=2), encoding='utf-8')
    print('Created', out_json)
    # render chart
    try:
        # Import renderer by path to avoid package import issues
        import importlib.util
        renderer_path = Path(__file__).parent / 'render_sim_chart.py'
        spec = importlib.util.spec_from_file_location('render_sim_chart', str(renderer_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        render_sim_chart = getattr(module, 'render_sim_chart')
        out_png = ROOT / 'simulate_cumulative.png'
        render_sim_chart(resp, out_png)
        print('Created', out_png)
    except Exception as e:
        print('Chart render failed:', e)
    # write report
    out_report = ROOT / 'simulate_report.txt'
    with open(out_report, 'w', encoding='utf-8') as f:
        summary = resp.get('summary', {})
        f.write(f"total PnL: {summary.get('pnl_total')}\n")
        f.write(f"trade count: {summary.get('trade_count')}\n")
        f.write(f"winrate: {summary.get('winrate')}\n\n")
        f.write('Per-trade summary:\n')
        for d in resp.get('details', []):
            f.write(f"entryDt={d.get('entryDt')}, exitDt={d.get('exitDt')}, entryPrice={d.get('entryPrice')}, exitPrice={d.get('exitPrice')}, pnlPct={d.get('pnlPct')}, exitType={d.get('exitType')}\n")
    print('Created', out_report)

def main():
    print('Uploading tradelist to', BASE)
    up = upload_tradelist()
    print('Upload response:', up.get('success', up))
    time.sleep(1)
    print('Calling simulate...')
    resp = call_simulate()
    print('Simulate returned, success=', resp.get('success'))
    render_and_report(resp)

if __name__ == '__main__':
    main()
