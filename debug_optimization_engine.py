#!/usr/bin/env python3
"""
🔍 DEBUG: Kiểm tra giá trị optimization_engine được gửi từ frontend
"""

# Thêm debug code vào optimize_ranges để xem request data
debug_code = """
        # 🔍 DEBUG: Print raw request data to see what frontend sends
        print("🔍 RAW REQUEST DATA:")
        print(f"   Full data: {data}")
        print(f"   optimization_engine value: '{data.get('optimization_engine')}' (type: {type(data.get('optimization_engine'))})")
        print(f"   Available keys: {list(data.keys())}")
        
        # Get optimization engine and criteria
        optimization_engine = data.get('optimization_engine', 'optuna')
        optimization_criteria = data.get('optimization_criteria', 'pnl')
        selected_params = data.get('selected_params', ['sl'])  # Default to SL only
        
        print(f"🧠 Selected Optimization Engine: {optimization_engine}")
        print(f"🎯 Selected Optimization Criteria: {optimization_criteria}")
        print(f"⚙️ Selected Parameters: {selected_params}")
"""

print("Để debug vấn đề này, bạn cần:")
print("1. Thêm debug code vào optimize_ranges() để xem request data")
print("2. Kiểm tra frontend có gửi đúng field 'optimization_engine' không")
print("3. Verify giá trị gửi có phải là 'grid_search' hay 'gridsearch' hay gì khác")
print()
print("Debug code để thêm vào web_app.py (sau line 3682):")
print(debug_code)
print()
print("Hoặc bạn có thể:")
print("- Kiểm tra Network tab trong browser để xem request payload")
print("- Hoặc start server và test với Grid Search để xem console logs")