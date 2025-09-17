#!/usr/bin/env python3
"""
Quick fix script for the trade_file issue in web_app.py
"""

# Read the file
with open('web_app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and fix the problematic lines
for i, line in enumerate(lines):
    if 'trade_content = trade_file.read()' in line and i > 2800:
        print(f'Found problematic line at {i+1}: {line.strip()}')
        
        # Replace the problematic section
        lines[i] = '        if not use_selected_data:\n'
        lines[i+1] = '            trade_content = trade_file.read().decode("utf-8")\n'
        lines[i+2] = '            candle_content = candle_file.read().decode("utf-8")\n'
        lines[i+3] = '            print(f"Files loaded: Trade={len(trade_content)} chars, Candle={len(candle_content)} chars")\n'
        lines[i+4] = '        else:\n'
        lines[i+5] = '            print("📊 Selected data mode - files already loaded above")\n'
        break

# Write back
with open('web_app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('✅ Fixed trade_file issue in web_app.py')