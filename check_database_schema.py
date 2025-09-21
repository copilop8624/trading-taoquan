#!/usr/bin/env python3
"""
Check database schema and TS values
"""
import sqlite3
import os

def check_database():
    db_path = "instance/optimization_results.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("PRAGMA table_info(optimization_results)")
        columns = cursor.fetchall()
        
        print("🔍 DATABASE SCHEMA:")
        print("=" * 40)
        for col in columns:
            print(f"{col[1]} ({col[2]})")
        print()
        
        # Get the latest few optimization results
        cursor.execute("""
        SELECT id, strategy, total_pnl, winrate, 
               ts_trig, ts_step, timestamp
        FROM optimization_results 
        ORDER BY id DESC 
        LIMIT 3
        """)
        
        results = cursor.fetchall()
        
        print("🔍 LATEST TS VALUES:")
        print("=" * 40)
        
        for result in results:
            id, strategy, pnl, wr, ts_trig, ts_step, timestamp = result
            print(f"ID: {id} | Strategy: {strategy}")
            print(f"PnL: {pnl:.2f}% | WR: {wr:.1f}%")
            print(f"TS_TRIG (raw): {ts_trig}")
            print(f"TS_STEP (raw): {ts_step}")
            print(f"TS_TRIG * 100: {ts_trig * 100:.2f}%")
            print(f"TS_STEP * 100: {ts_step * 100:.2f}%")
            print(f"Timestamp: {timestamp}")
            print("-" * 30)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_database()