# compare_csv_db_dogeusdt.py
import pandas as pd
import sqlite3
from datetime import datetime
import os

CSV_PATH = os.path.join('candles', 'BINANCE_DOGEUSDT.P, 30.csv')
DB_PATH = 'candlestick_data.db'
SYMBOL = 'DOGEUSDT'
TIMEFRAME = '30m'

# Đọc CSV
if not os.path.exists(CSV_PATH):
    print(f"❌ Không tìm thấy file {CSV_PATH}")
    exit(1)
df_csv = pd.read_csv(CSV_PATH)
# Tìm cột thời gian
for col in ['open_time', 'time', 'timestamp']:
    if col in df_csv.columns:
        time_col = col
        break
else:
    print("❌ Không tìm thấy cột thời gian trong CSV!")
    exit(1)

print(f"CSV: {CSV_PATH} có {len(df_csv)} dòng, cột thời gian: {time_col}")
print(f"  Min: {df_csv[time_col].min()}  Max: {df_csv[time_col].max()}")
# Hiển thị 3 giá trị đầu/cuối
print("  3 giá trị đầu:", df_csv[time_col].head(3).tolist())
print("  3 giá trị cuối:", df_csv[time_col].tail(3).tolist())

# Đọc DB
conn = sqlite3.connect(DB_PATH)
df_db = pd.read_sql_query(
    "SELECT open_time FROM candlestick_data WHERE symbol=? AND timeframe=? ORDER BY open_time ASC",
    conn, params=(SYMBOL, TIMEFRAME))
conn.close()
print(f"DB: {len(df_db)} dòng cho {SYMBOL} {TIMEFRAME}")
if not df_db.empty:
    print(f"  Min: {df_db['open_time'].min()}  Max: {df_db['open_time'].max()}")
    print("  3 giá trị đầu:", df_db['open_time'].head(3).tolist())
    print("  3 giá trị cuối:", df_db['open_time'].tail(3).tolist())
else:
    print("  Không có dữ liệu trong DB cho cặp này!")

# So sánh tập open_time
csv_set = set(df_csv[time_col])
db_set = set(df_db['open_time'])
only_in_csv = csv_set - db_set
only_in_db = db_set - csv_set
print(f"\nSố open_time chỉ có trong CSV, không có trong DB: {len(only_in_csv)}")
print(f"Số open_time chỉ có trong DB, không có trong CSV: {len(only_in_db)}")
if len(only_in_csv) > 0:
    print("  Ví dụ open_time chỉ có trong CSV:", list(only_in_csv)[:5])
if len(only_in_db) > 0:
    print("  Ví dụ open_time chỉ có trong DB:", list(only_in_db)[:5])
