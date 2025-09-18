#!/usr/bin/env python3
"""
DEBUG TEST: Enable DEBUG mode to see detailed logic flow
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'web_backtest'))

import pandas as pd
import numpy as np

# Enable DEBUG mode
import backtest_gridsearch_slbe_ts_Version3_FIXED as sim_module
sim_module.DEBUG = True

from backtest_gridsearch_slbe_ts_Version3_FIXED import simulate_trade

def debug_be_test():
    """Debug BE test with detailed logging"""
    print("🔍 DEBUG BE TEST")
    print("=" * 50)
    
    # Simple scenario: Price goes up (BE triggers), then back to entry
    candles = pd.DataFrame({
        'time': pd.date_range('2025-01-01', periods=4, freq='1min'),
        'open': [100.0, 101.5, 100.5, 100.0],
        'high': [100.2, 101.8, 100.8, 100.1],
        'low': [99.9, 101.2, 100.0, 99.9],
        'close': [101.5, 100.5, 100.0, 100.0]
    })
    
    pair_data = {
        'num': 1,
        'side': 'LONG',
        'entryDt': candles.iloc[0]['time'],
        'entryPrice': 100.0,
        'exitDt': candles.iloc[-1]['time'],
        'exitPrice': candles.iloc[-1]['close']
    }
    
    print("📊 TESTING WITH BE=1.0 (triggers at 101.0)")
    result, log = simulate_trade(pair_data, candles, sl=2.0, be=1.0, ts_trig=0, ts_step=0)
    
    print(f"\nResult: {result}")
    print(f"\nDetailed Log:")
    for line in log:
        print(f"  {line}")
    
    print(f"\n📈 Final: PnL={result['pnlPct']:.2f}%, Exit={result['exitType']}, Price={result['exitPrice']:.4f}")

if __name__ == "__main__":
    debug_be_test()