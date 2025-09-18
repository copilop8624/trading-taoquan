#!/usr/bin/env python3
"""
Check available strategies in database
"""

import sqlite3
import os

def check_strategies():
    """Check what strategies are available"""
    
    db_path = 'strategy_management.db'
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table structure
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📊 Tables in database: {tables}")
        
        # Check strategies table
        cursor.execute("SELECT * FROM strategies LIMIT 5")
        rows = cursor.fetchall()
        print(f"🎯 Sample strategies ({len(rows)} found):")
        
        for i, row in enumerate(rows):
            print(f"  {i+1}. {row}")
            
        # Get column names
        cursor.execute("PRAGMA table_info(strategies)")
        columns = cursor.fetchall()
        print(f"📋 Columns: {[col[1] for col in columns]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        
def check_candle_db():
    """Check candlestick database"""
    
    db_path = 'candlestick_data.db'
    if not os.path.exists(db_path):
        print(f"❌ Candle database not found: {db_path}")
        return
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get available symbols/timeframes
        cursor.execute("SELECT DISTINCT symbol, timeframe FROM candlestick_data LIMIT 10")
        rows = cursor.fetchall()
        print(f"🕯️ Available candle data ({len(rows)} combinations):")
        
        for row in rows:
            print(f"  {row[0]}_{row[1]}")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking candle database: {e}")

if __name__ == "__main__":
    print("🔍 Checking databases...")
    check_strategies()
    print()
    check_candle_db()