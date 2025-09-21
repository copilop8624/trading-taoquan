#!/usr/bin/env python3
"""
Debug script để kiểm tra giá trị TS thực tế trong database optimization_results
"""
import sys
import sqlite3

sys.path.append('.')

def check_latest_optimization():
    print("=== Checking Latest Optimization Results ===")
    
    try:
        # Connect to optimization results database
        conn = sqlite3.connect('instance/optimization_results.db')
        cur = conn.cursor()
        
        # Get latest optimization result
        query = '''
            SELECT id, parameters, result_summary, created_at 
            FROM optimization_results 
            ORDER BY created_at DESC 
            LIMIT 1
        '''
        
        result = cur.fetchone()
        if result:
            import json
            
            result_id, parameters_json, summary_json, created_at = result
            print(f"Latest optimization ID: {result_id}")
            print(f"Created at: {created_at}")
            
            # Parse parameters
            if parameters_json:
                params = json.loads(parameters_json)
                print(f"\n📊 Parameters (Raw JSON):")
                for key, value in params.items():
                    print(f"   {key}: {value}")
                    
                # Check specific TS values
                if 'ts_trig' in params and 'ts_step' in params:
                    ts_trig = params['ts_trig']
                    ts_step = params['ts_step']
                    print(f"\n🎯 TS Values Analysis:")
                    print(f"   ts_trig raw: {ts_trig}")
                    print(f"   ts_step raw: {ts_step}")
                    print(f"   ts_trig * 100: {ts_trig * 100}%")
                    print(f"   ts_step * 100: {ts_step * 100}%")
                    
                    # Check if values are already in percentage
                    if ts_trig > 10:  # Likely already in percentage
                        print(f"   ⚠️ ts_trig seems to be already in % format")
                    else:
                        print(f"   ✅ ts_trig seems to be in decimal format (need * 100)")
                        
                    if ts_step > 10:  # Likely already in percentage  
                        print(f"   ⚠️ ts_step seems to be already in % format")
                    else:
                        print(f"   ✅ ts_step seems to be in decimal format (need * 100)")
            
            # Parse summary
            if summary_json:
                summary = json.loads(summary_json)
                print(f"\n📈 Summary:")
                for key, value in summary.items():
                    print(f"   {key}: {value}")
        else:
            print("❌ No optimization results found")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_latest_optimization()