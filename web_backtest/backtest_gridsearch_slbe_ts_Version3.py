import pandas as pd
import numpy as np
try:
    # import shared minimum constant if available
    from ..smart_range_finder import TS_TRIGGER_MIN
except Exception:
    # fallback to local default
    TS_TRIGGER_MIN = 2.5
from tqdm import tqdm

def normalize_trade_date(s):
    try:
        # Định dạng đúng là tháng/ngày/năm
        return pd.to_datetime(s, format='%m/%d/%Y %H:%M', errors='coerce')
    except:
        return pd.NaT

def normalize_candle_date(s):
    try:
        return pd.to_datetime(s, errors='coerce')
    except:
        return pd.NaT

def smart_read_csv(path):
    """Đọc file CSV, tự nhận dạng phân cách ',' hoặc tab"""
    try:
        df = pd.read_csv(path, sep=",")
        if len(df.columns) == 1:
            df = pd.read_csv(path, sep="\t")
    except Exception:
        df = pd.read_csv(path, sep="\t")
    return df

def load_trade_csv(path):
    df = smart_read_csv(path)
    # Chuẩn hóa tên cột
    df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
    # Đổi tên các cột về chuẩn
    rename_map = {
        'trade_#': 'trade',
        'price_usdt': 'price',
        'date/time': 'date',
    }
    df.rename(columns=rename_map, inplace=True)
    # Kiểm tra các cột bắt buộc
    for c in ['trade', 'type', 'date', 'price']:
        if c not in df.columns:
            raise ValueError(f"Không tìm thấy cột '{c}' trong file trade! Header: {df.columns.tolist()}")
    # Chuẩn hóa ngày
    df['date'] = df['date'].apply(normalize_trade_date)
    # Loại bỏ dấu phẩy trong giá trước khi chuyển sang số
    df['price'] = df['price'].astype(str).str.replace(',', '').str.replace('"', '')
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    # Lọc entry/exit
    df = df[df['type'].str.lower().str.contains('entry') | df['type'].str.lower().str.contains('exit')]
    df = df.dropna(subset=['date', 'price'])
    return df

def load_candle_csv(path):
    df = smart_read_csv(path)
    df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
    # Đổi tên cột d thành time nếu có
    rename_map = {
        'd': 'time',
    }
    df.rename(columns=rename_map, inplace=True)
    # Kiểm tra cột time và OHLC
    for c in ['time', 'open', 'high', 'low', 'close']:
        if c not in df.columns:
            raise ValueError(f"Không tìm thấy cột '{c}' trong file candle! Header: {df.columns.tolist()}")
    df['time'] = df['time'].apply(normalize_candle_date)
    # Nếu cột time có timezone, chuyển về dạng không timezone để so sánh dễ hơn
    if isinstance(df['time'].dtype, pd.DatetimeTZDtype):
        df['time'] = df['time'].dt.tz_localize(None)
    for col in ['open','high','low','close']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['time'])
    return df

def get_trade_pairs(df_trade):
    log = []
    pairs = []
    for trade_num in df_trade['trade'].unique():
        group = df_trade[df_trade['trade']==trade_num]
        entry = group[group['type'].str.lower().str.contains('entry')]
        exit = group[group['type'].str.lower().str.contains('exit')]
        if len(entry)==0 or len(exit)==0:
            log.append(f"TradeNum {trade_num}: thiếu Entry hoặc Exit, bỏ qua")
            continue
        entry_row = entry.iloc[0]
        exit_row = exit.iloc[0]
        side = 'LONG' if 'long' in entry_row['type'].lower() else 'SHORT'
        pairs.append({
            'num': trade_num,
            'entryDt': entry_row['date'],
            'exitDt': exit_row['date'],
            'side': side,
            'entryPrice': entry_row['price'],
            'exitPrice': exit_row['price']
        })
    return pairs, log

def find_candle_idx(dt, df_candle):
    arr = df_candle['time'].values
    idx = np.where(arr == np.datetime64(dt))[0]
    return idx[0] if len(idx)>0 else -1

def simulate_trade(pair, df_candle, sl, be, ts_trig, ts_step):
    log = []
    entryIdx = find_candle_idx(pair['entryDt'], df_candle)
    exitIdx = find_candle_idx(pair['exitDt'], df_candle)
    if entryIdx==-1 or exitIdx==-1 or exitIdx <= entryIdx:
        log.append(f"TradeNum {pair['num']}: Không khớp nến hoặc exit <= entry, bỏ qua")
        return None, log
    prices = df_candle.iloc[entryIdx:exitIdx+1]
    entryPrice = prices.iloc[0]['open']
    exitPrice = prices.iloc[-1]['open']
    side = pair['side']
    # Enforce TS trigger floor: clamp incoming ts_trig to minimum allowed
    try:
        ts_trig = float(ts_trig)
    except Exception:
        ts_trig = 0.0
    if ts_trig > 0 and ts_trig < TS_TRIGGER_MIN:
        # clamp to minimum and log
        ts_trig = TS_TRIGGER_MIN
        log.append(f"TS trigger clamped to minimum {TS_TRIGGER_MIN}% for trade {pair['num']}")

    # Enable flags: only run a protection if its parameter > 0
    sl_enabled = (sl > 0)
    be_enabled = (be > 0)
    ts_enabled = (ts_trig > 0 and ts_step > 0)

    # Prices for protections (only meaningful if corresponding enabled)
    slPrice = entryPrice*(1-sl/100) if (side=='LONG' and sl_enabled) else (entryPrice*(1+sl/100) if sl_enabled else None)
    beTrigPrice = entryPrice*(1+be/100) if (side=='LONG' and be_enabled) else (entryPrice*(1-be/100) if be_enabled else None)
    beSLPrice = entryPrice*(1-0.0005) if side=='LONG' else entryPrice*(1+0.0005)
    # trailing-stop trigger price when enabled
    tsTrigPrice = None
    if ts_enabled:
        tsTrigPrice = entryPrice*(1+ts_trig/100) if side=='LONG' else entryPrice*(1-ts_trig/100)

    BE_reached = False
    TS_reached = False
    trailingActive = False
    trailingLevel = 0
    trailingSL = slPrice
    maxTrailingSL = slPrice
    finalExitIdx = exitIdx
    finalExitPrice = exitPrice
    finalExitDt = prices.iloc[-1]['time']
    exitType = "EXIT"
    done = False

    for i in range(1, len(prices)):
        high = prices.iloc[i]['high']
        low = prices.iloc[i]['low']
        nowDt = prices.iloc[i]['time']

        # SL check only if SL enabled and neither BE nor TS activated yet
        if sl_enabled and not BE_reached and not TS_reached:
            if (side=='LONG' and low<=slPrice) or (side=='SHORT' and high>=slPrice):
                finalExitIdx = entryIdx+i
                finalExitPrice = slPrice
                finalExitDt = nowDt
                exitType = "SL"
                done=True
                break

        # BE activation only if BE enabled
        if be_enabled and not BE_reached:
            if (side=='LONG' and high>=beTrigPrice) or (side=='SHORT' and low<=beTrigPrice):
                BE_reached = True
                trailingActive = True
                trailingLevel = 0
                trailingSL = beSLPrice
                maxTrailingSL = beSLPrice

        # TS activation only if TS enabled
        if ts_enabled and not TS_reached:
            if tsTrigPrice is not None and ((side=='LONG' and high>=tsTrigPrice) or (side=='SHORT' and low<=tsTrigPrice)):
                TS_reached = True
                trailingActive = True
                # Initialize trailingSL: prefer slPrice when present, otherwise use tsTrigPrice so it's numeric
                if slPrice is not None:
                    if trailingSL is not None:
                        trailingSL = max(trailingSL, slPrice)
                    else:
                        trailingSL = slPrice
                else:
                    # fallback to tsTrigPrice to ensure trailingSL is numeric
                    trailingSL = tsTrigPrice if tsTrigPrice is not None else entryPrice
                maxTrailingSL = trailingSL

        if trailingActive:
            priceNow = high if side=='LONG' else low
            fromEntry = (priceNow-entryPrice) if side=='LONG' else (entryPrice-priceNow)
            fromEntryPct = fromEntry/entryPrice*100
            stepCount = 0
            # Compute stepCount from TS if TS is enabled and ts_step > 0.
            if TS_reached and ts_step > 0:
                stepCount = int((fromEntryPct-ts_trig)/ts_step)
            # Also allow stepping based on BE progress if BE reached
            if BE_reached:
                fromBETrigPct = (priceNow-entryPrice)/entryPrice*100 if side=='LONG' else (entryPrice-priceNow)/entryPrice*100
                if fromBETrigPct>=be and ts_step > 0:
                    stepCount = int((fromBETrigPct-be)/ts_step)
                else:
                    stepCount = 0
            if stepCount>trailingLevel:
                trailingLevel = stepCount
                newTrailingSL = (entryPrice*(1+(ts_trig+trailingLevel*ts_step)/100)) if side=='LONG' else (entryPrice*(1-(ts_trig+trailingLevel*ts_step)/100))
                if BE_reached:
                    if side=='LONG': newTrailingSL = max(newTrailingSL, beSLPrice)
                    else: newTrailingSL = min(newTrailingSL, beSLPrice)
                trailingSL = newTrailingSL
                maxTrailingSL = trailingSL
            if (side=='LONG' and low<=trailingSL) or (side=='SHORT' and high>=trailingSL):
                finalExitIdx = entryIdx+i
                finalExitPrice = trailingSL
                finalExitDt = nowDt
                exitType = "BE SL" if BE_reached and trailingSL==beSLPrice and not TS_reached else "TS SL"
                done=True
                break

    pnl = (finalExitPrice-entryPrice) if side=='LONG' else (entryPrice-finalExitPrice)
    pnlPct = pnl/entryPrice*100 if entryPrice!=0 else 0
    return {
        'num': pair['num'],
        'side': side,
        'entryIdx': entryIdx,
        'exitIdx': finalExitIdx,
        'entryDt': prices.iloc[0]['time'],
        'exitDt': finalExitDt,
        'entryPrice': entryPrice,
        'exitPrice': finalExitPrice,
        'exitType': exitType,
        'pnlPctOrigin': (pair['exitPrice']-pair['entryPrice'])/pair['entryPrice']*100 if side=='LONG' else (pair['entryPrice']-pair['exitPrice'])/pair['entryPrice']*100,
        'pnlPct': pnlPct,
        'sl': sl,
        'be': be,
    'tsTrig': ts_trig,
    'tsStep': ts_step,
    'sl_enabled': sl_enabled,
    'be_enabled': be_enabled,
    'ts_enabled': ts_enabled
    }, log


from multiprocessing import Pool, cpu_count

def run_one_setting(args):
    sl, be, ts_trig, ts_step, trade_pairs, df_candle = args
    details = []
    skip = 0
    logs = []
    win_count = 0
    gain_sum = 0
    loss_sum = 0
    for pair in trade_pairs:
        res, log = simulate_trade(pair, df_candle, sl, be, ts_trig, ts_step)
        logs.extend(log)
        if res is not None:
            details.append(res)
            if res['pnlPct'] > 0: win_count += 1
            if res['pnlPct'] > 0: gain_sum += res['pnlPct']
            else: loss_sum -= res['pnlPct']
        else:
            skip += 1
    winrate = win_count / len(details) * 100 if len(details) > 0 else 0
    pf = gain_sum / loss_sum if loss_sum > 0 else 0
    pnl_total = sum([x['pnlPct'] for x in details if not np.isnan(x['pnlPct'])])
    return {
        'sl': sl, 'be': be, 'ts_trig': ts_trig, 'ts_step': ts_step,
        'pnl_total': pnl_total, 'winrate': winrate, 'pf': pf,
        'details': details, 'skip': skip, 'log': logs
    }

def grid_search_parallel(trade_pairs, df_candle, sl_list, be_list, ts_trig_list, ts_step_list, opt_type):
    all_args = [
        (sl, be, ts_trig, ts_step, trade_pairs, df_candle)
        for sl in sl_list
        for be in be_list
        for ts_trig in ts_trig_list
        for ts_step in ts_step_list
    ]
    print(f"Đang chạy {len(all_args):,} tổ hợp...")
    with Pool(processes=cpu_count()) as pool:
        results = list(tqdm(pool.imap_unordered(run_one_setting, all_args), total=len(all_args)))
    results.sort(key=lambda x: x[opt_type if opt_type != 'pnl' else 'pnl_total'], reverse=True)
    return results





# ===== Thêm profiling cho toàn bộ grid search =====
import cProfile
import pstats
def main_profile():
    path_trade = "60-tradelist-LONGSHORT.csv"
    path_candle = "BINANCE_BTCUSDT, 60.csv"
    df_trade = load_trade_csv(path_trade)
    df_candle = load_candle_csv(path_candle)

    # ===== KIỂM TRA NHANH MIN/MAX THỜI GIAN VÀ LỌC TRADE THEO VÙNG CANDLE =====
    entry_times = []
    exit_times = []
    for trade_num in df_trade['trade'].unique():
        group = df_trade[df_trade['trade']==trade_num]
        entry = group[group['type'].str.lower().str.contains('entry')]
        exit = group[group['type'].str.lower().str.contains('exit')]
        if len(entry)==0 or len(exit)==0:
            continue
        entry_times.append(entry.iloc[0]['date'])
        exit_times.append(exit.iloc[0]['date'])
    min_candle = df_candle['time'].min()
    max_candle = df_candle['time'].max()
    df_trade = df_trade[(df_trade['date'] >= min_candle) & (df_trade['date'] <= max_candle)]

    # ===== CHỌN SỐ LƯỢNG LỆNH KHẢO SÁT =====
    try:
        n_trades = int(input("Nhập số lượng lệnh cần khảo sát (0 = tất cả): "))
    except Exception:
        n_trades = 0
    if n_trades > 0:
        trade_order = df_trade.sort_values('date', ascending=False)['trade'].unique()[:n_trades]
        df_trade = df_trade[df_trade['trade'].isin(trade_order)]
    else:
        pass

    # Chạy grid search với các tham số mẫu
    trade_pairs, log_init = get_trade_pairs(df_trade)
    import numpy as np
    # Cấu hình dạng min, max, step
    sl_min, sl_max, sl_step = 0.5, 3, 0.1
    be_min, be_max, be_step = 0.2, 3, 0.1
    ts_trig_min, ts_trig_max, ts_trig_step = 0.5, 5, 0.2
    ts_step_min, ts_step_max, ts_step_step = 0.1, 5, 0.5
    # Sinh list giá trị
    sl_list = list(np.arange(sl_min, sl_max + sl_step/2, sl_step))
    be_list = list(np.arange(be_min, be_max + be_step/2, be_step))
    ts_trig_list = list(np.arange(ts_trig_min, ts_trig_max + ts_trig_step/2, ts_trig_step))
    ts_step_list = list(np.arange(ts_step_min, ts_step_max + ts_step_step/2, ts_step_step))
    opt_type = 'pnl'  # hoặc 'winrate', 'pf'
    results = grid_search_parallel(trade_pairs, df_candle, sl_list, be_list, ts_trig_list, ts_step_list, opt_type)
    print("\nTop 5 bộ SL, BE, TS tối ưu:")
    for i, res in enumerate(results[:5]):
        print(f"#{i+1}: SL={res['sl']} BE={res['be']} TS trig={res['ts_trig']} TS step={res['ts_step']}: "
              f"PnL={res['pnl_total']:.2f} Winrate={res['winrate']:.2f} PF={res['pf']:.2f} Lệnh hợp lệ: {len(res['details'])} Lệnh loại: {res['skip']}")
    # Xuất log chi tiết cho kết quả tối ưu số 1 (top 1)
    pd.DataFrame(results[0]['details']).to_csv('slbe_ts_opt_results.csv', index=False)
    pd.DataFrame({'Log': results[0]['log']}).to_csv('slbe_ts_opt_log.csv', index=False)

if __name__=="__main__":
    print("\n=== Đang chạy với profiling (cProfile) ===")
    profiler = cProfile.Profile()
    profiler.enable()
    main_profile()
    profiler.disable()
    with open("profile_gridsearch.txt", "w") as f:
        ps = pstats.Stats(profiler, stream=f)
        ps.sort_stats("cumtime").print_stats(40)
    print("\n=== Đã ghi profile vào profile_gridsearch.txt ===")
