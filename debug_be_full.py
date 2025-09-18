#!/usr/bin/env python3
"""
Debug FIXED BE logic with full debug output
"""

import pandas as pd
import numpy as np
import sys
import os
import importlib

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Force reload module to get latest changes
import web_backtest.backtest_gridsearch_slbe_ts_Version3 as backtest_module
importlib.reload(backtest_module)

def debug_be_with_logs():
    """Debug BE with full logging"""
    
    # Simple test case
    times = pd.date_range('2024-04-01', periods=6, freq='30T')
    prices = [1.0, 1.01, 1.015, 1.01, 1.005, 1.004]  # BE trigger → slight pullback
    
    df = pd.DataFrame({
        'time': times,
        'open': prices,
        'high': [p * 1.001 for p in prices],
        'low': [p * 0.999 for p in prices], 
        'close': prices
    })
    
    trade = {
        'num': 1, 'side': 'LONG', 'entryDt': times[0], 'exitDt': times[-1],
        'entryPrice': 1.0, 'exitPrice': prices[-1], 'pnlPct': 0.4
    }
    
    print("🔍 DEBUGGING BE LOGIC:")
    print("Prices:", [f"{p:.4f}" for p in prices])
    print("Expected: BE trigger at 1.01, SL moves to 1.003 (entry+0.3%)")
    print("Final price 1.004 should NOT hit SL 1.003")
    
    # Call simulate_trade function directly
    result, log = backtest_module.simulate_trade(trade, df, 10, 1.0, 0, 0)
    
    print(f"\n📋 FULL DEBUG LOG:")
    for i, line in enumerate(log):
        print(f"{i+1:2d}. {line}")
    
    if result:
        print(f"\n📊 FINAL RESULT:")
        print(f"   PnL: {result['pnlPct']:.4f}%")
        print(f"   Exit: {result['exitType']}")
        print(f"   Exit Price: {result['exitPrice']:.4f}")
    
    # Manual calculation check
    print(f"\n🧮 MANUAL CHECK:")
    entry = 1.0
    be_sl = entry * (1 + 0.3/100)  # entry + 0.3%
    final_price = prices[-1]
    print(f"   Entry: {entry:.4f}")
    print(f"   BE SL should be: {be_sl:.4f}")
    print(f"   Final price: {final_price:.4f}")
    print(f"   SL triggered?: {final_price <= be_sl}")

if __name__ == "__main__":
    debug_be_with_logs()