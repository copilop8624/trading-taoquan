import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
import requests

ROOT = Path('.')
def make_output_dirs(tag: str | None = None):
    if tag:
        name = tag
    else:
        name = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')
    screenshots = ROOT / 'screenshots' / name
    reports = ROOT / 'reports' / name
    screenshots.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    return screenshots, reports
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

def render_and_report(resp, tag: str | None = None):
    # create timestamped output dirs (or use tag)
    screenshots_dir, reports_dir = make_output_dirs(tag)
    # save JSON
    out_json = reports_dir / 'simulate_result.json'
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
        out_png = screenshots_dir / 'simulate_cumulative.png'
        render_sim_chart(resp, out_png)
        print('Created', out_png)
    except Exception as e:
        print('Chart render failed:', e)
    # write report
    out_report = reports_dir / 'simulate_report.txt'
    with open(out_report, 'w', encoding='utf-8') as f:
        summary = resp.get('summary', {})
        f.write(f"total PnL: {summary.get('pnl_total')}\n")
        f.write(f"trade count: {summary.get('trade_count')}\n")
        f.write(f"winrate: {summary.get('winrate')}\n\n")
        f.write('Per-trade summary:\n')
        for d in resp.get('details', []):
            f.write(f"entryDt={d.get('entryDt')}, exitDt={d.get('exitDt')}, entryPrice={d.get('entryPrice')}, exitPrice={d.get('exitPrice')}, pnlPct={d.get('pnlPct')}, exitType={d.get('exitType')}\n")
    print('Created', out_report)
    # Log created folder paths
    print('Outputs written to:')
    print(' - screenshots:', screenshots_dir)
    print(' - reports:  ', reports_dir)

def main(argv=None):
    parser = argparse.ArgumentParser(description='HTTP simulation client')
    parser.add_argument('-t', '--tag', help='Custom output folder tag (overrides UTC timestamp)')
    parser.add_argument('--skip-upload', action='store_true', help='Skip upload step (assumes tradelist already uploaded)')
    args = parser.parse_args(argv)

    print('Uploading tradelist to', BASE)
    if not args.skip_upload:
        up = upload_tradelist()
        print('Upload response:', up.get('success', up))
        time.sleep(1)
    else:
        print('Skipping upload step (per --skip-upload)')

    print('Calling simulate...')
    resp = call_simulate()
    print('Simulate returned, success=', resp.get('success'))
    render_and_report(resp, args.tag)

if __name__ == '__main__':
    main()
