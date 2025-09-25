import os
import shutil

tradelist_dir = 'tradelist'

# Detect pointer files (those with '...existing data from' in first line)
def is_pointer_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            second_line = f.readline()
            if '...existing data from' in first_line or '...existing data from' in second_line:
                return True
    except Exception:
        return False
    return False

def get_pointer_target(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if '...existing data from' in line:
                # Extract target filename
                parts = line.strip().split('from')
                if len(parts) > 1:
                    target = parts[1].replace('...', '').replace('csv', 'csv').replace('CSV', 'csv').strip()
                    target = target.replace(' ', '').replace('(', '').replace(')', '')
                    return target
    return None

removed = []
copied = []
for fname in os.listdir(tradelist_dir):
    fpath = os.path.join(tradelist_dir, fname)
    if not os.path.isfile(fpath):
        continue
    if is_pointer_file(fpath):
        target = get_pointer_target(fpath)
        if target:
            target_path = os.path.join(tradelist_dir, target)
            if os.path.exists(target_path):
                shutil.copyfile(target_path, fpath)
                copied.append(fname)
            else:
                os.remove(fpath)
                removed.append(fname)
        else:
            os.remove(fpath)
            removed.append(fname)

print(f"Pointer files replaced: {copied}")
print(f"Pointer files deleted: {removed}")
