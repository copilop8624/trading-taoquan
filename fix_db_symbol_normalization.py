import sqlite3
import re

def normalize_symbol(symbol):
    # Loại bỏ tiền tố BINANCE_ nếu có
    if symbol.upper().startswith('BINANCE_'):
        return symbol[8:]
    return symbol

def normalize_all_symbols(db_path='candlestick_data.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT DISTINCT symbol FROM candlestick_data')
    symbols = [row[0] for row in c.fetchall()]
    for symbol in symbols:
        new_symbol = normalize_symbol(symbol)
        if new_symbol != symbol:
            print(f"Đổi symbol {symbol} -> {new_symbol}")
            c.execute('UPDATE candlestick_data SET symbol=? WHERE symbol=?', (new_symbol, symbol))
    conn.commit()
    conn.close()
    print("Đã chuẩn hóa xong toàn bộ symbol trong DB.")

if __name__ == "__main__":
    normalize_all_symbols()
