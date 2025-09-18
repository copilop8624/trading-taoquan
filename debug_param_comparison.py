#!/usr/bin/env python3
"""
Simple debug to find parameter logging
"""
import requests
import json
import time

def simple_debug_test():
    # Stop server first to see fresh logs
    url = "http://localhost:5000/optimize_ranges"
    
    payload = {
        "ranges": {
            "sl_be_profit": [50.0, 50.1],  # Very tight range
            "trailing_stop_step": [1.0, 1.01]  # Very tight range  
        },
        "trials": 1,
        "optimization_engine": "optuna", 
        "optimization_criteria": "pnl",
        "selected_params": ["sl_be_profit", "trailing_stop_step"],
        "strategy": "BTCUSDT_30m_TRADELIST_v1",
        "candle_data": "BINANCE_BTCUSDT_30m.db"
    }
    
    print("🔍 Running minimal test to capture parameter comparison...")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success', False)}")
            
            # Print key metrics only
            if result.get('success') and 'data' in result:
                data = result['data']
                best_trial = data.get('best_trial', {})
                optimized_pnl = data.get('optimized_pnl', 0)
                
                print(f"🎯 Best trial value: {best_trial.get('value', 0)}")
                print(f"🔧 Best params: {best_trial.get('params', {})}")
                print(f"✅ Optimized PnL: {optimized_pnl}")
                
                print("📊 Trade analysis:", data.get('trade_analysis', {}).get('total_trades', 0), "trades")
                
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    simple_debug_test()