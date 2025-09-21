#!/usr/bin/env python3
"""
Simple check of TS values in the database
"""
import sqlite3
import os

def check_ts_values():
    db_path = "instance/optimization_results.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the latest few optimization results
        cursor.execute("""
        SELECT id, strategy, optimization_engine, total_pnl, winrate, 
               ts_trig, ts_step, timestamp
        FROM optimization_results 
        ORDER BY id DESC 
        LIMIT 5
        """)
        
        results = cursor.fetchall()
        
        print("🔍 LATEST TS VALUES IN DATABASE:")
        print("=" * 80)
        
        for result in results:
            id, strategy, engine, pnl, wr, ts_trig, ts_step, timestamp = result
            print(f"ID: {id} | Strategy: {strategy}")
            print(f"Engine: {engine} | PnL: {pnl:.2f}% | WR: {wr:.1f}%")
            print(f"TS_TRIG (raw): {ts_trig}")
            print(f"TS_STEP (raw): {ts_step}")
            print(f"TS_TRIG * 100: {ts_trig * 100:.2f}%")
            print(f"TS_STEP * 100: {ts_step * 100:.2f}%")
            print(f"Timestamp: {timestamp}")
            print("-" * 40)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_ts_values()