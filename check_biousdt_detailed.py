#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('strategy_management.db')
cur = conn.cursor()

# Check for strategies that may need cleanup
print("=== BIOUSDT Strategy Records ===")
rows = cur.execute('''
    SELECT id, symbol, timeframe, strategy_name, version, file_path, created_at 
    FROM strategies 
    WHERE symbol LIKE '%BIOUSDT%' 
    ORDER BY created_at
''').fetchall()

for r in rows:
    print(f"ID: {r[0]} | {r[1]} {r[2]} {r[3]} {r[4]} -> {r[5]} | Created: {r[6]}")

# Check if files exist
import os
print("\n=== File Existence Check ===")
for r in rows:
    file_path = r[5]
    exists = os.path.exists(file_path)
    print(f"{'✅' if exists else '❌'} {file_path}")
    if exists:
        size = os.path.getsize(file_path)
        print(f"    Size: {size} bytes")

conn.close()