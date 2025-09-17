import pandas as pd
import numpy as np
from tqdm import tqdm
import backtest_gridsearch_slbe_ts_Version3 as core

def run_backtest(trade_path, candle_path,
                 sl_min, sl_max, sl_step,
                 be_min, be_max, be_step,
                 ts_trig_min, ts_trig_max, ts_trig_step,
                 ts_step_min, ts_step_max, ts_step_step,
                 n_trades, opt_type):
    # Load dữ liệu
    df_trade = core.load_trade_csv(trade_path)
    df_candle = core.load_candle_csv(candle_path)
    # Lọc theo số lượng lệnh khảo sát
    min_candle = df_candle['time'].min()
    max_candle = df_candle['time'].max()
    df_trade = df_trade[(df_trade['date'] >= min_candle) & (df_trade['date'] <= max_candle)]
    if n_trades > 0:
        trade_order = df_trade.sort_values('date', ascending=False)['trade'].unique()[:n_trades]
        df_trade = df_trade[df_trade['trade'].isin(trade_order)]
    trade_pairs, log_init = core.get_trade_pairs(df_trade)
    # Sinh list giá trị
    sl_list = list(np.arange(sl_min, sl_max + sl_step/2, sl_step))
    be_list = list(np.arange(be_min, be_max + be_step/2, be_step))
    ts_trig_list = list(np.arange(ts_trig_min, ts_trig_max + ts_trig_step/2, ts_trig_step))
    ts_step_list = list(np.arange(ts_step_min, ts_step_max + ts_step_step/2, ts_step_step))
    # Chạy grid search
    results = core.grid_search_parallel(trade_pairs, df_candle, sl_list, be_list, ts_trig_list, ts_step_list, opt_type)
    # Lấy top 5 kết quả
    top_results = results[:5]
    # Chuẩn bị dữ liệu vẽ biểu đồ
    chart_data = {
        'labels': [f"SL={r['sl']},BE={r['be']},TS={r['ts_trig']},{r['ts_step']}" for r in top_results],
        'pnl': [r['pnl_total'] for r in top_results],
        'winrate': [r['winrate'] for r in top_results],
        'pf': [r['pf'] for r in top_results],
    }
    # Log chi tiết lệnh top 1
    log = top_results[0]['log']
    return top_results, log, chart_data
