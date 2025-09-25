# check_dogeusdt_candles.py
import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = 'candlestick_data.db'
SYMBOL = 'DOGEUSDT'

conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("""
    SELECT symbol, timeframe, COUNT(*) AS rows, MIN(open_time) AS min_t, MAX(open_time) AS max_t
    FROM candlestick_data
    WHERE symbol=?
    GROUP BY timeframe
    ORDER BY timeframe
""", conn, params=(SYMBOL,))
conn.close()

if df.empty:
    print(f"❌ Không có dữ liệu nến cho {SYMBOL} trong DB!")
else:
    print(f"✅ Các timeframe có dữ liệu cho {SYMBOL}:")
    for _, row in df.iterrows():
        min_time = datetime.utcfromtimestamp(row['min_t']//1000).strftime('%Y-%m-%d %H:%M') if row['min_t'] else 'N/A'
        max_time = datetime.utcfromtimestamp(row['max_t']//1000).strftime('%Y-%m-%d %H:%M') if row['max_t'] else 'N/A'
        print(f"  - {row['timeframe']}: {row['rows']} rows, từ {min_time} đến {max_time}")
