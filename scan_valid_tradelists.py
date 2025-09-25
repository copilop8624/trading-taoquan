import os
import csv

tradelist_dir = 'tradelist'
tradelist_files = []
for fname in os.listdir(tradelist_dir):
    fpath = os.path.join(tradelist_dir, fname)
    if not os.path.isfile(fpath):
        continue
    # Check if file is a valid CSV (not pointer)
    with open(fpath, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        if 'Trade #' in first_line or 'Trade' in first_line:
            tradelist_files.append(fname)

print('Valid tradelist files for import:')
for f in tradelist_files:
    print(f)
if not tradelist_files:
    print('No valid tradelist files found.')
