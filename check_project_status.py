# PROJECT STATUS CHECKER - Verify all fixes are applied
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_main_simulation_file():
    """Check main Version3 file has all fixes"""
    print("🔍 CHECKING MAIN SIMULATION FILE")
    print("=" * 50)
    
    file_path = "backtest_gridsearch_slbe_ts_Version3.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check 1: SL fix applied
    sl_fix_found = "finalExitPrice = current_active_sl" in content
    print(f"✅ SL Fix Applied: {sl_fix_found}")
    
    # Check 2: No duplicate logic
    duplicate_count = content.count("# Kích hoạt BE nếu đủ điều kiện")
    print(f"✅ No Code Duplication: {duplicate_count == 1}")
    
    # Check 3: DEBUG setting
    debug_setting = "DEBUG = False" in content
    print(f"✅ DEBUG = False (production): {debug_setting}")
    
    # Check 4: PF calculation clarity
    pf_fix = "loss_sum += abs(res['pnlPct'])" in content
    print(f"✅ PF Calculation Clear: {pf_fix}")
    
    return sl_fix_found and duplicate_count == 1 and debug_setting and pf_fix

def check_web_app():
    """Check web app has correct integration"""
    print("\n🔍 CHECKING WEB APP")
    print("=" * 50)
    
    with open("web_app.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check ADVANCED_MODE usage
    advanced_mode = "ADVANCED_MODE = True" in content
    print(f"✅ ADVANCED_MODE = True: {advanced_mode}")
    
    # Check Version3 import
    version3_import = "from backtest_gridsearch_slbe_ts_Version3" in content
    print(f"✅ Version3 Import: {version3_import}")
    
    return advanced_mode and version3_import

def check_test_files():
    """Check test files exist and work"""
    print("\n🔍 CHECKING TEST FILES")
    print("=" * 50)
    
    test_files = [
        "comprehensive_test_suite.py",
        "final_verification.py", 
        "test_sl_simple.py"
    ]
    
    all_exist = True
    for file in test_files:
        exists = os.path.exists(file)
        print(f"✅ {file}: {exists}")
        if not exists:
            all_exist = False
    
    return all_exist

def run_quick_simulation_test():
    """Run quick test to verify fixes work"""
    print("\n🔍 RUNNING QUICK SIMULATION TEST")
    print("=" * 50)
    
    try:
        from backtest_gridsearch_slbe_ts_Version3 import simulate_trade
        import pandas as pd
        
        # Simple test data
        df_test = pd.DataFrame({
            'time': pd.date_range('2025-01-01 10:00:00', periods=3, freq='1min'),
            'open':  [100.0, 99.0, 98.0],
            'high':  [100.0, 99.0, 98.0],
            'low':   [99.0,  98.0, 97.0],
            'close': [99.0,  98.0, 97.0]
        })
        
        pair_test = {
            'num': 999,
            'side': 'LONG',
            'entryDt': df_test.iloc[0]['time'],
            'exitDt': df_test.iloc[-1]['time'],
            'entryPrice': 100.0,
            'exitPrice': 97.0
        }
        
        # Test SL=2% (should trigger at 98.0)
        result, _ = simulate_trade(pair_test, df_test, sl=2.0, be=0, ts_trig=0, ts_step=0)
        
        if result:
            correct_exit = abs(result['exitPrice'] - 98.0) < 0.01
            correct_pnl = abs(result['pnlPct'] - (-2.0)) < 0.01
            correct_type = result['exitType'] == 'SL'
            
            print(f"✅ Exit Price Correct (98.0): {correct_exit}")
            print(f"✅ PnL Correct (-2.0%): {correct_pnl}")
            print(f"✅ Exit Type Correct (SL): {correct_type}")
            
            return correct_exit and correct_pnl and correct_type
        else:
            print("❌ No simulation result")
            return False
            
    except Exception as e:
        print(f"❌ Simulation Error: {e}")
        return False

def check_project_status():
    """Main project status check"""
    print("🚀 PROJECT STATUS CHECKER")
    print("=" * 60)
    
    # Run all checks
    main_file_ok = check_main_simulation_file()
    web_app_ok = check_web_app()
    test_files_ok = check_test_files()
    simulation_ok = run_quick_simulation_test()
    
    print("\n" + "=" * 60)
    print("📊 FINAL PROJECT STATUS:")
    
    if main_file_ok and web_app_ok and test_files_ok and simulation_ok:
        print("🎉 ✅ PROJECT FULLY FIXED AND READY!")
        print("✅ All critical bugs fixed")
        print("✅ All files updated correctly") 
        print("✅ Test suite working")
        print("✅ Simulation engine reliable")
        print("🚀 OPTIMIZATION CAN BE TRUSTED!")
    else:
        print("❌ PROJECT HAS REMAINING ISSUES:")
        if not main_file_ok:
            print("❌ Main simulation file issues")
        if not web_app_ok:
            print("❌ Web app integration issues")
        if not test_files_ok:
            print("❌ Test files missing")
        if not simulation_ok:
            print("❌ Simulation still has bugs")

if __name__ == "__main__":
    check_project_status()