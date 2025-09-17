#!/usr/bin/env python3
"""Check database data format"""

import sqlite3
import pandas as pd

# Check database schema
conn = sqlite3.connect('candlestick_data.db')
cursor = conn.cursor()

print("=== Database Schema ===")
cursor.execute('PRAGMA table_info(candlestick_data)')
columns = cursor.fetchall()
for col in columns:
    print(f"{col[1]}: {col[2]}")

print("\n=== Sample SAGA Data ===")
cursor.execute('''SELECT open_time, open_price, high_price, low_price, close_price 
                  FROM candlestick_data 
                  WHERE symbol = "BINANCE_SAGAUSDT" AND timeframe = "30m" 
                  ORDER BY open_time LIMIT 3''')
rows = cursor.fetchall()
for i, row in enumerate(rows):
    print(f"Row {i+1}: Time={row[0]}, Open={row[1]}, High={row[2]}, Low={row[3]}, Close={row[4]}")

print("\n=== Check time format ===")
if rows:
    import datetime
    try:
        # Try to convert first timestamp
        ts = rows[0][0]
        dt = pd.to_datetime(ts, unit='ms')
        print(f"Timestamp {ts} converts to: {dt}")
    except Exception as e:
        print(f"Error converting timestamp: {e}")

print("\n=== Price Range Analysis ===")
cursor.execute('''SELECT MIN(open_price), MAX(open_price), AVG(open_price) 
                  FROM candlestick_data 
                  WHERE symbol = "BINANCE_SAGAUSDT" AND timeframe = "30m"''')
price_stats = cursor.fetchone()
print(f"Price range: Min={price_stats[0]}, Max={price_stats[1]}, Avg={price_stats[2]:.6f}")

conn.close()