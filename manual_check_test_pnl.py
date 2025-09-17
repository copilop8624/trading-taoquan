import pandas as pd
from datetime import datetime
import concurrent.futures

# Thông số tối ưu
SL = 4.5
BE = 1.0
TS_TRIG = 1.0
TS_STEP = 0.0

# Lệnh test
trades = [
    {'num': 1386, 'side': 'LONG', 'entryDt': '2023-06-20 14:00', 'exitDt': None, 'entryPrice': 13.68, 'exitPrice': 13.40},
    {'num': 1363, 'side': 'SHORT', 'entryDt': '2023-06-04 15:00', 'exitDt': None, 'entryPrice': 15.98, 'exitPrice': 14.82},
]

def normalize_time(s):
    # Chuyển về datetime chuẩn
    return pd.to_datetime(s, format='%Y-%m-%d %H:%M', errors='coerce') if '-' in s else pd.to_datetime(s, format='%m/%d %H:%M', errors='coerce').replace(year=2023)

# Load data candle
candle = pd.read_csv('c:/Users/aio/OneDrive/Desktop/DATA TRADINGVIEW/EGLDUSDT/BINANCE_EGLDUSDT.P, 60.csv')
candle['time'] = pd.to_datetime(candle['time'])

# Chuẩn hóa entry/exit time
for t in trades:
    t['entryDt'] = normalize_time(t['entryDt'])
    # Tìm exitDt gần nhất sau entry (nếu chưa có)
    if not t['exitDt']:
        idx = candle[candle['time'] >= t['entryDt']].index
        if len(idx) > 0:
            t['exitDt'] = candle.loc[idx[-1], 'time']

# Hàm mô phỏng lại từng lệnh
from backtest_gridsearch_slbe_ts_Version3 import simulate_trade

from optimization_log_manager import OptimizationLogManager

log_mgr = OptimizationLogManager()

# Chạy mô phỏng từng lệnh song song để tăng tốc
results = []
with concurrent.futures.ThreadPoolExecutor() as executor:
    future_to_trade = {executor.submit(simulate_trade, t, candle, SL, BE, TS_TRIG, TS_STEP): t for t in trades}
    for future in concurrent.futures.as_completed(future_to_trade):
        t = future_to_trade[future]
        try:
            res, log = future.result()
            results.append((t, res, log))
        except Exception as exc:
            print(f"Trade #{t['num']} generated an exception: {exc}")

# Đảm bảo kết quả theo đúng thứ tự trades gốc
results_sorted = sorted(results, key=lambda x: trades.index(x[0]))
for t, res, log in results_sorted:
    print(f"Trade #{t['num']} {t['side']} entry {t['entryDt']} price {t['entryPrice']}")
    print(f"  Exit: {res['exitDt']} price {res['exitPrice']} | PnL: {res['pnlPct']:.2f}% | Type: {res['exitType']}")
    print('---')
    for l in log:
        print(l)
    print('===========================')
    # Ghi log kết quả từng lệnh
    param_ranges = {
        'sl_min': SL, 'sl_max': SL,
        'be_min': BE, 'be_max': BE,
        'ts_trig_min': TS_TRIG, 'ts_trig_max': TS_TRIG,
        'ts_step_min': TS_STEP, 'ts_step_max': TS_STEP
    }
    best_result = {
        'params': {'sl': SL, 'be': BE, 'ts_trig': TS_TRIG, 'ts_step': TS_STEP},
        'pnl': res['pnlPct'],
        'winrate': None,
        'pf': None
    }
    log_mgr.log_optimization(
        user='manual',
        project='EGLDUSDT_H1_manual_test',
        symbol='EGLDUSDT',
        timeframe='H1',
        param_ranges=param_ranges,
        best_result=best_result,
        notes=f"Trade #{t['num']} {t['side']} entry {t['entryDt']}"
    )
