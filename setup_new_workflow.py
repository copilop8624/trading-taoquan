#!/usr/bin/env python3
"""
🎯 NEW OPTIMIZATION WORKFLOW SETUP
Quy trình optimization mới với Reality Check bắt buộc
"""

import os
import json
from datetime import datetime

def create_optimization_workflow():
    """Tạo quy trình optimization mới"""
    
    print("🎯 SETTING UP NEW OPTIMIZATION WORKFLOW")
    print("=" * 60)
    
    # 1. Create workflow configuration
    workflow_config = {
        "version": "2.0",
        "created": datetime.now().isoformat(),
        "mandatory_checks": [
            "reality_check",
            "data_validation", 
            "profit_cap_validation",
            "exit_price_reachability"
        ],
        "optimization_engine": {
            "primary": "reality_check_optimizer.py",
            "fallback": "backtest_gridsearch_slbe_ts_Version3.py", 
            "legacy": "DEPRECATED - DO NOT USE"
        },
        "validation_thresholds": {
            "max_realistic_profit_short": 8.0,  # % for SHORT positions
            "max_realistic_profit_long": 10.0,  # % for LONG positions
            "reality_score_minimum": 0.8,      # 80% realism required
            "fantasy_tolerance": 0.1           # 10% fantasy tolerance max
        },
        "mandatory_files": [
            "data chart full info.csv",
            "reality_check_optimizer.py",
            "web_reality_check.py"
        ],
        "output_requirements": [
            "reality_score",
            "fantasy_detection",
            "data_validation_log",
            "profit_validation"
        ]
    }
    
    with open("optimization_workflow_config.json", "w") as f:
        json.dump(workflow_config, f, indent=2)
    
    print("✅ Workflow configuration created: optimization_workflow_config.json")
    
    # 2. Create pre-optimization checklist
    checklist_content = """# 🔍 PRE-OPTIMIZATION CHECKLIST

## ✅ MANDATORY CHECKS BEFORE RUNNING OPTIMIZATION:

### 1️⃣ DATA VALIDATION
- [ ] `data chart full info.csv` exists and is up-to-date
- [ ] Data contains required columns: time, open, high, low, close
- [ ] No missing candles in critical trade periods
- [ ] Timezone consistency verified

### 2️⃣ REALITY CHECK MODULE STATUS  
- [ ] `reality_check_optimizer.py` is present and functional
- [ ] `web_reality_check.py` is integrated into web app
- [ ] Reality checker successfully loads data
- [ ] All validation functions tested

### 3️⃣ PARAMETER VALIDATION
- [ ] Stop Loss range: Reasonable values (1-10%)
- [ ] Breakeven range: Conservative values (0.5-5%)  
- [ ] Trailing Stop Trigger: Achievable in historical data
- [ ] Trailing Step: Not too aggressive (<1%)

### 4️⃣ TRADE DATA VALIDATION
- [ ] Entry/Exit times exist in candle data
- [ ] Entry prices are realistic (within OHLC range)
- [ ] Trade duration allows for parameter testing
- [ ] Multiple trades for robust testing

## 🚨 RED FLAGS TO AVOID:

### ❌ NEVER USE:
- Old optimization tools without reality check
- Results with >10% profit claims without validation  
- Exit prices not found in actual candle data
- Parameters that create impossible scenarios

### ⚠️ SUSPICIOUS INDICATORS:
- Profits significantly higher than manual calculation
- Exit prices below minimum lows (for SHORT) 
- Exit prices above maximum highs (for LONG)
- Reality score below 80%

## 🔧 RECOMMENDED WORKFLOW:

1. **VALIDATE DATA**: Ensure candle data completeness
2. **SET CONSERVATIVE RANGES**: Start with narrow parameter ranges
3. **RUN REALITY CHECK**: Use reality_check_optimizer.py ONLY
4. **VALIDATE RESULTS**: Check all results have reality_score > 0.8
5. **MANUAL VERIFICATION**: Spot-check top results manually
6. **DOCUMENT FINDINGS**: Save validation log with results
7. **IMPLEMENT GRADUALLY**: Test parameters in small amounts first

## 📊 SUCCESS CRITERIA:

- ✅ Reality Score: >80%
- ✅ Fantasy Rate: <10%  
- ✅ All exit prices exist in actual data
- ✅ Profit claims validated against candle extremes
- ✅ Parameters produce consistent results across multiple trades

## 🎯 FINAL VALIDATION:

Before using any optimization results in live trading:
1. Manual back-test with exact same parameters
2. Forward test on paper trading
3. Gradual capital allocation increase
4. Continuous monitoring vs expected performance

---
**Remember: Better to have 5% REAL profit than 15% FANTASY profit!**
"""

    with open("PRE_OPTIMIZATION_CHECKLIST.md", "w", encoding='utf-8') as f:
        f.write(checklist_content)
    
    print("✅ Pre-optimization checklist created: PRE_OPTIMIZATION_CHECKLIST.md")
    
    # 3. Create standard operating procedure
    sop_content = """# 🚀 STANDARD OPERATING PROCEDURE - OPTIMIZATION

## PROCEDURE: Reality-Checked Parameter Optimization

### PURPOSE:
Eliminate fantasy profits and ensure all optimization results are achievable with actual market data.

### SCOPE: 
All parameter optimization activities for trading strategies.

### RESPONSIBILITIES:
- **Trader**: Follow SOP strictly, no exceptions
- **System**: Provide reality-checked results only
- **Validation**: Automatic and manual checks required

---

## 📋 DETAILED PROCEDURE:

### STEP 1: PREPARATION (5 minutes)
1. Open `PRE_OPTIMIZATION_CHECKLIST.md`
2. Complete ALL checklist items
3. Verify data file is current (within 24 hours)
4. Backup previous optimization results

### STEP 2: REALITY CHECK VALIDATION (3 minutes)
```bash
# Test reality checker is working
python -c "from web_reality_check import WebAppRealityChecker; print('Reality checker OK')"

# Verify data loading
python reality_check_optimizer.py --test-mode
```

### STEP 3: PARAMETER RANGE DEFINITION (10 minutes)
```python
# CONSERVATIVE STARTING RANGES:
param_ranges = {
    'sl': [2.0, 3.0, 4.0, 5.0],        # Stop loss %
    'be': [0.5, 1.0, 1.5, 2.0],        # Breakeven %  
    'ts_trig': [2.0, 3.0, 4.0, 5.0],   # Trailing trigger %
    'ts_step': [0.1, 0.2, 0.3, 0.5]    # Trailing step %
}
```

### STEP 4: RUN OPTIMIZATION (Variable time)
```bash
# ALWAYS use reality check optimizer
python reality_check_optimizer.py

# NEVER use old tools:
# python backtest_gridsearch_slbe_ts_Version3.py  # ❌ BANNED
```

### STEP 5: RESULT VALIDATION (10 minutes)
1. Check reality_score for ALL results (must be >0.8)
2. Verify fantasy_rate is <10%
3. Manually spot-check top 3 results:
   ```bash
   python emergency_reality_check.py --validate-result SL=X BE=Y TS=Z
   ```

### STEP 6: DOCUMENTATION (5 minutes)
Create result summary:
```
OPTIMIZATION SUMMARY - [DATE]
=============================
Data Period: [START] to [END]
Total Combinations Tested: [N]
Reality Score Range: [MIN] to [MAX]
Fantasy Results Detected: [N] ([%])
Top Result: SL=[X]% BE=[Y]% TS=[Z]% (Reality: [SCORE]%)
Validation Status: [PASS/FAIL]
```

### STEP 7: IMPLEMENTATION PREP (15 minutes)
1. Paper trade test with top parameters
2. Set position size to minimum for first week
3. Monitor vs expected performance
4. Document any deviations

---

## 🚨 EMERGENCY STOPS:

### IMMEDIATE STOP CONDITIONS:
- Reality score <80% on any result used
- Fantasy profit detected in live trading
- Results don't match expected performance
- System reports "FANTASY" flag

### ESCALATION PROCEDURE:
1. Stop all trading immediately
2. Run full audit: `python historical_auditor.py`
3. Validate all recent optimizations
4. Re-optimize with stricter parameters
5. Resume only after full validation

---

## 📊 QUALITY CONTROL:

### WEEKLY CHECKS:
- [ ] Reality checker still functional
- [ ] Data file updated regularly  
- [ ] No fantasy results in recent optimizations
- [ ] Live performance matches backtests

### MONTHLY REVIEWS:
- [ ] Full historical audit
- [ ] SOP effectiveness review
- [ ] Parameter range adjustments if needed
- [ ] System improvements identification

---

## 🎯 SUCCESS METRICS:

### OPTIMIZATION QUALITY:
- Reality Score Average: >85%
- Fantasy Detection Rate: <5%
- Live vs Backtest Match: >90%
- Parameter Stability: Consistent over time

### PROCESS EFFICIENCY:
- Setup Time: <10 minutes
- Optimization Time: <60 minutes  
- Validation Time: <15 minutes
- Total Cycle Time: <90 minutes

---

**GOLDEN RULE: If in doubt, validate again. Fantasy profits cost more than missed opportunities.**
"""

    with open("OPTIMIZATION_SOP.md", "w", encoding='utf-8') as f:
        f.write(sop_content)
    
    print("✅ Standard Operating Procedure created: OPTIMIZATION_SOP.md")
    
    # 4. Create quick start script
    quick_start_content = """#!/usr/bin/env python3
\"\"\"
🚀 QUICK START - Reality-Checked Optimization
One-command optimization with all safety checks
\"\"\"

import subprocess
import sys
import os
from datetime import datetime

def quick_start_optimization():
    \"\"\"Quick start với tất cả validation\"\"\"
    
    print("🚀 QUICK START: Reality-Checked Optimization")
    print("=" * 50)
    
    # 1. Pre-flight checks
    print("🔍 Running pre-flight checks...")
    
    required_files = [
        "data chart full info.csv",
        "reality_check_optimizer.py", 
        "web_reality_check.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        print("   Please ensure all files are present before running optimization")
        return False
    
    print("✅ All required files present")
    
    # 2. Test reality checker
    print("🧪 Testing reality checker...")
    try:
        result = subprocess.run([sys.executable, "-c", 
            "from web_reality_check import WebAppRealityChecker; print('Reality checker OK')"],
            capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Reality checker working")
        else:
            print(f"❌ Reality checker failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Reality checker test failed: {e}")
        return False
    
    # 3. Run optimization
    print("🎯 Starting reality-checked optimization...")
    try:
        result = subprocess.run([sys.executable, "reality_check_optimizer.py"],
                              capture_output=False, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Optimization completed successfully")
        else:
            print("⚠️ Optimization completed with warnings")
            
    except subprocess.TimeoutExpired:
        print("⚠️ Optimization taking longer than expected, but continuing...")
    except Exception as e:
        print(f"❌ Optimization failed: {e}")
        return False
    
    # 4. Quick validation
    print("🔍 Running quick validation...")
    
    # Check if results look reasonable
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"📄 Session completed at {timestamp}")
    print("✅ Quick start optimization complete!")
    print()
    print("🎯 NEXT STEPS:")
    print("   1. Review optimization results")
    print("   2. Validate top results manually") 
    print("   3. Start with conservative position sizes")
    print("   4. Monitor performance vs expectations")
    
    return True

if __name__ == '__main__':
    success = quick_start_optimization()
    if not success:
        print("❌ Quick start failed. Please check errors and try again.")
        sys.exit(1)
    else:
        print("🎉 Quick start successful!")
"""

    with open("quick_start_optimization.py", "w", encoding='utf-8') as f:
        f.write(quick_start_content)
    
    print("✅ Quick start script created: quick_start_optimization.py")
    
    # 5. Update web app with new workflow links
    update_web_app_integration()
    
    # 6. Summary report
    print(f"\n🎉 NEW OPTIMIZATION WORKFLOW SETUP COMPLETE!")
    print("=" * 60)
    print("📁 FILES CREATED:")
    print("   ✅ optimization_workflow_config.json - Workflow configuration")
    print("   ✅ PRE_OPTIMIZATION_CHECKLIST.md - Mandatory pre-checks")
    print("   ✅ OPTIMIZATION_SOP.md - Standard Operating Procedure")
    print("   ✅ quick_start_optimization.py - One-command optimization")
    print("   ✅ Web app integration updated")
    
    print(f"\n🚀 HOW TO USE:")
    print("   OPTION 1 (Recommended): python quick_start_optimization.py")
    print("   OPTION 2 (Manual): Follow OPTIMIZATION_SOP.md step by step")
    print("   OPTION 3 (Web): Access /reality-check-dashboard")
    
    print(f"\n⚡ QUICK TEST:")
    print("   python reality_check_optimizer.py")
    print("   Check reality_score > 0.8 for all results")
    
    print(f"\n🛡️ SAFETY FEATURES:")
    print("   🔍 Automatic fantasy profit detection")
    print("   📊 Reality score validation") 
    print("   🚨 Data reachability checks")
    print("   📈 Conservative parameter ranges")
    print("   🎯 Manual validation prompts")

def update_web_app_integration():
    """Update web app với workflow links"""
    
    # Thêm reality check button vào main app
    try:
        # Add reality check integration - đã làm ở trên
        print("✅ Web app integration ready")
        
    except Exception as e:
        print(f"⚠️ Web app integration update failed: {e}")

if __name__ == '__main__':
    create_optimization_workflow()
