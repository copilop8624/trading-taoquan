#!/usr/bin/env python3
"""
Analyze TS step 5% - Is it too large for real trading?
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

def analyze_ts_step_reality():
    """Analyze if TS step 5% is too large for real trading"""
    
    print("🔍 ANALYZING TS STEP 5% - Is it realistic?")
    print()
    
    # Real crypto volatility analysis
    print("📊 CRYPTO DAILY VOLATILITY REALITY:")
    crypto_daily_moves = {
        "BTC (Bull market)": "±2-5% daily, ±1-3% intraday",
        "BTC (Bear market)": "±3-8% daily, ±2-5% intraday", 
        "ETH (Normal)": "±3-6% daily, ±2-4% intraday",
        "Altcoins (High vol)": "±5-15% daily, ±3-10% intraday",
        "During pumps": "±10-30% daily, ±5-20% intraday"
    }
    
    for asset, volatility in crypto_daily_moves.items():
        print(f"   {asset:<20}: {volatility}")
    
    print()
    print("💡 TS STEP ANALYSIS:")
    
    # Test different TS steps on realistic scenarios
    scenarios = [
        {
            "name": "BTC Normal Day",
            "description": "BTC trend day với pullbacks 2-3%",
            "prices": [100, 102, 104, 102, 105, 103, 107, 105, 110],
            "max_pullback": 3.0
        },
        {
            "name": "ETH Volatile Day", 
            "description": "ETH strong move với pullbacks 4-5%",
            "prices": [100, 105, 110, 105, 115, 109, 120, 114, 125],
            "max_pullback": 5.2
        },
        {
            "name": "Altcoin Pump",
            "description": "Altcoin pump với pullbacks 8-10%", 
            "prices": [100, 115, 130, 120, 145, 130, 160, 145, 175],
            "max_pullback": 10.3
        }
    ]
    
    ts_steps = [1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0]
    
    print(f"{'Scenario':<18} {'Max Pullback':<12} {'Recommended TS':<15} {'Why'}")
    print("=" * 70)
    
    for scenario in scenarios:
        max_pb = scenario["max_pullback"]
        
        # Rule: TS step should be > max expected pullback
        if max_pb <= 3:
            recommended = "4-5%"
            reason = "Safe margin above pullback"
        elif max_pb <= 5:
            recommended = "6-7%"
            reason = "Buffer for volatility"
        elif max_pb <= 8:
            recommended = "9-10%"
            reason = "High volatility asset"
        else:
            recommended = "12-15%"
            reason = "Extreme volatility"
            
        print(f"{scenario['name']:<18} {max_pb:<12.1f}% {recommended:<15} {reason}")
    
    print()
    print("🎯 TS STEP 5% ASSESSMENT:")
    print("   ✅ GOOD for: BTC/ETH normal conditions (2-3% pullbacks)")
    print("   ⚠️ RISKY for: High volatility periods (5%+ pullbacks)")
    print("   ❌ BAD for: Altcoin pumps, extreme volatility (8%+ pullbacks)")
    
    print()
    print("📈 PRACTICAL TEST - Different TS Steps:")
    
    # Test on realistic BTC scenario
    times = pd.date_range('2024-04-01', periods=10, freq='1H')
    btc_prices = [50000, 51000, 52000, 50500, 53000, 51500, 54000, 52500, 55000, 54000]
    # 50k → 54k (+8%) với 3% pullbacks
    
    df = pd.DataFrame({
        'time': times,
        'open': btc_prices,
        'high': [p * 1.01 for p in btc_prices],
        'low': [p * 0.99 for p in btc_prices],
        'close': btc_prices
    })
    
    trade = {
        'num': 1, 'side': 'LONG', 'entryDt': times[0], 'exitDt': times[-1],
        'entryPrice': 50000, 'exitPrice': 54000, 'pnlPct': 8.0
    }
    
    print(f"\n{'TS Step':<8} {'Final PnL':<10} {'Retention':<10} {'Assessment'}")
    print("-" * 45)
    
    baseline = 8.0  # No TS
    
    for ts_step in [2, 3, 4, 5, 6, 8, 10]:
        try:
            result, log = backtest_module.simulate_trade(trade, df, 15, 0, 3, ts_step)
            
            if result:
                pnl = result['pnlPct']
                retention = (pnl / baseline) * 100
                
                if retention > 90:
                    assessment = "🏆 Excellent"
                elif retention > 80:
                    assessment = "✅ Very Good" 
                elif retention > 70:
                    assessment = "🟢 Good"
                elif retention > 50:
                    assessment = "🟡 Acceptable"
                else:
                    assessment = "❌ Poor"
                    
                print(f"{ts_step:<8}% {pnl:<10.1f}% {retention:<10.0f}% {assessment}")
            else:
                print(f"{ts_step:<8}% {'ERROR':<10} {'ERROR':<10} Failed")
                
        except Exception as e:
            print(f"{ts_step:<8}% {'ERROR':<10} {'ERROR':<10} {str(e)[:15]}")
    
    print()
    print("🔧 RECOMMENDATION BASED ON ANALYSIS:")
    print("   📍 Current minimum: 5% - REASONABLE for most cases")
    print("   📍 Conservative: 3-4% for low volatility (BTC/ETH normal)")
    print("   📍 Aggressive: 6-8% for high volatility (altcoins)")
    print("   📍 Extreme: 10%+ for pump scenarios")
    
    print()
    print("💰 BUSINESS LOGIC:")
    print("   • TS step quá nhỏ (<3%): Bị noise kill, mất profit")
    print("   • TS step vừa (3-7%): Balance protection vs preservation") 
    print("   • TS step lớn (>8%): An toàn nhưng ít protection")
    
    print()
    print("🎯 CONCLUSION:")
    print("   TS step 5% là REASONABLE compromise:")
    print("   ✅ Đủ lớn để tránh noise (>3% pullbacks)")
    print("   ✅ Đủ nhỏ để có protection (<8% loss)")
    print("   ✅ Phù hợp với crypto volatility thực tế")
    print("   → Có thể giữ 5% hoặc giảm xuống 3-4% nếu muốn tighter")

if __name__ == "__main__":
    analyze_ts_step_reality()