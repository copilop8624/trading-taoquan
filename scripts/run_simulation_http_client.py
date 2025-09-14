from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path('.')
SAMPLE = ROOT / 'sample_trades_TEST.csv'
BASE = os.environ.get('SIM_BASE_URL', 'http://127.0.0.1:5000')


def make_output_dirs(tag: str | None = None):
    name = tag if tag else datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M%S')
    screenshots = ROOT / 'screenshots' / name
    reports = ROOT / 'reports' / name
    screenshots.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    return screenshots, reports


def upload_tradelist(timeout=60):
    url = f"{BASE.rstrip('/')}/upload_tradelist"
    if not SAMPLE.exists():
        raise FileNotFoundError(f"Sample tradelist not found: {SAMPLE}")
    with open(SAMPLE, 'rb') as f:
        files = {'file': (SAMPLE.name, f, 'text/csv')}
        data = {'symbol': 'TEST', 'strategy': 'demo', 'date_parse_mode': 'default', 'drop_incomplete': 'on'}
        r = requests.post(url, files=files, data=data, timeout=timeout)
    r.raise_for_status()
    return r.json()


def call_simulate(timeout=120):
    url = f"{BASE.rstrip('/')}/simulate"
    payload = {
        'symbol': 'TEST',
        'strategy': 'demo',
        'tp_levels': [1, 2, 5],
        'sl': -2,
        'trailing_stop': 0,
        'break_even_trigger': 0,
        'break_even_sl': 0,
    }
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def render_sim_chart_from_path(resp, out_png: Path):
    # import renderer by path to avoid package issues
    import importlib.util

    renderer_path = Path(__file__).parent / 'render_sim_chart.py'
    spec = importlib.util.spec_from_file_location('render_sim_chart', str(renderer_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    render_sim_chart = getattr(module, 'render_sim_chart')
    render_sim_chart(resp, out_png)


def write_outputs(resp, tag: str | None = None, run_cmd: str | None = None, record_env: bool = False):
    screenshots_dir, reports_dir = make_output_dirs(tag)
    # write json
    out_json = reports_dir / 'simulate_result.json'
    out_json.write_text(json.dumps(resp, indent=2), encoding='utf-8')
    print('Created', out_json)
    # render chart
    try:
        out_png = screenshots_dir / 'simulate_cumulative.png'
        render_sim_chart_from_path(resp, out_png)
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

    # automatic run_info
    try:
        venv = os.environ.get('VIRTUAL_ENV') or os.environ.get('CONDA_PREFIX') or ''
        pyver = sys.version.replace('\n', ' ')
        osinfo = f"{platform.system()} {platform.release()} ({platform.machine()})"
        utc_ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
        # exact command used (best available)
        cmd = run_cmd or shlex.join(sys.argv)
        log_lines = [
            f"Command: {cmd}",
            f"UTC: {utc_ts}",
            f"Tag: {tag or ''}",
            "",
            "Environment:",
            f"Python: {pyver}",
            f"Venv: {venv}",
            f"OS: {osinfo}",
        ]
        req_file = None
        if record_env:
            try:
                pip_out = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], stderr=subprocess.DEVNULL, timeout=60)
                pip_text = pip_out.decode('utf-8', errors='replace')
                log_lines.append('')
                log_lines.append('pip freeze:')
                log_lines.extend(pip_text.splitlines())
                # also save a requirements snapshot
                ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                req_file = reports_dir / f'requirements-{ts}.txt'
                req_file.write_text(pip_text, encoding='utf-8')
                print('Wrote requirements snapshot:', req_file)
            except Exception as e:
                log_lines.append('')
                log_lines.append(f'pip freeze failed: {e}')

        run_info = '\n'.join(log_lines) + '\n'
        run_file = reports_dir / 'run_info.txt'
        run_file.write_text(run_info, encoding='utf-8')
        print('Wrote run log:', run_file)
        env_recorded = 'yes' if record_env else 'no'
    except Exception as e:
        print('Failed to write run_info:', e)
        env_recorded = 'no'

    print('Outputs written to:')
    print(' - screenshots:', screenshots_dir.resolve())
    print(' - reports:  ', reports_dir.resolve())
    return screenshots_dir.resolve(), reports_dir.resolve()


def main(argv=None):
    parser = argparse.ArgumentParser(description='HTTP simulation client')
    parser.add_argument('-t', '--tag', help='Custom output folder tag (overrides UTC timestamp)')
    parser.add_argument('--skip-upload', action='store_true', help='Skip upload step (assumes tradelist already uploaded)')
    parser.add_argument('--record-env', action='store_true', help='Record environment (pip freeze) into run_info and a requirements snapshot')
    args = parser.parse_args(argv)

    if not args.skip_upload:
        print('Uploading tradelist to', BASE)
        up = upload_tradelist()
        print('Upload response:', up.get('success', up))
        time.sleep(1)
    else:
        print('Skipping upload step (per --skip-upload)')

    print('Calling simulate...')
    resp = call_simulate()
    print('Simulate returned, success=', resp.get('success'))
    run_cmd = shlex.join(sys.argv)
    screenshots_dir, reports_dir = write_outputs(resp, args.tag, run_cmd=run_cmd, record_env=args.record_env)
    # print a short confirmation
    print(f"Run completed. Log: {reports_dir / 'run_info.txt'} | UTC: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')} | env_recorded={ 'yes' if args.record_env else 'no' }")


if __name__ == '__main__':
    main()
