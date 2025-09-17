import sqlite3
from typing import List, Tuple, Optional
import pandas as pd
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'candlestick_data.db')

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS candlestick_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                open_time INTEGER NOT NULL,
                open_price REAL NOT NULL,
                high_price REAL NOT NULL,
                low_price REAL NOT NULL,
                close_price REAL NOT NULL,
                volume REAL NOT NULL,
                UNIQUE(symbol, timeframe, open_time)
            )
        ''')
        conn.commit()

def insert_candles(symbol: str, timeframe: str, candles: List[Tuple[int, float, float, float, float, float]]):
    """
    candles: List of (open_time, open, high, low, close, volume)
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.executemany('''
            INSERT OR IGNORE INTO candlestick_data (symbol, timeframe, open_time, open_price, high_price, low_price, close_price, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', [(symbol, timeframe, *row) for row in candles])
        conn.commit()

def get_candles(symbol: str, timeframe: str, start_time: Optional[int]=None, end_time: Optional[int]=None) -> pd.DataFrame:
    with get_connection() as conn:
        c = conn.cursor()
        query = 'SELECT open_time, open_price, high_price, low_price, close_price, volume FROM candlestick_data WHERE symbol=? AND timeframe=?'
        params = [symbol, timeframe]
        if start_time:
            query += ' AND open_time >= ?'
            params.append(start_time)
        if end_time:
            query += ' AND open_time <= ?'
            params.append(end_time)
        query += ' ORDER BY open_time ASC'
        c.execute(query, params)
        rows = c.fetchall()
    df = pd.DataFrame(rows, columns=['open_time','open','high','low','close','volume'])
    return df

def resample_candles(df: pd.DataFrame, new_timeframe: str) -> pd.DataFrame:
    """
    Resample candles to a higher timeframe (e.g. from 1m to 30m)
    new_timeframe: e.g. '5m', '15m', '1h'
    """
    if df.empty:
        return df
    tf_map = {'m': 60, 'h': 3600, 'd': 86400}
    unit = new_timeframe[-1]
    n = int(new_timeframe[:-1])
    seconds = n * tf_map[unit]
    df['open_time'] = pd.to_datetime(df['open_time'], unit='s')
    df.set_index('open_time', inplace=True)
    rule = f'{n}{unit.upper()}'
    ohlc_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }
    resampled = df.resample(rule).agg(ohlc_dict).dropna().reset_index()
    resampled['open_time'] = resampled['open_time'].astype(int) // 10**9
    return resampled[['open_time','open','high','low','close','volume']]

# Gọi hàm này khi khởi động app
init_db()
