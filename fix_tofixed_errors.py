#!/usr/bin/env python3
"""
Fix all .toFixed() calls in HTML templates to use safeToFixed() instead
"""

import re
import os

def fix_tofixed_in_file(filepath):
    """Fix .toFixed() calls in a file"""
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern to match .toFixed() calls but NOT in safeToFixed function definition
    # Exclude lines that contain "function safeToFixed" or "return Number(value).toFixed"
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Skip if this is the safeToFixed function definition
        if 'function safeToFixed' in line or 'return Number(value).toFixed' in line or 'originalToFixed' in line:
            fixed_lines.append(line)
            continue
            
        # Replace .toFixed() with safeToFixed() 
        # Pattern: (something).toFixed(digits)
        pattern = r'(\([^)]+\)|[a-zA-Z_][a-zA-Z0-9_\.]*)\s*\.toFixed\s*\(\s*(\d+)\s*\)'
        
        def replace_tofixed(match):
            expression = match.group(1)
            digits = match.group(2)
            # Remove outer parentheses if they exist
            if expression.startswith('(') and expression.endswith(')'):
                expression = expression[1:-1]
            return f'safeToFixed({expression}, {digits})'
        
        new_line = re.sub(pattern, replace_tofixed, line)
        fixed_lines.append(new_line)
    
    new_content = '\n'.join(fixed_lines)
    
    if new_content != original_content:
        # Backup original
        backup_path = filepath + '.backup_before_tofixed_fix'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"📝 Backup created: {backup_path}")
        
        # Write fixed content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # Count changes
        changes = len(re.findall(r'\.toFixed\s*\(', original_content)) - len(re.findall(r'\.toFixed\s*\(', new_content))
        print(f"✅ Fixed {changes} .toFixed() calls in {filepath}")
        return True
    else:
        print(f"ℹ️ No .toFixed() calls to fix in {filepath}")
        return False

if __name__ == "__main__":
    # Fix templates
    template_files = [
        "templates/index.html",
        "templates/results.html", 
        "templates/strategy_management.html",
        "templates/reality_check_dashboard.html"
    ]
    
    total_fixes = 0
    for template_file in template_files:
        if fix_tofixed_in_file(template_file):
            total_fixes += 1
    
    print(f"\n🎉 Fixed .toFixed() issues in {total_fixes} files!")
    print("✅ All templates should now use safeToFixed() instead of direct .toFixed() calls")