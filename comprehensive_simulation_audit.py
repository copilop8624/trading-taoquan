#!/usr/bin/env python3
"""
COMPREHENSIVE SIMULATION AUDIT: Phát hiện và fix các vấn đề realism
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'web_backtest'))

import pandas as pd
import numpy as np

def analyze_current_price_sequence():
    """Phân tích vấn đề với get_realistic_price_sequence hiện tại"""
    print("🔍 AUDIT: Current get_realistic_price_sequence Logic")
    print("=" * 60)
    
    # Test case: Bullish candle
    candle_bull = {'open': 100, 'high': 105, 'low': 99, 'close': 104}
    
    # Test case: Bearish candle  
    candle_bear = {'open': 100, 'high': 102, 'low': 95, 'close': 96}
    
    from backtest_gridsearch_slbe_ts_Version3_FIXED import get_realistic_price_sequence
    
    seq_bull = get_realistic_price_sequence(candle_bull)
    seq_bear = get_realistic_price_sequence(candle_bear)
    
    print("BULLISH Candle O=100 H=105 L=99 C=104:")
    print(f"  Sequence: {seq_bull}")
    
    print("BEARISH Candle O=100 H=102 L=95 C=96:")  
    print(f"  Sequence: {seq_bear}")
    
    print("\n🚨 PROBLEMS IDENTIFIED:")
    print("1. Both bullish/bearish use same pattern logic")
    print("2. Always hits both high AND low in same candle (unrealistic)")
    print("3. No intermediate price movements")
    print("4. Pattern doesn't reflect market psychology")
    
    return seq_bull, seq_bear

def design_improved_price_sequence():
    """Thiết kế logic sequence realistic hơn"""
    print("\n💡 IMPROVED REALISTIC PRICE SEQUENCE DESIGN")
    print("=" * 60)
    
    def get_improved_realistic_sequence(candle):
        """
        Improved version: More realistic price movements
        """
        o, h, l, c = candle['open'], candle['high'], candle['low'], candle['close']
        
        # Calculate candle characteristics
        body_size = abs(c - o)
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        range_size = h - l
        
        # Strong bullish (close near high)
        if c > o and (c - o) / range_size > 0.6:
            # Open -> gradual rise -> high -> minor pullback -> close
            mid_price = o + (h - o) * 0.7
            return [
                ('open', o),
                ('mid_rise', mid_price), 
                ('high', h),
                ('close', c)
            ]
        
        # Strong bearish (close near low)
        elif o > c and (o - c) / range_size > 0.6:
            # Open -> gradual fall -> low -> minor bounce -> close
            mid_price = o - (o - l) * 0.7
            return [
                ('open', o),
                ('mid_fall', mid_price),
                ('low', l),
                ('close', c)
            ]
        
        # Doji/indecision (small body, large wicks)
        elif body_size / range_size < 0.3:
            return [
                ('open', o),
                ('high', h),
                ('low', l), 
                ('close', c)
            ]
        
        # Normal bullish
        elif c > o:
            return [
                ('open', o),
                ('high', h),
                ('low', l),
                ('close', c)
            ]
        
        # Normal bearish
        else:
            return [
                ('open', o),
                ('low', l),
                ('high', h), 
                ('close', c)
            ]
    
    # Test improved version
    candles = [
        {'open': 100, 'high': 108, 'low': 99, 'close': 107, 'type': 'Strong Bull'},
        {'open': 100, 'high': 101, 'low': 92, 'close': 93, 'type': 'Strong Bear'},
        {'open': 100, 'high': 102, 'low': 98, 'close': 100.5, 'type': 'Doji'},
        {'open': 100, 'high': 104, 'low': 98, 'close': 103, 'type': 'Normal Bull'},
    ]
    
    for candle in candles:
        seq = get_improved_realistic_sequence(candle)
        print(f"{candle['type']}: {seq}")
    
    return get_improved_realistic_sequence

def check_slippage_realism():
    """Kiểm tra tính realistic của slippage implementation"""
    print("\n🧪 SLIPPAGE REALISM AUDIT")
    print("=" * 50)
    
    print("Current Implementation:")
    print("  - SL Hit: 0.02% slippage (worse execution)")
    print("  - LONG SL: price * (1 - 0.02/100) = worse price")
    print("  - SHORT SL: price * (1 + 0.02/100) = worse price")
    
    print("\nRealism Assessment:")
    print("  ✅ Slippage direction correct (worse for trader)")
    print("  ❓ 0.02% might be low for volatile crypto")
    print("  ❓ Should vary by market conditions")
    print("  ❌ No spread simulation")
    
    # Slippage recommendations
    slippage_scenarios = {
        'Major pairs (BTC/ETH)': '0.01-0.03%',
        'Altcoins': '0.05-0.15%', 
        'High volatility': '0.1-0.5%',
        'Low liquidity': '0.2-1.0%'
    }
    
    print("\n💡 REALISTIC SLIPPAGE BY SCENARIO:")
    for scenario, slip in slippage_scenarios.items():
        print(f"  {scenario}: {slip}")

def audit_be_ts_timing():
    """Audit BE/TS activation timing realism"""
    print("\n⏰ BE/TS TIMING REALISM AUDIT")
    print("=" * 50)
    
    print("Current Logic:")
    print("  1. Check BE activation (if price hit trigger)")
    print("  2. Check TS activation (independent)")
    print("  3. Update trailing SL (if TS active)")
    print("  4. Check SL hit (after all updates)")
    
    print("\nRealism Issues:")
    print("  ❌ BE/TS checked on EVERY price tick (unrealistic frequency)")
    print("  ❓ No order execution delay")
    print("  ❓ Instant SL movement (no manual intervention time)")
    print("  ✅ Logic sequence correct (activation before SL check)")
    
    print("\nImprovement Suggestions:")
    print("  💡 Add execution delay for BE/TS activation")
    print("  💡 Batch updates (not every tick)")
    print("  💡 Manual trailing vs automated")

if __name__ == "__main__":
    print("🚨 COMPREHENSIVE SIMULATION REALISM AUDIT")
    print("=" * 70)
    
    try:
        # Audit current issues
        analyze_current_price_sequence()
        design_improved_price_sequence()
        check_slippage_realism()
        audit_be_ts_timing()
        
        print("\n🎯 SUMMARY OF ISSUES FOUND:")
        print("1. ❌ Price sequence too simplistic (always hits H&L)")
        print("2. ❓ Slippage might need market-specific adjustment") 
        print("3. ❌ BE/TS activation frequency unrealistic")
        print("4. ✅ Core logic flow fixed (BE/TS before SL)")
        
        print("\n🔧 PRIORITY FIXES:")
        print("1. Fix get_realistic_price_sequence with market psychology")
        print("2. Add dynamic slippage based on volatility")
        print("3. Add execution delays for BE/TS")
        
    except Exception as e:
        print(f"❌ Audit failed: {e}")
        import traceback
        traceback.print_exc()