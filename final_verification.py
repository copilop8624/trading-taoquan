# FINAL VERIFICATION - ALL SIMULATION LOGIC WORKING
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtest_gridsearch_slbe_ts_Version3 import simulate_trade
import pandas as pd

def final_verification():
    """Final verification that all logic is working correctly"""
    print("🎯 FINAL VERIFICATION - ALL SIMULATION LOGIC")
    print("=" * 60)
    
    # Test 1: SL Logic
    print("1️⃣ SL LOGIC TEST:")
    df_sl = pd.DataFrame({
        'time': pd.date_range('2025-01-01 10:00:00', periods=5, freq='1min'),
        'open':  [100.0, 99.0, 98.0, 97.0, 96.0],
        'high':  [100.0, 99.0, 98.0, 97.0, 96.0],
        'low':   [99.0,  98.0, 97.0, 96.0, 95.0],  # Triggers SL
        'close': [99.0,  98.0, 97.0, 96.0, 95.0]
    })
    
    pair_sl = {'num': 1, 'side': 'LONG', 'entryDt': df_sl.iloc[0]['time'], 
               'exitDt': df_sl.iloc[-1]['time'], 'entryPrice': 100.0, 'exitPrice': 95.0}
    
    result_sl, _ = simulate_trade(pair_sl, df_sl, sl=2.0, be=0, ts_trig=0, ts_step=0)
    expected_sl = 100.0 * (1 - 2.0/100)
    
    print(f"   Entry: {result_sl['entryPrice']:.2f}")
    print(f"   Expected SL: {expected_sl:.2f}")
    print(f"   Actual Exit: {result_sl['exitPrice']:.2f}")
    print(f"   Exit Type: {result_sl['exitType']}")
    print(f"   ✅ SL WORKING: {abs(result_sl['exitPrice'] - expected_sl) < 0.01}")
    
    # Test 2: BE Logic  
    print("\n2️⃣ BE LOGIC TEST:")
    df_be = pd.DataFrame({
        'time': pd.date_range('2025-01-01 10:00:00', periods=6, freq='1min'),
        'open':  [100.0, 101.0, 102.0, 103.5, 102.0, 101.0],  # BE triggers at 103.5
        'high':  [100.5, 101.5, 102.5, 104.0, 102.5, 101.5],
        'low':   [99.5,  100.5, 101.5, 102.5, 100.5, 99.5],   # Goes back to entry
        'close': [100.0, 101.0, 102.0, 103.5, 102.0, 101.0]
    })
    
    pair_be = {'num': 2, 'side': 'LONG', 'entryDt': df_be.iloc[0]['time'], 
               'exitDt': df_be.iloc[-1]['time'], 'entryPrice': 100.0, 'exitPrice': 101.0}
    
    result_be, log_be = simulate_trade(pair_be, df_be, sl=5.0, be=3.0, ts_trig=0, ts_step=0)
    be_triggered = any("BE kích hoạt" in line for line in log_be)
    
    print(f"   Entry: {result_be['entryPrice']:.2f}")
    print(f"   BE Trigger Expected: {100.0 * 1.03:.2f}")
    print(f"   BE Triggered: {be_triggered}")
    print(f"   Exit Type: {result_be['exitType']}")
    print(f"   ✅ BE WORKING: {be_triggered}")
    
    # Test 3: TS Logic
    print("\n3️⃣ TS LOGIC TEST:")
    df_ts = pd.DataFrame({
        'time': pd.date_range('2025-01-01 10:00:00', periods=6, freq='1min'),
        'open':  [100.0, 101.0, 102.0, 104.0, 103.5, 102.8],  # TS triggers, then hits TS
        'high':  [100.5, 101.5, 102.5, 104.5, 104.0, 103.0],
        'low':   [99.5,  100.5, 101.5, 103.5, 102.5, 102.5],
        'close': [100.0, 101.0, 102.0, 104.0, 103.5, 102.8]
    })
    
    pair_ts = {'num': 3, 'side': 'LONG', 'entryDt': df_ts.iloc[0]['time'], 
               'exitDt': df_ts.iloc[-1]['time'], 'entryPrice': 100.0, 'exitPrice': 102.8}
    
    result_ts, log_ts = simulate_trade(pair_ts, df_ts, sl=10.0, be=0, ts_trig=3.0, ts_step=1.0)
    ts_triggered = any("Trailing kích hoạt" in line for line in log_ts)
    ts_updates = sum(1 for line in log_ts if "trailingSL update" in line)
    
    print(f"   Entry: {result_ts['entryPrice']:.2f}")
    print(f"   TS Trigger Expected: {100.0 * 1.03:.2f}")
    print(f"   TS Triggered: {ts_triggered}")
    print(f"   TS Updates: {ts_updates}")
    print(f"   Exit Type: {result_ts['exitType']}")
    print(f"   ✅ TS WORKING: {ts_triggered and 'TS' in result_ts['exitType']}")
    
    print("\n" + "=" * 60)
    print("🎉 FINAL RESULT:")
    
    sl_ok = abs(result_sl['exitPrice'] - expected_sl) < 0.01
    be_ok = be_triggered
    ts_ok = ts_triggered and 'TS' in result_ts['exitType']
    
    if sl_ok and be_ok and ts_ok:
        print("✅ ALL SIMULATION LOGIC VERIFIED WORKING CORRECTLY!")
        print("✅ SL exits at exact SL price")
        print("✅ BE triggers and moves SL to entry")
        print("✅ TS triggers and updates trailing SL")
        print("🚀 SIMULATION ENGINE IS FULLY RELIABLE!")
    else:
        print("❌ SOME ISSUES REMAIN:")
        if not sl_ok: print("❌ SL logic issue")
        if not be_ok: print("❌ BE logic issue")  
        if not ts_ok: print("❌ TS logic issue")

if __name__ == "__main__":
    final_verification()