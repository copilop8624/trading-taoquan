import sqlite3

def check_databases():
    """Check available data in databases"""
    
    # Check strategy management DB
    try:
        conn = sqlite3.connect('strategy_management.db')
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Strategy DB tables: {tables}")
        
        if tables:
            # Check first table content
            table_name = tables[0][0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"Table {table_name} columns: {columns}")
            
            # Get sample data
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
            sample = cursor.fetchall()
            print(f"Sample data: {sample}")
        
        conn.close()
    except Exception as e:
        print(f"Strategy DB error: {e}")
    
    # Check candlestick DB  
    try:
        conn = sqlite3.connect('candlestick_data.db')
        cursor = conn.cursor()
        
        # Get available symbols and timeframes
        cursor.execute("SELECT DISTINCT symbol, timeframe FROM candlestick_data LIMIT 10")
        symbols = cursor.fetchall()
        print(f"Available candle data: {symbols}")
        
        conn.close()
    except Exception as e:
        print(f"Candlestick DB error: {e}")

if __name__ == "__main__":
    check_databases()