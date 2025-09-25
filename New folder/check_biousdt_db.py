import sqlite3

conn = sqlite3.connect('strategy_management.db')
cur = conn.cursor()

# Fetch and print strategies for a specific symbol (BIOUSDT)
rows = list(cur.execute("SELECT filename, symbol, timeframe, strategy_name, version, is_active FROM strategies WHERE symbol='BIOUSDT';"))
for row in rows:
    print(row)

# Scan for all symbols with multiple versions or inactive strategies
print("\n=== All strategies with multiple versions or inactive ===")
rows = cur.execute('''
    SELECT symbol, timeframe, strategy_name, version, is_active, file_path 
    FROM strategies 
    WHERE is_active=0 OR symbol IN (
        SELECT symbol FROM strategies GROUP BY symbol, timeframe, strategy_name HAVING COUNT(*) > 1
    )
    ORDER BY symbol, timeframe, strategy_name, version
''').fetchall()
for row in rows:
    print(row)

conn.close()