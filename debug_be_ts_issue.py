#!/usr/bin/env python3
"""
Debug specific SAGA trade to understand why BE+TS reduces PnL from 274% to <100%
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from web_backtest.backtest_gridsearch_slbe_ts_Version3 import simulate_trade, load_trade_csv, load_candle_csv

def debug_saga_trade():
    """Debug SAGA trades to find why BE+TS kills profits"""
    
    print("🔍 Loading SAGA data...")
    
    # Load trade data
    try:
        pairs = load_trade_csv("SAGAUSDT_30m_BS4_v1")
        print(f"✅ Loaded {len(pairs)} SAGA trades")
    except Exception as e:
        print(f"❌ Error loading trades: {e}")
        return
    
    # Load candle data  
    try:
        df_candle = load_candle_csv("BINANCE_SAGAUSDT_30m.db")
        print(f"✅ Loaded {len(df_candle)} SAGA candles")
    except Exception as e:
        print(f"❌ Error loading candles: {e}")
        return
    
    if not pairs:
        print("❌ No trades to analyze")
        return
    
    # Find high-profit trades to debug
    high_profit_trades = []
    for pair in pairs:
        original_pnl = pair.get('pnlPct', 0)
        if abs(original_pnl) > 50:  # Focus on trades with >50% profit
            high_profit_trades.append(pair)
    
    print(f"🎯 Found {len(high_profit_trades)} high-profit trades (>50%)")
    
    if not high_profit_trades:
        print("❌ No high-profit trades found")
        return
    
    # Test different scenarios on first high-profit trade
    test_trade = high_profit_trades[0]
    print(f"\n🧪 Testing trade #{test_trade['num']} - Original PnL: {test_trade.get('pnlPct', 0):.2f}%")
    
    scenarios = [
        {"name": "Original (no SL/BE/TS)", "sl": 0, "be": 0, "ts_trig": 0, "ts_step": 0},
        {"name": "SL only 5%", "sl": 5.0, "be": 0, "ts_trig": 0, "ts_step": 0},
        {"name": "SL + BE (1%)", "sl": 5.0, "be": 1.0, "ts_trig": 0, "ts_step": 0},
        {"name": "SL + TS (2%, 0.5%)", "sl": 5.0, "be": 0, "ts_trig": 2.0, "ts_step": 0.5},
        {"name": "SL + BE + TS", "sl": 5.0, "be": 1.0, "ts_trig": 2.0, "ts_step": 0.5},
        {"name": "Conservative BE+TS", "sl": 5.0, "be": 2.0, "ts_trig": 5.0, "ts_step": 1.0},
    ]
    
    print(f"\n{'Scenario':<25} {'PnL%':<10} {'Exit Type':<10} {'Details'}")
    print("=" * 70)
    
    for scenario in scenarios:
        try:
            result, log = simulate_trade(
                test_trade, df_candle, 
                scenario["sl"], scenario["be"], 
                scenario["ts_trig"], scenario["ts_step"]
            )
            
            if result:
                pnl = result.get('pnlPct', 0)
                exit_type = result.get('exitType', 'Unknown')
                
                # Show key events from log
                key_events = []
                for line in log:
                    if 'ACTIVATED' in line or 'HIT' in line or 'UPDATED' in line:
                        key_events.append(line.split(' ')[-1])
                
                details = ' | '.join(key_events[:3]) if key_events else 'Normal exit'
                
                print(f"{scenario['name']:<25} {pnl:<10.2f} {exit_type:<10} {details}")
                
                # Show detailed log for problematic scenarios
                if scenario['name'] in ['SL + BE + TS'] and pnl < 100:
                    print(f"\n🔍 DETAILED LOG for {scenario['name']}:")
                    for line in log[-20:]:  # Last 20 lines
                        if any(key in line for key in ['ACTIVATED', 'HIT', 'UPDATED', 'Candle']):
                            print(f"   {line}")
                    print()
                    
            else:
                print(f"{scenario['name']:<25} {'ERROR':<10} {'Failed':<10}")
                
        except Exception as e:
            print(f"{scenario['name']:<25} {'ERROR':<10} {str(e):<10}")
    
    print(f"\n📊 Analysis Summary:")
    print(f"- Original trade PnL: {test_trade.get('pnlPct', 0):.2f}%")
    print(f"- Entry: {test_trade.get('entryPrice', 0):.4f}")
    print(f"- Exit: {test_trade.get('exitPrice', 0):.4f}")
    print(f"- Side: {test_trade.get('side', 'Unknown')}")

if __name__ == "__main__":
    debug_saga_trade()