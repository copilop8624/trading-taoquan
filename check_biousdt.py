#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('strategy_management.db')
cur = conn.cursor()
rows = cur.execute('SELECT symbol, timeframe, strategy_name, version, file_path FROM strategies WHERE symbol LIKE ?', ['%BIOUSDT%']).fetchall()

print('BIOUSDT strategies in database:')
for r in rows:
    print(f'{r[0]} {r[1]} {r[2]} {r[3]} -> {r[4]}')
    
print(f'\nTotal: {len(rows)} strategies found')
conn.close()