import json
import os
import numpy as np
from web_backtest.backtest_gridsearch_slbe_ts_Version3 import load_trade_csv, load_candle_csv, get_trade_pairs, simulate_trade

OUT_DIR = 'output_demo'
RANGE_PATH = os.path.join(OUT_DIR, 'range_analysis.json')
if not os.path.exists(RANGE_PATH):
    raise SystemExit('Missing range_analysis.json')
with open(RANGE_PATH, 'r', encoding='utf-8') as f:
    r = json.load(f)

bal_sl = r['recommended_ranges']['sl_ranges']['balanced']
bal_be = r['recommended_ranges']['be_ranges']['balanced']
bal_ts = r['recommended_ranges']['ts_ranges']['balanced']
bal_ts_step = r['recommended_ranges']['ts_step_ranges']['balanced']

def make_list(cfg, max_points=4):
    vals = list(np.arange(cfg['min'], cfg['max'] + cfg['step']/2, cfg['step']))
    if len(vals) > max_points:
        idx = np.linspace(0, len(vals)-1, max_points).astype(int)
        vals = [vals[i] for i in idx]
    return vals

sl_list = make_list(bal_sl, max_points=3)
be_list = make_list(bal_be, max_points=3)
ts_list = make_list(bal_ts, max_points=3)
ts_step_list = make_list(bal_ts_step, max_points=2)

print('SL:', sl_list)
print('BE:', be_list)
print('TS:', ts_list)
print('TS step:', ts_step_list)

# Choose one symbol from previous demo results to keep run fast
TRADE_FILE = '60-tradelist-LONGSHORT.csv'
CANDLE_FILE = 'BINANCE_BTCUSDT, 60.csv'
if not os.path.exists(TRADE_FILE) or not os.path.exists(CANDLE_FILE):
    TRADE_FILE = 'sample_tradelist.csv'
    cand_choices = [p for p in os.listdir('.') if p.lower().endswith('.csv') and 'binance' in p.lower() and 'btc' in p.lower()]
    CANDLE_FILE = cand_choices[0] if cand_choices else None
    if CANDLE_FILE is None:
        raise SystemExit('No candle CSV found in repo')

print('Using:', TRADE_FILE, CANDLE_FILE)

df_trade = load_trade_csv(TRADE_FILE)
df_candle = load_candle_csv(CANDLE_FILE)
trade_pairs, log = get_trade_pairs(df_trade)

results = []
for sl in sl_list:
    for be in be_list:
        for ts in ts_list:
            for tss in ts_step_list:
                details = []
                logs = []
                for pair in trade_pairs:
                    res, lg = simulate_trade(pair, df_candle, sl, be, ts, tss)
                    logs.extend(lg)
                    if res is not None:
                        details.append(res)
                pnl_total = sum([x['pnlPct'] for x in details if x is not None])
                winrate = sum(1 for x in details if x and x.get('pnlPct',0)>0) / len(details) * 100 if details else 0
                results.append({'sl':sl,'be':be,'ts_trig':ts,'ts_step':tss,'pnl_total':pnl_total,'winrate':winrate,'count':len(details),'logs':logs[:10]})

results.sort(key=lambda x: x['pnl_total'], reverse=True)
OUT = os.path.join(OUT_DIR, 'grid_search_results.json')
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump({'meta':{'sl_list':sl_list,'be_list':be_list,'ts_list':ts_list,'ts_step_list':ts_step_list}, 'results': results}, f, ensure_ascii=False, indent=2)
print('Wrote', OUT)
