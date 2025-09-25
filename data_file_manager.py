import os
import glob
import pandas as pd
from datetime import datetime

TRADLIST_DIR = 'tradelist'
CANDLE_DIR = 'candles'


def list_files(directory, pattern='*.csv'):
    files = glob.glob(os.path.join(directory, pattern))
    return files


def get_tradelist_info(filepath):
    try:
        df = pd.read_csv(filepath)
        n = len(df)
        date_cols = [c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()]
        min_time, max_time = None, None
        if date_cols:
            min_time = pd.to_datetime(df[date_cols[0]], errors='coerce').min()
            max_time = pd.to_datetime(df[date_cols[0]], errors='coerce').max()
        return {'file': os.path.basename(filepath), 'rows': n, 'min_time': min_time, 'max_time': max_time}
    except Exception as e:
        return {'file': os.path.basename(filepath), 'error': str(e)}


def get_candle_info(filepath):
    try:
        df = pd.read_csv(filepath)
        n = len(df)
        min_time, max_time = None, None
        if 'time' in df.columns:
            min_time = pd.to_datetime(df['time'], errors='coerce').min()
            max_time = pd.to_datetime(df['time'], errors='coerce').max()
        return {'file': os.path.basename(filepath), 'rows': n, 'min_time': min_time, 'max_time': max_time}
    except Exception as e:
        return {'file': os.path.basename(filepath), 'error': str(e)}


def main():
    print('=== TRADELIST FILES ===')
    tradelist_files = list_files(TRADLIST_DIR)
    for f in tradelist_files:
        info = get_tradelist_info(f)
        print(info)

    print('\n=== CANDLE FILES ===')
    candle_files = list_files(CANDLE_DIR)
    for f in candle_files:
        info = get_candle_info(f)
        print(info)

    # Add more CLI options as needed (delete, rename, preview, etc.)

if __name__ == '__main__':
    main()
