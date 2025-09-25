#!/usr/bin/env python3
import sqlite3
import os

conn = sqlite3.connect('strategy_management.db')
cur = conn.cursor()

# Delete the malformed record (ID 20 with timeframe "30" instead of "30m")
print("Deleting malformed BIOUSDT record...")
cur.execute('DELETE FROM strategies WHERE id = 20')
print(f"Deleted {cur.rowcount} record(s)")

# Soft delete BIOUSDT_30m_TRADELIST_v2
cur.execute("UPDATE strategies SET is_active=0 WHERE symbol='BIOUSDT' AND timeframe='30m' AND strategy_name='TRADELIST' AND version='v2'")
print(f"Soft deleted {cur.rowcount} record(s) for BIOUSDT_30m_TRADELIST_v2")

# Verify remaining active records
print("\n=== Remaining ACTIVE BIOUSDT Records ===")
rows = cur.execute('''
    SELECT id, symbol, timeframe, strategy_name, version, file_path 
    FROM strategies 
    WHERE symbol LIKE '%BIOUSDT%' AND is_active=1
    ORDER BY id
''').fetchall()
for row in rows:
    print(row)

# Soft delete all inactive or missing PERPUSDT tradelists
print("\n=== Soft deleting missing PERPUSDT tradelists ===")
rows = cur.execute('''
    SELECT id, file_path FROM strategies 
    WHERE symbol LIKE '%PERPUSDT%' AND is_active=1
''').fetchall()
for row in rows:
    id, file_path = row
    if not os.path.exists(file_path):
        print(f"Soft deleting id {id} (missing file: {file_path})")
        cur.execute('UPDATE strategies SET is_active=0 WHERE id=?', (id,))

conn.commit()
conn.close()
print("\nDatabase updated successfully!")