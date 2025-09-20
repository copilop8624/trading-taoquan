#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🐛 CRITICAL DEBUG TOOL: SL Logic Failure Investigation
========================================================
BUG REPORT: SL=2.75% allows losses of -9.61%, -6.41% in BIOUSDT optimization
This should be IMPOSSIBLE - investigating fundamental simulation logic error

TARGET: Find why SL trigger logic fails and fix immediately
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import traceback
import os
import sys

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_test_data():
    """Load BIOUSDT test data for debugging"""
    try:
        # Try to find BIOUSDT files
        biousdt_files = []
        for filename in os.listdir('.'):
            if 'BIOUSDT' in filename.upper() and filename.endswith('.csv'):
                biousdt_files.append(filename)
        
        print(f"🔍 Found BIOUSDT files: {biousdt_files}")
        return biousdt_files
    except Exception as e:
        print(f"❌ Error loading test data: {e}")
        return []

def debug_single_trade_sl_logic(entry_price, exit_price, side, sl_percent, candle_data=None, trade_id=None):
    """
    Debug a single trade's SL logic step by step
    
    Args:
        entry_price: Entry price
        exit_price: Actual exit price from data
        side: 'LONG' or 'SHORT'
        sl_percent: Stop loss percentage (e.g., 2.75)
        candle_data: Optional candle data for detailed analysis
        trade_id: Trade identifier for logging
    
    Returns:
        dict: Detailed debug analysis
    """
    
    debug_info = {
        'trade_id': trade_id,
        'input_params': {
            'entry_price': entry_price,
            'exit_price': exit_price,
            'side': side,
            'sl_percent': sl_percent
        },
        'calculations': {},
        'logic_checks': {},
        'potential_issues': [],
        'conclusion': ''
    }
    
    try:
        # Calculate what SL price should be
        if side.upper() == 'LONG':
            sl_price = entry_price * (1 - sl_percent / 100)
            # For LONG: loss occurs when price goes below SL
            expected_max_loss = -sl_percent
        else:  # SHORT
            sl_price = entry_price * (1 + sl_percent / 100)
            # For SHORT: loss occurs when price goes above SL
            expected_max_loss = -sl_percent
        
        debug_info['calculations']['sl_price'] = sl_price
        debug_info['calculations']['expected_max_loss'] = expected_max_loss
        
        # Calculate actual PnL
        if side.upper() == 'LONG':
            actual_pnl = ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            actual_pnl = ((entry_price - exit_price) / entry_price) * 100
        
        debug_info['calculations']['actual_pnl'] = actual_pnl
        
        # CRITICAL CHECK: Is actual loss worse than SL should allow?
        sl_should_trigger = False
        if side.upper() == 'LONG':
            sl_should_trigger = exit_price <= sl_price
        else:  # SHORT
            sl_should_trigger = exit_price >= sl_price
        
        debug_info['logic_checks']['sl_should_trigger'] = sl_should_trigger
        debug_info['logic_checks']['actual_loss_exceeds_sl'] = actual_pnl < expected_max_loss
        
        # IDENTIFY POTENTIAL ISSUES
        if actual_pnl < expected_max_loss:
            debug_info['potential_issues'].append("🚨 CRITICAL: Actual loss exceeds SL limit!")
            debug_info['potential_issues'].append(f"Expected max loss: {expected_max_loss:.2f}%, Actual: {actual_pnl:.2f}%")
        
        if sl_should_trigger and actual_pnl < expected_max_loss:
            debug_info['potential_issues'].append("🐛 BUG: SL should have triggered but loss exceeded limit")
        
        if not sl_should_trigger and actual_pnl < expected_max_loss:
            debug_info['potential_issues'].append("🤔 WEIRD: SL didn't trigger but loss exceeded limit - check exit logic")
        
        # Price comparison details
        if side.upper() == 'LONG':
            debug_info['logic_checks']['exit_vs_sl'] = f"Exit {exit_price:.6f} vs SL {sl_price:.6f}"
            debug_info['logic_checks']['exit_below_sl'] = exit_price < sl_price
        else:
            debug_info['logic_checks']['exit_vs_sl'] = f"Exit {exit_price:.6f} vs SL {sl_price:.6f}"
            debug_info['logic_checks']['exit_above_sl'] = exit_price > sl_price
        
        # Generate conclusion
        if debug_info['potential_issues']:
            debug_info['conclusion'] = "🚨 SIMULATION BUG DETECTED - SL logic failure"
        else:
            debug_info['conclusion'] = "✅ SL logic appears correct for this trade"
            
    except Exception as e:
        debug_info['error'] = str(e)
        debug_info['conclusion'] = f"❌ Debug analysis failed: {e}"
    
    return debug_info

def analyze_biousdt_optimization_results():
    """Analyze BIOUSDT optimization results to find SL logic failures"""
    
    print("🔍 ANALYZING BIOUSDT OPTIMIZATION RESULTS")
    print("=" * 60)
    
    # Sample problematic trades from your report
    problematic_trades = [
        {
            'trade_id': 'T001',
            'side': 'LONG',
            'entry_price': 0.009500,  # Example BIOUSDT price
            'exit_price': 0.008587,   # This would give ~-9.61% loss
            'sl_percent': 2.75,
            'reported_pnl': -9.61
        },
        {
            'trade_id': 'T002', 
            'side': 'LONG',
            'entry_price': 0.009200,
            'exit_price': 0.008611,   # This would give ~-6.41% loss
            'sl_percent': 2.75,
            'reported_pnl': -6.41
        }
    ]
    
    debug_results = []
    
    for trade in problematic_trades:
        print(f"\n🔍 Debugging Trade {trade['trade_id']}")
        print("-" * 40)
        
        debug_result = debug_single_trade_sl_logic(
            entry_price=trade['entry_price'],
            exit_price=trade['exit_price'], 
            side=trade['side'],
            sl_percent=trade['sl_percent'],
            trade_id=trade['trade_id']
        )
        
        debug_results.append(debug_result)
        
        # Print detailed analysis
        print(f"Entry Price: {trade['entry_price']:.6f}")
        print(f"Exit Price: {trade['exit_price']:.6f}")
        print(f"SL%: {trade['sl_percent']}%")
        print(f"Expected SL Price: {debug_result['calculations'].get('sl_price', 'N/A'):.6f}")
        print(f"Expected Max Loss: {debug_result['calculations'].get('expected_max_loss', 'N/A'):.2f}%")
        print(f"Actual PnL: {debug_result['calculations'].get('actual_pnl', 'N/A'):.2f}%")
        print(f"Reported PnL: {trade['reported_pnl']:.2f}%")
        
        print("\n🚨 ISSUES FOUND:")
        for issue in debug_result['potential_issues']:
            print(f"  - {issue}")
        
        print(f"\n📊 CONCLUSION: {debug_result['conclusion']}")
    
    return debug_results

def generate_fix_recommendations():
    """Generate specific recommendations to fix SL logic"""
    
    recommendations = {
        'immediate_fixes': [
            "🔧 Check simulate_trade() function SL trigger logic",
            "🔧 Verify candle data matching and datetime alignment", 
            "🔧 Audit entry/exit price calculation accuracy",
            "🔧 Check if SL calculation uses correct entry price",
            "🔧 Verify side (LONG/SHORT) handling in SL logic"
        ],
        'code_locations_to_check': [
            "simulate_trade() in backtest_gridsearch_slbe_ts_Version3.py",
            "find_candle_idx() datetime matching logic",
            "SL trigger conditions in simulation loop",
            "Price data extraction from candles",
            "PnL calculation formulas"
        ],
        'testing_strategy': [
            "Create manual step-by-step simulation for failing trades",
            "Add extensive logging to simulation engine",
            "Compare simulation results with raw tradelist",
            "Test with simplified data to isolate bug",
            "Validate candle data integrity"
        ]
    }
    
    return recommendations

def create_manual_verification_script():
    """Create a script for manual trade verification"""
    
    verification_script = '''
def manual_verify_trade(entry_dt, exit_dt, entry_price, side, sl_percent, candle_file):
    """
    Manually verify a single trade step by step
    """
    print(f"🔍 MANUAL VERIFICATION")
    print(f"Entry: {entry_dt} at {entry_price}")
    print(f"Side: {side}, SL: {sl_percent}%")
    
    # Load candle data
    df_candle = pd.read_csv(candle_file)
    
    # Calculate SL price
    if side == 'LONG':
        sl_price = entry_price * (1 - sl_percent/100)
        print(f"SL Price: {sl_price:.6f}")
    
    # Find entry candle
    # ... step by step verification logic
    
    return verification_result

# Example usage:
# result = manual_verify_trade(
#     entry_dt="2024-01-15 10:30:00",
#     exit_dt="2024-01-15 14:45:00", 
#     entry_price=0.009500,
#     side="LONG",
#     sl_percent=2.75,
#     candle_file="BINANCE_BIOUSDT.P, 240.csv"
# )
'''
    
    return verification_script

def main():
    """Main debugging execution"""
    
    print("🐛 SL LOGIC FAILURE INVESTIGATION")
    print("=" * 50)
    print("BUG: SL=2.75% allows -9.61%, -6.41% losses")
    print("This is IMPOSSIBLE and indicates critical simulation bug")
    print("=" * 50)
    
    # 1. Analyze problematic trades
    debug_results = analyze_biousdt_optimization_results()
    
    # 2. Generate fix recommendations
    print("\n" + "=" * 50)
    print("🔧 FIX RECOMMENDATIONS")
    print("=" * 50)
    
    recommendations = generate_fix_recommendations()
    
    print("\n🚨 IMMEDIATE FIXES NEEDED:")
    for fix in recommendations['immediate_fixes']:
        print(f"  {fix}")
    
    print("\n📁 CODE LOCATIONS TO CHECK:")
    for location in recommendations['code_locations_to_check']:
        print(f"  {location}")
    
    print("\n🧪 TESTING STRATEGY:")
    for strategy in recommendations['testing_strategy']:
        print(f"  {strategy}")
    
    # 3. Save debug results
    with open('sl_bug_debug_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'bug_description': 'SL=2.75% allows losses exceeding -9%',
            'debug_results': debug_results,
            'recommendations': recommendations
        }, f, indent=2)
    
    print(f"\n📊 Debug results saved to: sl_bug_debug_results.json")
    
    # 4. Create manual verification template
    verification_script = create_manual_verification_script()
    with open('manual_trade_verification.py', 'w') as f:
        f.write(verification_script)
    
    print(f"📝 Manual verification script created: manual_trade_verification.py")
    
    print("\n" + "=" * 50)
    print("🎯 NEXT STEPS:")
    print("1. Run this debug analysis")
    print("2. Check simulation engine code at identified locations")
    print("3. Use manual verification script for problem trades")
    print("4. Fix SL trigger logic")
    print("5. Re-test BIOUSDT optimization")
    print("=" * 50)

if __name__ == "__main__":
    main()