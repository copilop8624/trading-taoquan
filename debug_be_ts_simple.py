#!/usr/bin/env python3
"""
Simple debug for BE/TS logic using hypothetical SAGA-like trade
"""

import pandas as pd
import numpy as np
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from web_backtest.backtest_gridsearch_slbe_ts_Version3 import simulate_trade
    print("✅ Loaded simulate_trade function")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def create_test_data():
    """Create test data mimicking SAGA high-profit scenario"""
    
    # Create candle data representing a strong uptrend (like 274% profit scenario)
    times = pd.date_range('2024-04-01 00:00:00', periods=50, freq='30T')
    
    # Simulate strong uptrend: 1.0 -> 3.74 (274% gain)
    entry_price = 1.0
    final_price = 3.74  # 274% gain
    
    # Create price progression with some volatility
    base_progression = np.linspace(entry_price, final_price, 50)
    volatility = np.random.normal(0, 0.02, 50)  # 2% random volatility
    prices = base_progression + volatility
    
    # Ensure no negative prices and smooth progression
    for i in range(1, len(prices)):
        if prices[i] < prices[i-1] * 0.95:  # Prevent >5% drops
            prices[i] = prices[i-1] * 0.98  # Allow small 2% pullbacks
    
    # Create OHLC data
    candles = []
    for i, price in enumerate(prices):
        if i == 0:
            open_price = entry_price
        else:
            open_price = candles[i-1]['close']
        
        # Add some intracandle volatility
        high = price * 1.01  # 1% higher
        low = price * 0.99   # 1% lower
        close = price
        
        candles.append({
            'time': times[i],
            'open': open_price,
            'high': max(open_price, high, close),
            'low': min(open_price, low, close),
            'close': close
        })
    
    df_candle = pd.DataFrame(candles)
    
    # Create trade pair
    trade = {
        'num': 1,
        'side': 'LONG',
        'entryDt': times[0],
        'exitDt': times[-1],
        'entryPrice': entry_price,
        'exitPrice': final_price,
        'pnlPct': 274.0  # Original PnL
    }
    
    return trade, df_candle

def debug_be_ts_logic():
    """Debug BE/TS behavior on high-profit trade"""
    
    print("🧪 Creating test data for SAGA-like scenario...")
    trade, df_candle = create_test_data()
    
    print(f"📊 Test Trade Setup:")
    print(f"   Entry: {trade['entryPrice']:.4f}")
    print(f"   Original Exit: {trade['exitPrice']:.4f}")
    print(f"   Original PnL: {trade['pnlPct']:.2f}%")
    print(f"   Duration: {len(df_candle)} candles")
    
    # Test scenarios
    scenarios = [
        {"name": "No BE/TS", "sl": 10, "be": 0, "ts_trig": 0, "ts_step": 0},
        {"name": "BE 1% only", "sl": 10, "be": 1.0, "ts_trig": 0, "ts_step": 0},
        {"name": "TS only (2%, 0.5%)", "sl": 10, "be": 0, "ts_trig": 2.0, "ts_step": 0.5},
        {"name": "BE+TS aggressive", "sl": 10, "be": 1.0, "ts_trig": 2.0, "ts_step": 0.5},
        {"name": "BE+TS conservative", "sl": 10, "be": 5.0, "ts_trig": 10.0, "ts_step": 2.0},
    ]
    
    print(f"\n{'Scenario':<20} {'Final PnL%':<12} {'Exit Type':<10} {'Analysis'}")
    print("=" * 75)
    
    for scenario in scenarios:
        try:
            result, log = simulate_trade(
                trade, df_candle,
                scenario["sl"], scenario["be"], 
                scenario["ts_trig"], scenario["ts_step"]
            )
            
            if result:
                final_pnl = result['pnlPct']
                exit_type = result['exitType']
                
                # Analyze what happened
                analysis = ""
                if final_pnl < 50:
                    analysis = "❌ SEVERE PROFIT LOSS"
                elif final_pnl < 150:
                    analysis = "⚠️ Significant reduction"  
                elif final_pnl > 250:
                    analysis = "✅ Good preservation"
                else:
                    analysis = "📉 Moderate reduction"
                
                print(f"{scenario['name']:<20} {final_pnl:<12.2f} {exit_type:<10} {analysis}")
                
                # Show critical events for problematic scenarios
                if scenario['name'] in ['BE+TS aggressive'] and final_pnl < 100:
                    print("\n🔍 CRITICAL EVENTS LOG:")
                    for line in log:
                        if any(keyword in line for keyword in ['ACTIVATED', 'HIT', 'UPDATED']):
                            print(f"   ⚠️ {line}")
                    print()
                    
            else:
                print(f"{scenario['name']:<20} {'ERROR':<12} {'Failed':<10} Simulation failed")
                
        except Exception as e:
            print(f"{scenario['name']:<20} {'ERROR':<12} {'Exception':<10} {str(e)}")
    
    print(f"\n💡 ANALYSIS:")
    print(f"If BE 1% causes severe profit loss, it means:")
    print(f"  1. BE triggers at just 1% profit")
    print(f"  2. Moves SL to entry price (0% profit)")
    print(f"  3. Any pullback = exit with 0% instead of 274%")
    print(f"\nIf TS 0.5% step causes loss, it means:")
    print(f"  1. SL follows price too closely")
    print(f"  2. Normal pullbacks trigger premature exit")
    print(f"  3. Should use wider TS step like 2-5%")

if __name__ == "__main__":
    debug_be_ts_logic()