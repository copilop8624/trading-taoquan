# check_dogeusdt_timestamp.py
import sqlite3
from datetime import datetime

DB_PATH = 'candlestick_data.db'
SYMBOL = 'DOGEUSDT'
TIMEFRAME = '30m'

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Lấy min/max open_time (epoch ms)
c.execute("""
    SELECT MIN(open_time), MAX(open_time), COUNT(*) FROM candlestick_data
    WHERE symbol=? AND timeframe=?
""", (SYMBOL, TIMEFRAME))
min_t, max_t, n_rows = c.fetchone()

# Lấy 5 dòng đầu và cuối (theo open_time)
c.execute("""
    SELECT open_time, open, high, low, close, volume FROM candlestick_data
    WHERE symbol=? AND timeframe=? ORDER BY open_time ASC LIMIT 5
""", (SYMBOL, TIMEFRAME))
first_rows = c.fetchall()
c.execute("""
    SELECT open_time, open, high, low, close, volume FROM candlestick_data
    WHERE symbol=? AND timeframe=? ORDER BY open_time DESC LIMIT 5
""", (SYMBOL, TIMEFRAME))
last_rows = c.fetchall()
conn.close()

def ts_to_str(ts):
    if not ts: return 'N/A'
    try:
        # ms to s
        if ts > 10_000_000_000:
            ts = ts // 1000
        return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
    except Exception:
        return str(ts)

print(f"DOGEUSDT 30m: {n_rows} rows")
print(f"  MIN open_time: {min_t} ({ts_to_str(min_t)})")
print(f"  MAX open_time: {max_t} ({ts_to_str(max_t)})")

print("\n5 dòng đầu:")
for r in first_rows:
    print(f"  {r[0]} ({ts_to_str(r[0])}) | O:{r[1]} H:{r[2]} L:{r[3]} C:{r[4]} V:{r[5]}")

print("\n5 dòng cuối:")
for r in last_rows:
    print(f"  {r[0]} ({ts_to_str(r[0])}) | O:{r[1]} H:{r[2]} L:{r[3]} C:{r[4]} V:{r[5]}")

# Phát hiện lỗi timestamp
err = False
if min_t and (min_t < 946684800000 or min_t > 4102444800000):  # Trước 2000 hoặc sau 2100
    print("❌ Cảnh báo: MIN open_time bất thường (trước năm 2000 hoặc sau 2100)")
    err = True
if max_t and (max_t < 946684800000 or max_t > 4102444800000):
    print("❌ Cảnh báo: MAX open_time bất thường (trước năm 2000 hoặc sau 2100)")
    err = True
if not err:
    print("✅ Timestamp có vẻ hợp lệ (nằm trong khoảng 2000-2100)")
