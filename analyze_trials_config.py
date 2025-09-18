#!/usr/bin/env python3
"""
PHÂN TÍCH: Vấn đề cấu hình n_trials trong Optuna
"""

def analyze_trials_config():
    """Phân tích tất cả nơi config n_trials trong codebase"""
    
    print("🔍 PHÂN TÍCH: Cấu hình n_trials trong Optuna")
    print("=" * 60)
    print()
    
    print("📊 CÁC NƠI XUẤT HIỆN n_trials:")
    print()
    
    configs = [
        {
            "location": "web_app.py:1961 - optuna_search function",
            "value": "n_trials=50",
            "type": "Function default parameter",
            "usage": "Default value cho function definition"
        },
        {
            "location": "web_app.py:2062 - grid_search_sl_fallback",
            "value": "n_trials=50", 
            "type": "Hard-coded call",
            "usage": "Gọi optuna_search với 50 trials fixed"
        },
        {
            "location": "web_app.py:3999 - optimize_ranges route",
            "value": "n_trials=100",
            "type": "Hard-coded call", 
            "usage": "Gọi optuna_search với 100 trials (comment: faster testing)"
        },
        {
            "location": "templates/index.html:538 - Max Iterations input",
            "value": "value='100' min='10' max='500'",
            "type": "Frontend form field",
            "usage": "User có thể nhập 10-500, default 100"
        },
        {
            "location": "templates/index.html:1786 - JavaScript",
            "value": "params.max_iterations = ...",
            "type": "Frontend data collection",
            "usage": "Gửi max_iterations từ form tới backend"
        }
    ]
    
    print(f"{'Location':<40} {'Value':<15} {'Type':<20} {'Status'}")
    print("-" * 95)
    
    for config in configs:
        status = "🔗 CONNECTED" if "frontend" in config["type"].lower() else "❌ ISOLATED"
        if "optimize_ranges" in config["location"]:
            status = "⚠️ MIXED"
        elif "function" in config["type"].lower():
            status = "🔧 TEMPLATE"
        
        print(f"{config['location'][:39]:<40} {config['value'][:14]:<15} {config['type'][:19]:<20} {status}")
    
    print()
    print("🚨 VẤN ĐỀ PHÁT HIỆN:")
    print()
    
    problems = [
        {
            "issue": "Frontend → Backend GAP",
            "detail": "Frontend gửi 'max_iterations' nhưng backend KHÔNG nhận",
            "impact": "User setting bị ignore, backend dùng hard-coded values",
            "severity": "🔴 HIGH"
        },
        {
            "issue": "Multiple Hard-coded Values",
            "detail": "Code có 50, 100 trials ở các nơi khác nhau",
            "impact": "Inconsistent behavior, khó maintain",
            "severity": "🟡 MEDIUM"
        },
        {
            "issue": "No Central Configuration",
            "detail": "Không có 1 nơi duy nhất để config trials",
            "impact": "Phải sửa nhiều nơi khi thay đổi",
            "severity": "🟡 MEDIUM"
        }
    ]
    
    for problem in problems:
        print(f"{problem['severity']} {problem['issue']}")
        print(f"   📝 Chi tiết: {problem['detail']}")
        print(f"   💥 Tác động: {problem['impact']}")
        print()
    
    print("🎯 HIỆN TRẠNG THỰC TẾ:")
    print()
    print("   ❌ Frontend 'Max Iterations' = KHÔNG HOẠT ĐỘNG")
    print("   ⚠️ Route /optimize_ranges = 100 trials (hard-coded)")
    print("   ⚠️ Route /optimize fallback = 50 trials (hard-coded)")
    print("   🔧 Function default = 50 trials (template only)")
    print()
    
    print("✅ GIẢI PHÁP ĐỀ XUẤT:")
    print()
    print("1. 🔗 KẾT NỐI FRONTEND → BACKEND:")
    print("   • Backend nhận 'max_iterations' từ request")
    print("   • Truyền vào optuna_search function")
    print()
    print("2. 🏗️ CENTRALIZED CONFIG:")
    print("   • Tạo DEFAULT_OPTUNA_TRIALS = 100")
    print("   • Tất cả calls dùng chung config này")
    print()
    print("3. 📊 VALIDATION:")
    print("   • Validate 10 ≤ max_iterations ≤ 500")
    print("   • Fallback về default nếu invalid")
    print()
    
    print("🔧 CODE CHANGES NEEDED:")
    print()
    print("   web_app.py:")
    print("     • Thêm DEFAULT_OPTUNA_TRIALS = 100")
    print("     • Route /optimize_ranges: nhận max_iterations") 
    print("     • Route /optimize: nhận max_iterations")
    print("     • Tất cả optuna_search calls: dùng user input")
    print()
    print("   templates/index.html:")
    print("     • ✅ Đã có frontend form (hoạt động)")
    print("     • ✅ Đã gửi max_iterations (hoạt động)")
    print()
    
    print("⚡ PRIORITY: HIGH")
    print("   User setting bị ignore = Bad UX!")

if __name__ == "__main__":
    analyze_trials_config()