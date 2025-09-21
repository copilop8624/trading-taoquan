#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('strategy_management.db')
cur = conn.cursor()

# Delete the malformed record (ID 20 with timeframe "30" instead of "30m")
print("Deleting malformed BIOUSDT record...")
cur.execute('DELETE FROM strategies WHERE id = 20')
print(f"Deleted {cur.rowcount} record(s)")

# Verify remaining records
print("\n=== Remaining BIOUSDT Records ===")
rows = cur.execute('''
    SELECT id, symbol, timeframe, strategy_name, version, file_path 
    FROM strategies 
    WHERE symbol LIKE '%BIOUSDT%' 
    ORDER BY id
''').fetchall()

for r in rows:
    print(f"ID: {r[0]} | {r[1]} {r[2]} {r[3]} {r[4]} -> {r[5]}")

conn.commit()
conn.close()
print("\nDatabase updated successfully!")