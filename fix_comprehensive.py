#!/usr/bin/env python3
"""
Comprehensive fix for the optimization flow issue
"""

# Read the file
with open('web_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the section that needs fixing - after the trade_content line we just fixed
# We need to handle the try/except block that follows
old_section = """        try:
            df_trade = load_trade_csv_from_content(trade_content)
            df_candle = load_candle_csv_from_content(candle_content)
            print("Using content-based loading (safer)")"""

new_section = """        if not use_selected_data:
            # Upload mode - load from content
            try:
                df_trade = load_trade_csv_from_content(trade_content)
                df_candle = load_candle_csv_from_content(candle_content)
                print("Using content-based loading (safer)")"""

# Apply the fix
if old_section in content:
    content = content.replace(old_section, new_section)
    print("✅ Fixed the df_trade loading logic")
else:
    print("❌ Could not find the section to fix")

# Write back
with open('web_app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Applied comprehensive fix for optimization flow')