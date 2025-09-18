#!/usr/bin/env python3
"""
🐞 Debug Optimization Step by Step
"""

import requests
import json

def test_quick_summary_first():
    """Test quick summary first to ensure data loading works"""
    
    form_data = {
        'strategy': 'BTCUSDT_60m_LONG_SHORT_v1',
        'candle_data': 'BINANCE_BTCUSDT_60m.db'
    }
    
    print("🧪 Testing Quick Summary first...")
    
    try:
        response = requests.post(
            'http://localhost:5000/quick_summary_strategy',
            data=form_data,
            timeout=30
        )
        
        print(f"Quick Summary status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Quick Summary works")
                data = result['data']
                print(f"   Strategy: {data.get('strategy_name')}")
                print(f"   Trades: {data.get('total_trades')}")
                print(f"   PnL: {data.get('total_pnl')}")
                return True
            else:
                print(f"❌ Quick Summary failed: {result.get('error')}")
        else:
            print(f"❌ Quick Summary HTTP error: {response.text}")
            
    except Exception as e:
        print(f"❌ Quick Summary exception: {e}")
        
    return False

def test_simple_optimization():
    """Test very simple optimization"""
    
    # Minimal parameter set
    test_data = {
        "strategy": "BTCUSDT_60m_LONG_SHORT_v1",
        "candle_data": "BINANCE_BTCUSDT_60m.db",
        "optimization_engine": "optuna",  # Use Optuna with minimal trials
        "sl_min": 1.0,
        "sl_max": 1.0,  # Same value = no optimization
        "sl_step": 0.1,
        "be_min": 0.5,
        "be_max": 0.5,  # Same value = no optimization
        "be_step": 0.1,
        "ts_min": 1.0,
        "ts_max": 1.0,  # Same value = no optimization
        "ts_step": 0.1
    }
    
    print("🔥 Testing Simple Optimization...")
    print(f"Test data: {json.dumps(test_data, indent=2)}")
    
    try:
        response = requests.post(
            'http://localhost:5000/optimize_ranges',
            json=test_data,
            timeout=60
        )
        
        print(f"Optimization status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Simple Optimization works")
                return True
            else:
                print(f"❌ Optimization failed: {result.get('error')}")
        else:
            print(f"❌ Optimization HTTP error")
            
    except Exception as e:
        print(f"❌ Optimization exception: {e}")
        
    return False

if __name__ == "__main__":
    print("🐞 Starting Debug Process...")
    
    # Step 1: Test data loading
    if test_quick_summary_first():
        print("\n" + "="*50)
        # Step 2: Test optimization
        test_simple_optimization()
    else:
        print("❌ Data loading failed, can't proceed to optimization")