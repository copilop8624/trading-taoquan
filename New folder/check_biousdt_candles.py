import sqlite3
conn = sqlite3.connect('candlestick_data.db')
c = conn.cursor()
c.execute('SELECT DISTINCT symbol, timeframe FROM candlestick_data WHERE symbol LIKE "%BIOUSDT%";')
print(c.fetchall())
conn.close()