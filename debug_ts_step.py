#!/usr/bin/env python3
"""
Debug why TS 5% still gives only 38% instead of higher retention
"""

import pandas as pd
import numpy as np
import sys
import os
import importlib

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Force reload
import web_backtest.backtest_gridsearch_slbe_ts_Version3 as backtest_module
importlib.reload(backtest_module)

def debug_ts_behavior():
    """Debug TS with fewer price points to see step-by-step"""
    
    # Simplified scenario: 1.0 → 2.0 with one pullback
    times = pd.date_range('2024-04-01', periods=8, freq='30T')
    prices = [
        1.0,    # Entry
        1.03,   # +3%
        1.08,   # +8% (TS trigger at 5%)
        1.15,   # +15% 
        1.20,   # +20% peak
        1.15,   # -4% pullback (should not hit TS)
        1.18,   # Recovery
        2.0     # Final +100%
    ]
    
    df = pd.DataFrame({
        'time': times,
        'open': prices,
        'high': [p * 1.002 for p in prices],
        'low': [p * 0.998 for p in prices],
        'close': prices
    })
    
    trade = {
        'num': 1, 'side': 'LONG', 'entryDt': times[0], 'exitDt': times[-1],
        'entryPrice': 1.0, 'exitPrice': 2.0, 'pnlPct': 100.0
    }
    
    print("🔍 TS DEBUG:")
    print("Prices:", [f"{p:.3f}" for p in prices])
    print("TS trigger at +5% (1.05), TS step 5%")
    print("At peak 1.20: TS SL = 1.20 * (1-0.05) = 1.14")
    print("Pullback to 1.15 should NOT hit TS SL 1.14")
    
    # Test different TS steps
    for ts_step in [5.0, 8.0, 10.0, 15.0]:
        result, log = backtest_module.simulate_trade(trade, df, 20, 0, 5.0, ts_step)
        
        if result:
            pnl = result['pnlPct']
            exit_type = result['exitType']
            exit_price = result['exitPrice']
            
            print(f"\nTS {ts_step:4.1f}%: PnL={pnl:6.1f}% | Exit={exit_type} | Price={exit_price:.3f}")
            
            # Show TS events
            ts_events = [line for line in log if 'TS' in line and ('ACTIVATED' in line or 'UPDATED' in line or 'HIT' in line)]
            for event in ts_events:
                print(f"     🔍 {event}")
        else:
            print(f"TS {ts_step:4.1f}%: ERROR")
    
    print(f"\n💡 EXPECTATION:")
    print(f"   TS step ≥10% should allow 100% profit retention")
    print(f"   TS step 5-8% should allow 80-90% retention") 
    print(f"   Current results suggest TS is still too aggressive")

if __name__ == "__main__":
    debug_ts_behavior()