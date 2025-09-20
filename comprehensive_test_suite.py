# COMPREHENSIVE SIMULATION TESTING SUITE
# Catch bugs like SL exit price error before they cause issues
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Temporarily enable DEBUG for testing
import backtest_gridsearch_slbe_ts_Version3
original_debug = backtest_gridsearch_slbe_ts_Version3.DEBUG
backtest_gridsearch_slbe_ts_Version3.DEBUG = True

from backtest_gridsearch_slbe_ts_Version3 import simulate_trade
import pandas as pd
import numpy as np

def restore_debug():
    """Restore original DEBUG setting"""
    backtest_gridsearch_slbe_ts_Version3.DEBUG = original_debug

def create_test_candles():
    """Create test candle data for comprehensive testing"""
    return pd.DataFrame({
        'time': pd.date_range('2025-01-01 10:00:00', periods=10, freq='1min'),
        'open': [100.0, 101.0, 102.0, 103.0, 104.0, 103.0, 102.0, 101.0, 100.0, 99.0],
        'high': [100.5, 101.5, 103.5, 104.5, 105.0, 103.5, 102.5, 101.5, 100.5, 99.5],
        'low':  [99.5,  100.0, 101.0, 102.0, 103.0, 102.0, 101.0, 100.0, 99.0,  98.0],
        'close':[100.0, 101.0, 102.0, 103.0, 104.0, 103.0, 102.0, 101.0, 100.0, 99.0]
    })

def test_sl_exit_accuracy():
    """Test SL exits at exact SL price, not candle extremes"""
    print("🔍 TESTING SL EXIT ACCURACY")
    
    df_candle = create_test_candles()
    
    # LONG position with SL that should trigger
    pair = {
        'num': 1,
        'side': 'LONG',
        'entryDt': df_candle.iloc[0]['time'],
        'exitDt': df_candle.iloc[-1]['time'],
        'entryPrice': 100.0,
        'exitPrice': 99.0
    }
    
    # Test aggressive SL
    result, log = simulate_trade(pair, df_candle, sl=2.0, be=0, ts_trig=0, ts_step=0)
    
    if backtest_gridsearch_slbe_ts_Version3.DEBUG:
        print(f"📋 Trade simulation log:")
        for line in log[:5]:  # Show first 5 log lines
            print(f"   {line}")
    
    if result:
        sl_price = 100.0 * (1 - 2.0/100)  # Expected SL = 98.0
        print(f"   Entry: {result['entryPrice']:.2f}")
        print(f"   Expected SL: {sl_price:.2f}")
        print(f"   Exit Price: {result['exitPrice']:.2f}")
        print(f"   Exit Type: {result['exitType']}")
        print(f"   PnL: {result['pnlPct']:.2f}%")
        
        # Verification
        is_sl_hit = result['exitType'] in ['SL', 'TS SL']
        correct_exit_price = abs(result['exitPrice'] - sl_price) < 0.001
        correct_pnl = abs(result['pnlPct'] - (-2.0)) < 0.01
        
        if is_sl_hit and correct_exit_price and correct_pnl:
            print("   ✅ SL EXIT ACCURACY: CORRECT")
        else:
            print("   ❌ SL EXIT ACCURACY: ERROR")
            if not is_sl_hit:
                print(f"      Expected SL hit, got {result['exitType']}")
            if not correct_exit_price:
                print(f"      Wrong exit price: {result['exitPrice']:.4f} vs {sl_price:.4f}")
            if not correct_pnl:
                print(f"      Wrong PnL: {result['pnlPct']:.2f}% vs -2.00%")
    else:
        print("   ❌ NO RESULT RETURNED")

def test_be_trigger_accuracy():
    """Test BE triggers at correct price and moves SL correctly"""
    print("\n🔍 TESTING BE TRIGGER ACCURACY")
    
    df_candle = create_test_candles()
    
    # LONG position that should trigger BE
    pair = {
        'num': 2,
        'side': 'LONG', 
        'entryDt': df_candle.iloc[0]['time'],
        'exitDt': df_candle.iloc[-1]['time'],
        'entryPrice': 100.0,
        'exitPrice': 99.0
    }
    
    # Test BE=3% (should trigger at 103.0)
    result, log = simulate_trade(pair, df_candle, sl=2.0, be=3.0, ts_trig=0, ts_step=0)
    
    be_trigger_price = 100.0 * (1 + 3.0/100)  # Expected BE trigger = 103.0
    
    if result:
        print(f"   Entry: {result['entryPrice']:.2f}")
        print(f"   Expected BE trigger: {be_trigger_price:.2f}")
        print(f"   Exit Type: {result['exitType']}")
        print(f"   PnL: {result['pnlPct']:.2f}%")
        
        # Check if BE was triggered in logs
        be_triggered = any("BE kích hoạt" in line for line in log)
        
        if be_triggered:
            print("   ✅ BE TRIGGER: DETECTED IN LOGS")
        else:
            print("   ❌ BE TRIGGER: NOT DETECTED")
            
        # Since price goes to 104.0, BE should trigger but final PnL depends on final exit
        if result['exitType'] == 'EXIT':  # Normal exit, not SL
            print("   ✅ BE LOGIC: WORKING (no SL hit after BE)")
        else:
            print(f"   ⚠️ BE LOGIC: Unexpected exit type {result['exitType']}")

def test_ts_update_accuracy():
    """Test Trailing Stop updates correctly"""
    print("\n🔍 TESTING TS UPDATE ACCURACY")
    
    df_candle = create_test_candles()
    
    # LONG position for TS testing
    pair = {
        'num': 3,
        'side': 'LONG',
        'entryDt': df_candle.iloc[0]['time'],
        'exitDt': df_candle.iloc[-1]['time'],
        'entryPrice': 100.0,
        'exitPrice': 99.0
    }
    
    # Test TS trigger=3%, step=1%
    result, log = simulate_trade(pair, df_candle, sl=10.0, be=0, ts_trig=3.0, ts_step=1.0)
    
    if result:
        print(f"   Entry: {result['entryPrice']:.2f}")
        print(f"   Exit Type: {result['exitType']}")
        print(f"   PnL: {result['pnlPct']:.2f}%")
        
        # Check TS activation and updates in logs
        ts_activated = any("Trailing kích hoạt" in line for line in log)
        ts_updates = sum(1 for line in log if "trailingSL update" in line)
        
        print(f"   TS Activated: {ts_activated}")
        print(f"   TS Updates: {ts_updates}")
        
        if ts_activated and ts_updates > 0:
            print("   ✅ TS LOGIC: WORKING")
        else:
            print("   ❌ TS LOGIC: ISSUES")

def test_calculation_consistency():
    """Test PnL calculation consistency"""
    print("\n🔍 TESTING CALCULATION CONSISTENCY")
    
    df_candle = create_test_candles()
    
    # Simple exit test
    pair = {
        'num': 4,
        'side': 'LONG',
        'entryDt': df_candle.iloc[0]['time'],
        'exitDt': df_candle.iloc[4]['time'],  # Exit at 5th candle
        'entryPrice': 100.0,
        'exitPrice': 104.0
    }
    
    result, log = simulate_trade(pair, df_candle, sl=0, be=0, ts_trig=0, ts_step=0)
    
    if result:
        entry = result['entryPrice']
        exit_price = result['exitPrice']
        reported_pnl = result['pnlPct']
        
        # Manual calculation
        expected_pnl = (exit_price - entry) / entry * 100
        
        print(f"   Entry: {entry:.2f}")
        print(f"   Exit: {exit_price:.2f}")
        print(f"   Reported PnL: {reported_pnl:.2f}%")
        print(f"   Expected PnL: {expected_pnl:.2f}%")
        
        if abs(reported_pnl - expected_pnl) < 0.01:
            print("   ✅ PNL CALCULATION: CONSISTENT")
        else:
            print("   ❌ PNL CALCULATION: INCONSISTENT")

def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print("🚀 COMPREHENSIVE SIMULATION TESTING SUITE")
    print("=" * 50)
    
    test_sl_exit_accuracy()
    test_be_trigger_accuracy()
    test_ts_update_accuracy()
    test_calculation_consistency()
    
    print("\n" + "=" * 50)
    print("🏁 COMPREHENSIVE TESTING COMPLETE")
    print("💡 RECOMMENDATION: Run this suite after any simulation changes")
    
    # Restore original DEBUG setting
    restore_debug()

if __name__ == "__main__":
    run_comprehensive_tests()