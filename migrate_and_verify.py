#!/usr/bin/env python3
# migrate_and_verify.py
# Senior Data/DevOps Engineer migration & E2E verify script

import os
import sys
import glob
import re
import json
import shutil
import sqlite3
import time
from datetime import datetime
import requests
import pandas as pd

# === Robust normalization functions (from web_app.py) ===
def normalize_symbol_and_timeframe(raw, default_timeframe='30m'):
    """
    Chuẩn hóa mọi kiểu symbol/timeframe đầu vào về tuple (symbol, timeframe)
    Hỗ trợ: có/không prefix sàn, có/không timeframe, mọi kiểu phân tách
    """
    s = str(raw).strip().upper()
    s = re.sub(r'^(BINANCE_|BYBIT_|OKX_)', '', s)
    symbol, timeframe = s, None
    # Ưu tiên tách theo dấu _, sau đó dấu cách
    if '_' in s:
        parts = s.split('_')
        if len(parts) == 2:
            symbol, timeframe = parts
    elif ' ' in s:
        parts = s.split()
        if len(parts) == 2:
            symbol, timeframe = parts
    # Nếu chưa có timeframe, kiểm tra hậu tố kiểu 30M, 60M, 1H...
    if timeframe is None:
        m = re.match(r'^([A-Z0-9]+)(\d{1,4}[A-Z]?)$', symbol)
        if m:
            symbol, timeframe = m.group(1), m.group(2)
    if timeframe is None:
        timeframe = default_timeframe
    return symbol, timeframe

def normalize_symbol_format(symbol, ensure_prefix=True):
    """
    Normalize symbol format for consistent handling across the application
    Args:
        symbol (str): Input symbol (e.g., 'BTCUSDT', 'BINANCE_BTCUSDT')
        ensure_prefix (bool): If True, ensures BINANCE_ prefix is present
                             If False, removes BINANCE_ prefix
    Returns:
        str: Normalized symbol format
    """
    if not symbol:
        return ""
    symbol = symbol.strip().upper()
    if ensure_prefix:
        # Ensure symbol has BINANCE_ prefix for internal processing
        if not symbol.startswith('BINANCE_'):
            return f"BINANCE_{symbol}"
        return symbol
    else:
        # Remove BINANCE_ prefix for display
        return symbol.replace('BINANCE_', '')

# ==== CONFIG (override by env/args if needed) ====
HOST = os.environ.get('HOST', 'http://localhost:5000')
DB_PATH = os.environ.get('DB_PATH', os.path.abspath('./candlestick_data.db'))
DATA_DIR = os.environ.get('DATA_DIR', os.path.abspath('./data'))
PAIRS = os.environ.get('PAIRS', 'BIOUSDT:30m').split(',')
BINANCE_DAYS = int(os.environ.get('BINANCE_DAYS', '365'))
REPORT_PATH = os.path.abspath('migration_report.json')

# ==== 1. Backup DB ====
def backup_db(db_path):
    if not os.path.exists(db_path):
        # Create empty DB
        conn = sqlite3.connect(db_path)
        conn.close()
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    backup_path = db_path.replace('.db', f'.backup_{ts}.db')
    shutil.copy2(db_path, backup_path)
    before_size = os.path.getsize(db_path)
    print(f"[INFO] DB backed up to {backup_path}, size={before_size} bytes")
    return before_size, backup_path

# ==== 2. Scan sources ====
def scan_sources(data_dir):
    sources = []
    # CSV
    for f in glob.glob(os.path.join(data_dir, '*.csv')):
        fname = os.path.basename(f)
        # Hỗ trợ các định dạng: BINANCE_SYMBOL.P, 30.csv | BINANCE_SYMBOL, 30.csv | BINANCE_SYMBOL_30.csv | ...
        # Cho phép cả dấu _ trước timeframe (ví dụ: BINANCE_1000PEPEUSDT.P_30.csv)
        m = re.match(r'(BINANCE_)?([A-Za-z0-9]+)(?:\.P)?[,_ ]*_*(\d+[a-zA-Z]*)\.csv', fname)
        if not m:
            print(f"  ⚠️ Cannot parse filename: {fname}")
            continue
        symbol_raw = m.group(2)
        tf_raw = m.group(3)
        # Normalize symbol and timeframe
        symbol = normalize_symbol_format(symbol_raw, ensure_prefix=True)
        tf_map = {"30": "30m", "60": "1h", "240": "4h", "1440": "1d"}
        timeframe = tf_map.get(tf_raw.lower(), tf_raw.lower())
        # Final normalization (handle edge cases)
        symbol, timeframe = normalize_symbol_and_timeframe(f"{symbol}_{timeframe}")
        sources.append({'path': f, 'source_type': 'csv', 'symbol': symbol, 'timeframe': timeframe})
    # DB
    for f in glob.glob(os.path.join(data_dir, '*.db')) + glob.glob(os.path.join(data_dir, '*.sqlite')):
        fname = os.path.basename(f)
        m = re.match(r'(BINANCE_)?([A-Za-z0-9]+)[.,_ ]*(\d+[a-zA-Z]*)\.(db|sqlite)', fname)
        if m:
            symbol_raw = m.group(2)
            tf_raw = m.group(3)
            symbol = normalize_symbol_format(symbol_raw, ensure_prefix=True)
            tf_map = {"30": "30m", "60": "1h", "240": "4h", "1440": "1d"}
            timeframe = tf_map.get(tf_raw.lower(), tf_raw.lower())
            symbol, timeframe = normalize_symbol_and_timeframe(f"{symbol}_{timeframe}")
            sources.append({'path': f, 'source_type': 'db', 'symbol': symbol, 'timeframe': timeframe})
    return sources

# ==== 3. Ensure table ====
def ensure_table(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS candlestick_data (
      symbol TEXT NOT NULL,
      timeframe TEXT NOT NULL,
      open_time INTEGER NOT NULL,
      open REAL, high REAL, low REAL, close REAL, volume REAL,
      PRIMARY KEY (symbol, timeframe, open_time)
    )''')
    conn.commit()
    conn.close()

# ==== 4. Migrate from DB ====
def migrate_from_db(src, db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        conn.execute(f"ATTACH DATABASE '{src['path']}' AS srcdb")
        # Try common table names
        for tbl in ['candles', 'kline', 'klines', 'ohlcv']:
            try:
                # Check if table exists
                r = c.execute(f"SELECT name FROM srcdb.sqlite_master WHERE type='table' AND name='{tbl}'").fetchone()
                if not r:
                    continue
                # Insert/replace
                sql = f"""
                INSERT OR REPLACE INTO candlestick_data (symbol, timeframe, open_time, open, high, low, close, volume)
                SELECT ?, ?, 
                  CASE WHEN length(open_time)>10 THEN substr(open_time,1,13) ELSE open_time*1000 END,
                  open, high, low, close, volume
                FROM srcdb.{tbl}
                """
                c.execute(sql, (src['symbol'], src['timeframe']))
                conn.commit()
                rows = c.execute(f"SELECT COUNT(*) FROM candlestick_data WHERE symbol=? AND timeframe=?", (src['symbol'], src['timeframe'])).fetchone()[0]
                print(f"[DB MIGRATE] {src['path']} ({tbl}): {rows} rows")
                break
            except Exception as e:
                continue
        conn.execute("DETACH DATABASE srcdb")
    except Exception as e:
        print(f"[WARN] DB migrate failed for {src['path']}: {e}")
    finally:
        conn.close()

# ==== 5. Migrate from CSV ====
def migrate_from_csv(src, db_path):
    try:
        df = pd.read_csv(src['path'])
        # Map columns
        col_map = {c.lower(): c for c in df.columns}
        time_col = col_map.get('open_time') or col_map.get('time')
        open_col = col_map.get('open') or col_map.get('open_price')
        high_col = col_map.get('high') or col_map.get('high_price')
        low_col = col_map.get('low') or col_map.get('low_price')
        close_col = col_map.get('close') or col_map.get('close_price')
        volume_col = col_map.get('volume')
        if not time_col or not open_col or not high_col or not low_col or not close_col or not volume_col:
            print(f"[WARN] CSV {src['path']} missing columns, skip")
            return 0
        # Convert time to epoch seconds (chuẩn với DB)
        import numpy as np
        def convert_time(val):
            # Nếu là số, xử lý như cũ
            try:
                ival = int(val)
                # Nếu nhỏ hơn 10_000_000_000 thì là epoch giây, nếu lớn là ms
                if ival < 10_000_000_000:
                    return ival
                elif ival < 10_000_000_000_000:
                    return ival // 1000
                else:
                    return ival
            except Exception:
                pass
            # Nếu là string ISO
            try:
                return int(pd.to_datetime(val).timestamp())
            except Exception:
                return np.nan
        df['open_time'] = df[time_col].apply(convert_time)
        df_import = df[['open_time', open_col, high_col, low_col, close_col, volume_col]].copy()
        df_import.columns = ['open_time', 'open', 'high', 'low', 'close', 'volume']
        df_import['symbol'] = src['symbol']
        df_import['timeframe'] = src['timeframe']
        # Drop rows with invalid open_time
        df_import = df_import.dropna(subset=['open_time'])
        df_import['open_time'] = df_import['open_time'].astype(int)
        # Insert
        conn = sqlite3.connect(db_path)
        df_import.to_sql('candlestick_data', conn, if_exists='append', index=False, method='multi')
        conn.close()
        print(f"[CSV MIGRATE] {src['path']}: {len(df_import)} rows")
        return len(df_import)
    except Exception as e:
        print(f"[WARN] CSV migrate failed for {src['path']}: {e}")
        return 0

# ==== 6. API fetch for missing pairs ====
def fetch_api(symbol, timeframe, host, days):
    url = f"{host}/api/binance/add"
    payload = {"symbol": symbol, "timeframe": timeframe, "days": days}
    try:
        r = requests.post(url, json=payload, timeout=60)
        print(f"[API FETCH] {symbol}/{timeframe}: HTTP {r.status_code}, {r.text[:100]}")
        return r.status_code, r.text
    except Exception as e:
        print(f"[API FETCH ERROR] {symbol}/{timeframe}: {e}")
        return 0, str(e)

# ==== 7. Verify pairs in DB ====
def verify_pairs(db_path, pairs):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    summary = []
    for p in pairs:
        symbol, tf = p.split(':')
        r = c.execute("SELECT COUNT(*), MIN(open_time), MAX(open_time) FROM candlestick_data WHERE symbol=? AND timeframe=?", (symbol, tf)).fetchone()
        summary.append({'symbol': symbol, 'timeframe': tf, 'rows': r[0], 'min_t': r[1], 'max_t': r[2]})
    conn.close()
    return summary

# ==== 8. Optimize E2E test ====
def test_optimize(host):
    url = f"{host}/optimize_ranges"
    payload = {
      "strategy": "BIOUSDT_30_TRADELIST_v3",
      "candle_data": "BINANCE_BIOUSDT_30m.db",
      "optimization_engine": "grid_search",
      "optimization_criteria": "pnl",
      "selected_params": ["sl"],
      "sl_min": 0.5, "sl_max": 3, "sl_step": 0.1,
      "be_min": 2, "be_max": 5, "be_step": 0.05,
      "ts_active_min": 2, "ts_active_max": 5, "ts_active_step": 0.1,
      "ts_step_min": 3, "ts_step_max": 8, "ts_step_step": 1,
      "step_multiplier": "1.5",
      "engine_type": "realistic",
      "max_iterations": "100"
    }
    try:
        r = requests.post(url, json=payload, timeout=120)
        print(f"[OPTIMIZE] HTTP {r.status_code}")
        print(r.text)
        return r.status_code, r.text
    except Exception as e:
        print(f"[OPTIMIZE ERROR] {e}")
        return 0, str(e)

# ==== MAIN ====
def main():
    report = {'timestamp': datetime.now().isoformat()}
    before_size, backup_path = backup_db(DB_PATH)
    report['before_size'] = before_size
    report['backup_path'] = backup_path
    ensure_table(DB_PATH)
    sources = scan_sources(DATA_DIR)
    report['sources_scanned'] = sources
    csv_imported = 0
    db_imported = 0
    # Migrate DB
    for src in sources:
        if src['source_type'] == 'db':
            migrate_from_db(src, DB_PATH)
            db_imported += 1
    # Migrate CSV
    for src in sources:
        if src['source_type'] == 'csv':
            csv_imported += migrate_from_csv(src, DB_PATH)
    report['csv_imported'] = csv_imported
    report['db_imported'] = db_imported
    # API fetch for missing pairs
    pairs = [p if ':' in p else f"{p}:30m" for p in PAIRS]
    missing = []
    summary = verify_pairs(DB_PATH, pairs)
    for s in summary:
        if s['rows'] == 0:
            fetch_api(s['symbol'], s['timeframe'], HOST, BINANCE_DAYS)
            missing.append({'symbol': s['symbol'], 'timeframe': s['timeframe']})
    # Re-verify after API
    summary2 = verify_pairs(DB_PATH, pairs)
    report['pairs_summary'] = summary2
    report['after_size'] = os.path.getsize(DB_PATH)
    # Optimize E2E
    opt_code, opt_text = test_optimize(HOST)
    report['optimize_status'] = opt_code
    report['optimize_response'] = opt_text[:1000]
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(f"[DONE] Migration report: {REPORT_PATH}")

if __name__ == '__main__':
    main()
