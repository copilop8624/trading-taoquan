# Sao lưu bản gốc trước khi refactor toàn diện simulate_trade và các logic liên quan
# Ngày: 2025-07-24
# Lưu ý: Đây là bản backup để có thể so sánh, phục hồi nếu cần.

import shutil
import datetime
import os

def backup_file(src_path):
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    dst_path = src_path.replace('.py', f'_backup_{now}.py')
    shutil.copy2(src_path, dst_path)
    print(f"Đã backup file {src_path} thành {dst_path}")

if __name__ == "__main__":
    backup_file('backtest_gridsearch_slbe_ts_Version3.py')
    backup_file('web_backtest/backtest_gridsearch_slbe_ts_Version3.py')
