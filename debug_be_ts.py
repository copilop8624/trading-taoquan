# DEBUG BE/TS ISSUES - STEP BY STEP ANALYSIS
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtest_gridsearch_slbe_ts_Version3 import simulate_trade
import pandas as pd

def debug_be_issue():
    """Debug why BE is not being detected"""
    print("🔍 DEBUGGING BE ISSUE")
    
    # Create candle data where price clearly goes above BE trigger
    df_candle = pd.DataFrame({
        'time': pd.date_range('2025-01-01 10:00:00', periods=8, freq='1min'),
        'open':  [100.0, 101.0, 102.0, 103.5, 104.0, 103.0, 102.0, 101.0],  # Clear move to 103.5, 104.0
        'high':  [100.5, 101.5, 102.5, 104.0, 104.5, 103.5, 102.5, 101.5],
        'low':   [99.5,  100.5, 101.5, 102.5, 103.0, 102.0, 101.0, 100.0],
        'close': [100.0, 101.0, 102.0, 103.5, 104.0, 103.0, 102.0, 101.0]
    })
    
    pair = {
        'num': 1,
        'side': 'LONG',
        'entryDt': df_candle.iloc[0]['time'],
        'exitDt': df_candle.iloc[-1]['time'],
        'entryPrice': 100.0,
        'exitPrice': 101.0
    }
    
    # Test BE=3% (should trigger at 103.0)
    print(f"📊 Setup:")
    print(f"   Entry Price: {pair['entryPrice']}")
    print(f"   BE Setting: 3%")
    print(f"   BE Trigger Price: {100.0 * 1.03} (103.0)")
    print(f"   Max Price in candles: {max(df_candle['high'])} (104.5)")
    
    result, log = simulate_trade(pair, df_candle, sl=10.0, be=3.0, ts_trig=0, ts_step=0)
    
    print(f"\n📋 Full simulation log:")
    for i, line in enumerate(log):
        print(f"   {i+1:2d}: {line}")
    
    if result:
        print(f"\n📊 Result:")
        print(f"   Exit Type: {result['exitType']}")
        print(f"   Exit Price: {result['exitPrice']}")
        print(f"   PnL: {result['pnlPct']:.2f}%")
    
    # Check for BE detection
    be_detected = any("BE kích hoạt" in line for line in log)
    print(f"\n🔍 Analysis:")
    print(f"   BE Detected in logs: {be_detected}")
    if not be_detected:
        print("   ❌ BE NOT TRIGGERED - Need to investigate logic")

def debug_ts_issue():
    """Debug why TS is not being activated"""
    print("\n" + "="*50)
    print("🔍 DEBUGGING TS ISSUE")
    
    # Create candle data where price clearly goes above TS trigger
    df_candle = pd.DataFrame({
        'time': pd.date_range('2025-01-01 10:00:00', periods=8, freq='1min'),
        'open':  [100.0, 101.0, 102.0, 103.5, 105.0, 104.0, 103.0, 102.0],  # Clear move to 105.0
        'high':  [100.5, 101.5, 102.5, 104.0, 105.5, 104.5, 103.5, 102.5],
        'low':   [99.5,  100.5, 101.5, 102.5, 104.0, 103.0, 102.0, 101.0],
        'close': [100.0, 101.0, 102.0, 103.5, 105.0, 104.0, 103.0, 102.0]
    })
    
    pair = {
        'num': 2,
        'side': 'LONG',
        'entryDt': df_candle.iloc[0]['time'],
        'exitDt': df_candle.iloc[-1]['time'],
        'entryPrice': 100.0,
        'exitPrice': 102.0
    }
    
    # Test TS trigger=3%, step=1%
    print(f"📊 Setup:")
    print(f"   Entry Price: {pair['entryPrice']}")
    print(f"   TS Trigger: 3%")
    print(f"   TS Trigger Price: {100.0 * 1.03} (103.0)")
    print(f"   TS Step: 1%")
    print(f"   Max Price in candles: {max(df_candle['high'])} (105.5)")
    
    result, log = simulate_trade(pair, df_candle, sl=10.0, be=0, ts_trig=3.0, ts_step=1.0)
    
    print(f"\n📋 Full simulation log:")
    for i, line in enumerate(log):
        print(f"   {i+1:2d}: {line}")
    
    if result:
        print(f"\n📊 Result:")
        print(f"   Exit Type: {result['exitType']}")
        print(f"   Exit Price: {result['exitPrice']}")
        print(f"   PnL: {result['pnlPct']:.2f}%")
    
    # Check for TS detection
    ts_triggered = any("Trailing kích hoạt" in line for line in log)
    ts_updates = sum(1 for line in log if "trailingSL update" in line)
    
    print(f"\n🔍 Analysis:")
    print(f"   TS Triggered in logs: {ts_triggered}")
    print(f"   TS Updates count: {ts_updates}")
    if not ts_triggered:
        print("   ❌ TS NOT TRIGGERED - Need to investigate logic")

def analyze_issues():
    """Analyze what's wrong with BE/TS logic"""
    print("\n" + "="*50)
    print("🔍 ROOT CAUSE ANALYSIS")
    
    # Let's read the actual logic to see what's wrong
    with open('backtest_gridsearch_slbe_ts_Version3.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Look for BE logic
    if 'use_BE and not BE_reached' in content:
        print("✅ BE logic exists in code")
    else:
        print("❌ BE logic missing or malformed")
    
    # Look for TS logic  
    if 'use_TS and not TS_reached' in content:
        print("✅ TS logic exists in code")
    else:
        print("❌ TS logic missing or malformed")
    
    # Check for DEBUG flag
    if 'DEBUG:' in content:
        print("✅ DEBUG logging exists")
    else:
        print("❌ DEBUG logging missing")

if __name__ == "__main__":
    debug_be_issue()
    debug_ts_issue()
    analyze_issues()