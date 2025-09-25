import sqlite3

conn = sqlite3.connect('strategy_management.db')
rows = list(conn.execute("SELECT id, filename, symbol, timeframe, strategy_name, version, is_active, file_path FROM strategies WHERE symbol LIKE '%PERPUSDT%' ORDER BY is_active DESC, version DESC;"))
for row in rows:
    print(row)
conn.close()