import sqlite3
conn = sqlite3.connect('candlestick_data.db')
c = conn.cursor()
c.execute('SELECT DISTINCT symbol, timeframe FROM candlestick_data WHERE symbol = "BIOUSDT" AND timeframe = "30m";')
print(c.fetchall())
conn.close()