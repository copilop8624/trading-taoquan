#!/usr/bin/env python3
"""
Check TS values from parameters JSON field
"""
import sqlite3
import json
import os

def check_ts_parameters():
    db_path = "instance/optimization_results.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the latest optimization results with parameters
        cursor.execute("""
        SELECT id, strategy, total_pnl, winrate, parameters, timestamp
        FROM optimization_results 
        ORDER BY id DESC 
        LIMIT 3
        """)
        
        results = cursor.fetchall()
        
        print("🔍 LATEST TS VALUES FROM PARAMETERS:")
        print("=" * 60)
        
        for result in results:
            id, strategy, pnl, wr, params_json, timestamp = result
            print(f"ID: {id} | Strategy: {strategy}")
            print(f"PnL: {pnl:.2f}% | WR: {wr:.1f}%")
            print(f"Timestamp: {timestamp}")
            
            try:
                params = json.loads(params_json)
                print(f"Raw Parameters: {params}")
                
                if 'ts_trig' in params:
                    ts_trig = params['ts_trig']
                    print(f"TS_TRIG (raw): {ts_trig}")
                    print(f"TS_TRIG * 100: {ts_trig * 100:.2f}%")
                
                if 'ts_activation' in params:
                    ts_activation = params['ts_activation']
                    print(f"TS_ACTIVATION (raw): {ts_activation}")
                    print(f"TS_ACTIVATION * 100: {ts_activation * 100:.2f}%")
                
                if 'ts_step' in params:
                    ts_step = params['ts_step']
                    print(f"TS_STEP (raw): {ts_step}")
                    print(f"TS_STEP * 100: {ts_step * 100:.2f}%")
                    
            except json.JSONDecodeError:
                print("❌ Failed to parse parameters JSON")
            
            print("-" * 40)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_ts_parameters()