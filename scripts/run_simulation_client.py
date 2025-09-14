import json
import os
from pathlib import Path
from web_app import app

from scripts.render_sim_chart import render_sim_chart

import json
import os
from pathlib import Path
from web_app import app

from scripts.render_sim_chart import render_sim_chart

ROOT = Path('.')
SAMPLE = ROOT / 'sample_trades_TEST.csv'
assert SAMPLE.exists(), 'sample CSV missing'

client = app.test_client()
with open(SAMPLE, 'rb') as f:
    rv = client.post('/upload_tradelist', data={
        'file': (f, SAMPLE.name),
        'symbol': 'TEST',
        'strategy': 'demo',
        'date_parse_mode': 'default',
        'drop_incomplete': 'on'
    }, content_type='multipart/form-data')
    print('upload status', rv.status_code)
    print(rv.get_json())

# now call simulate
payload = {
    'symbol': 'TEST',
    'strategy': 'demo',
    'tp_levels': [1,2,5],
    'sl': -2,
    'trailing_stop': 0,
    'break_even_trigger': 0,
    'break_even_sl': 0
}
rv = client.post('/simulate', json=payload)
print('simulate status', rv.status_code)
resp = rv.get_json()
print(json.dumps(resp, indent=2))

# save JSON result to repo root
out_json = ROOT / 'simulate_result.json'
out_json.write_text(json.dumps(resp, indent=2), encoding='utf-8')
print('Created', out_json)

# Render chart to repo root
out_png = ROOT / 'simulate_cumulative.png'
try:
    render_sim_chart(resp, out_png)
    print('Created', out_png)
except Exception as e:
    print('Chart render failed:', e)

# Create short text report
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
