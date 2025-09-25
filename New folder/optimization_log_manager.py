import os
import pandas as pd
from datetime import datetime

class OptimizationLogManager:
    """
    Module quản lý log kết quả tối ưu hóa, lưu trữ theo mã, khung thời gian, tên user/project, timestamp.
    Không ảnh hưởng tới các module tool hiện tại.
    """
    def __init__(self, log_path='optimization_logs.csv'):
        self.log_path = log_path
        if not os.path.exists(self.log_path):
            # Tạo file log nếu chưa có
            pd.DataFrame(columns=[
                'timestamp', 'user', 'project', 'symbol', 'timeframe',
                'sl_min', 'sl_max', 'be_min', 'be_max', 'ts_trig_min', 'ts_trig_max', 'ts_step_min', 'ts_step_max',
                'best_params', 'best_pnl', 'best_winrate', 'best_pf', 'notes'
            ]).to_csv(self.log_path, index=False)

    def log_optimization(self, user, project, symbol, timeframe, param_ranges, best_result, notes=None):
        # Ghi log 1 lần tối ưu
        entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': user,
            'project': project,
            'symbol': symbol,
            'timeframe': timeframe,
            'sl_min': param_ranges.get('sl_min'),
            'sl_max': param_ranges.get('sl_max'),
            'be_min': param_ranges.get('be_min'),
            'be_max': param_ranges.get('be_max'),
            'ts_trig_min': param_ranges.get('ts_trig_min'),
            'ts_trig_max': param_ranges.get('ts_trig_max'),
            'ts_step_min': param_ranges.get('ts_step_min'),
            'ts_step_max': param_ranges.get('ts_step_max'),
            'best_params': str(best_result.get('params')),
            'best_pnl': best_result.get('pnl'),
            'best_winrate': best_result.get('winrate'),
            'best_pf': best_result.get('pf'),
            'notes': notes or ''
        }
        df = pd.read_csv(self.log_path)
        df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
        df.to_csv(self.log_path, index=False)

    def get_logs(self, symbol=None, timeframe=None, user=None, project=None):
        # Truy vấn log theo các tiêu chí
        df = pd.read_csv(self.log_path)
        if symbol:
            df = df[df['symbol'] == symbol]
        if timeframe:
            df = df[df['timeframe'] == timeframe]
        if user:
            df = df[df['user'] == user]
        if project:
            df = df[df['project'] == project]
        return df

    def get_projects(self):
        df = pd.read_csv(self.log_path)
        return df['project'].unique().tolist()

    def get_symbols(self):
        df = pd.read_csv(self.log_path)
        return df['symbol'].unique().tolist()

    def get_timeframes(self):
        df = pd.read_csv(self.log_path)
        return df['timeframe'].unique().tolist()

# Checklist:
# - Không ảnh hưởng tới tool đang dùng
# - Log đầy đủ thông tin tối ưu
# - Cho phép user đặt tên, quản lý, truy vấn, xuất dữ liệu
# - Dễ tích hợp vào workflow web/app hoặc script
# - Tự động tạo file log nếu chưa có
# - Không ghi đè dữ liệu cũ
# - Đảm bảo an toàn dữ liệu
