#!/usr/bin/env python3
"""
Fix the syntax error in the try/except block
"""

# Read the file
with open('web_app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and fix the syntax error - move except block inside the if
for i, line in enumerate(lines):
    if 'if not use_selected_data:' in line and i > 2820:
        print(f'Found conditional at line {i+1}: {line.strip()}')
        # Fix the indentation of except block
        for j in range(i+1, min(i+20, len(lines))):
            if 'except Exception as content_error:' in lines[j]:
                print(f'Found except at line {j+1}, fixing indentation')
                # Add proper indentation to except and following lines
                while j < len(lines) and (lines[j].startswith('        except') or lines[j].startswith('            ') or lines[j].strip() == ''):
                    if lines[j].startswith('        except'):
                        lines[j] = '            except' + lines[j][15:]
                    elif lines[j].startswith('            ') and lines[j].strip():
                        lines[j] = '    ' + lines[j]
                    j += 1
                    if lines[j-1].strip() == '' and not lines[j].startswith('    '):
                        break
                break
        break

# Write back
with open('web_app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('✅ Fixed syntax error in try/except block')