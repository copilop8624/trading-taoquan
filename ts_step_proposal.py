#!/usr/bin/env python3
"""
Proposal: Dynamic TS step minimums based on asset type
"""

def propose_dynamic_ts_minimums():
    """Propose more realistic TS step minimums"""
    
    print("🔧 PROPOSAL: Dynamic TS Step Minimums")
    print()
    
    asset_profiles = {
        "Conservative (BTC/ETH stable)": {
            "typical_pullback": "2-3%",
            "recommended_ts_min": "3-4%",
            "reasoning": "Normal conditions, tighter control OK"
        },
        "Moderate (BTC/ETH normal)": {
            "typical_pullback": "3-5%", 
            "recommended_ts_min": "5-6%",
            "reasoning": "Current setting, good balance"
        },
        "Aggressive (Altcoins/Volatile)": {
            "typical_pullback": "5-8%",
            "recommended_ts_min": "8-10%", 
            "reasoning": "High vol needs wider stops"
        },
        "Extreme (Pump/Dump scenarios)": {
            "typical_pullback": "8-15%",
            "recommended_ts_min": "12-15%",
            "reasoning": "Extreme moves need extreme stops"
        }
    }
    
    print("📊 PROPOSED TS MINIMUMS BY SCENARIO:")
    print(f"{'Scenario':<30} {'Pullback':<12} {'TS Min':<10} {'Reasoning'}")
    print("=" * 80)
    
    for scenario, data in asset_profiles.items():
        print(f"{scenario:<30} {data['typical_pullback']:<12} {data['recommended_ts_min']:<10} {data['reasoning']}")
    
    print()
    print("🎯 CURRENT VS PROPOSED:")
    print("   Current fixed minimum: 5%")
    print("   Proposed options:")
    print("   • Option 1: Keep 5% (good for most cases)")
    print("   • Option 2: Lower to 3% (more flexible, but risky)")
    print("   • Option 3: Dynamic UI (user selects asset type)")
    
    print()
    print("💡 RECOMMENDATION:")
    print("   Keep TS step minimum = 3-4%")
    print("   Reasons:")
    print("   ✅ More flexible than 5%")
    print("   ✅ Still prevents 0.5% disasters") 
    print("   ✅ Experienced users can go tighter")
    print("   ✅ Beginners protected from <3% mistakes")
    
    print()
    print("⚖️ RISK/REWARD BALANCE:")
    print("   3% minimum: 80% cases OK, 20% might be tight")
    print("   5% minimum: 95% cases OK, 5% might be loose")
    print("   → 3% gives more flexibility with acceptable risk")

if __name__ == "__main__":
    propose_dynamic_ts_minimums()