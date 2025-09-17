import json
import traceback
from web_backtest import backtest_gridsearch_slbe_ts_Version3 as bg

# Paths (relative to workspace)
path_trade = "60-tradelist-LONGSHORT.csv"
path_candle = "BINANCE_BTCUSDT, 60.csv"

print('Loading files...')
df_trade = bg.load_trade_csv(path_trade)
df_candle = bg.load_candle_csv(path_candle)

# limit trades for speed
trade_pairs, log_init = bg.get_trade_pairs(df_trade)
print(f'Found {len(trade_pairs)} pairs, using up to 20 for tests')
trade_pairs = trade_pairs[:20]

results_store = {}

try:
    # Test A: TS disabled (very small)
    sl_list = [1.0]
    be_list = [0.5]
    ts_trig_list = [0]
    ts_step_list = [0]
    print('\nRunning grid: TS disabled (small)')
    res_disabled = bg.grid_search_parallel(trade_pairs, df_candle, sl_list, be_list, ts_trig_list, ts_step_list, 'pnl')
    print('Top 3 (TS disabled):')
    for r in res_disabled[:3]:
        print(r['sl'], r['be'], r['ts_trig'], r['ts_step'], 'pnl=', r.get('pnl_total'))
    results_store['ts_disabled_top3'] = res_disabled[:3]

    # Test B: TS only (very small)
    sl_list = [0]
    be_list = [0]
    ts_trig_list = [1.0]
    ts_step_list = [0.1]
    print('\nRunning grid: TS only (small)')
    res_tsonly = bg.grid_search_parallel(trade_pairs, df_candle, sl_list, be_list, ts_trig_list, ts_step_list, 'pnl')
    print('Top 3 (TS only):')
    for r in res_tsonly[:3]:
        print(r['sl'], r['be'], r['ts_trig'], r['ts_step'], 'pnl=', r.get('pnl_total'))
    results_store['ts_only_top3'] = res_tsonly[:3]

except Exception as e:
    print('ERROR during tests:')
    traceback.print_exc()

with open('quick_test_results.json', 'w', encoding='utf-8') as f:
    json.dump(results_store, f, default=str, indent=2)

print('\nSaved quick_test_results.json')
