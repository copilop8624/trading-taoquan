"""
Common utility functions for backend modules.
"""

import re
import pandas as pd
from datetime import datetime

def normalize_symbol_format(symbol, ensure_prefix=None, available_symbols=None):
    """
    Normalize symbol format for consistent handling across the application.
    Args:
        symbol (str): Input symbol (e.g., 'BTCUSDT', 'BINANCE_BTCUSDT')
        ensure_prefix (bool|None):
            - True: ensures BINANCE_ prefix is present
            - False: removes BINANCE_ prefix
            - None (default): do not change prefix, just normalize case
        available_symbols (list[str], optional): List of known symbols (case-insensitive) for matching.
    Returns:
        str: Normalized symbol format, optionally matched to available_symbols.
    """
    if not symbol:
        return ""
    symbol = str(symbol).strip().upper()

    # Handle prefix logic if requested
    if ensure_prefix is True:
        if not symbol.startswith('BINANCE_'):
            symbol = f"BINANCE_{symbol}"
    elif ensure_prefix is False:
        symbol = symbol.replace('BINANCE_', '')

    # If available_symbols is provided, match against them (case-insensitive, with numeric prefix logic)
    if available_symbols:
        symbol_map = {s.upper(): s for s in available_symbols}
        # 1. Direct match
        if symbol in symbol_map:
            return symbol_map[symbol]
        # 2. Try removing numeric prefixes (10, 100, 1000)
        numeric_prefixes = ["10", "100", "1000"]
        for prefix in numeric_prefixes:
            if symbol.startswith(prefix):
                base = symbol[len(prefix):]
                if base in symbol_map:
                    return symbol_map[base]
        # 3. Try adding numeric prefixes if base symbol alone is not found
        for prefix in numeric_prefixes:
            candidate = prefix + symbol
            if candidate in symbol_map:
                return symbol_map[candidate]
        # Not found, return as-is
        return symbol
    return symbol

def parse_csv_filename(filename):
    match = re.match(r'BINANCE_([A-Za-z0-9]+)(?:\.P)?[,_ ]*_*(\d+[a-zA-Z]*)\.csv', filename)
    if match:
        symbol = match.group(1)
        tf_raw = match.group(2)
        if tf_raw.isdigit():
            timeframe = f"{tf_raw}m"
        else:
            timeframe = tf_raw
        return symbol, timeframe
    return None, None

def convert_csv_to_timestamp(date_str):
    formats = [
        '%Y-%m-%d %H:%M:%S', '%Y.%m.%d %H:%M:%S', '%m/%d/%Y %H:%M', '%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M', '%d.%m.%Y %H:%M',
    ]
    for fmt in formats:
        try:
            return int(datetime.strptime(date_str, fmt).timestamp())
        except Exception:
            continue
    try:
        return int(pd.to_datetime(date_str, errors='coerce').timestamp())
    except Exception:
        return None

def normalize_trade_date(s):
    try:
        dt = pd.to_datetime(s, format='%Y-%m-%d %H:%M', errors='coerce')
        if not pd.isna(dt):
            if dt.tz is None:
                dt = dt.tz_localize('UTC').tz_localize(None)
            return dt

            # --- CLEANED normalize_symbol_format START ---
    except Exception:
        pass
    try:
        dt = pd.to_datetime(s, format='%m/%d/%Y %H:%M', errors='coerce')
        if not pd.isna(dt):
            if dt.tz is None:
                dt = dt.tz_localize('Asia/Bangkok').tz_convert('UTC').tz_localize(None)
            return dt
    except Exception:
        pass
    try:
        dt = pd.to_datetime(s, errors='coerce')
        if not pd.isna(dt):
            if dt.tz is None:
                dt = dt.tz_localize('UTC').tz_localize(None)
            else:
                dt = dt.tz_convert('UTC').tz_localize(None)
            return dt
    except Exception:
        pass
    return pd.NaT

def normalize_candle_date(s):
    try:
        dt = pd.to_datetime(s, errors='coerce')
        if not pd.isna(dt):
            if dt.tz is not None:
                dt = dt.tz_localize(None)
            return dt
    except Exception:
        return pd.NaT
    return pd.NaT

def safe_int(value, default=0):
    try:
        if value is None or value == '' or (isinstance(value, float) and (value != value or value == float('inf') or value == float('-inf'))):
            return default
        return int(float(value))
    except Exception:
        return default

def safe_float(value, default=0.0):
    try:
        if value is None or value == '' or (isinstance(value, float) and (value != value or value == float('inf') or value == float('-inf'))):
            return default
        return float(value)
    except Exception:
        return default

def discover_available_symbols():
    import glob
    import os
    files = glob.glob('BINANCE_*.csv')
    symbols = set()
    for f in files:
        name = os.path.basename(f)
        if name.startswith('BINANCE_'):
            s = name.split(',')[0].replace('BINANCE_', '').split('.')[0]
            symbols.add(s)
    return sorted(list(symbols))

