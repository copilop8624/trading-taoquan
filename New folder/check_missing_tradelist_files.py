import sqlite3
import os

conn = sqlite3.connect('strategy_management.db')
rows = list(conn.execute("SELECT id, filename, symbol, timeframe, strategy_name, version, is_active, file_path FROM strategies WHERE is_active=1 ORDER BY symbol, version DESC;"))
missing = []
for row in rows:
    id, filename, symbol, timeframe, strategy_name, version, is_active, file_path = row
    if not os.path.exists(file_path):
        print(f"MISSING: {symbol} {timeframe} {strategy_name} {version} -> {file_path}")
        missing.append((id, file_path))
conn.close()
if not missing:
    print("All active strategies have valid files.")
else:
    print(f"Total missing: {len(missing)}")
