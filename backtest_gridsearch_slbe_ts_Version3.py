import pandas as pd
import numpy as np
from tqdm import tqdm

# DEBUG flag: set True để bật log chi tiết, False để giảm log tối đa
DEBUG = False

def normalize_trade_date(s):
    """Normalize trade date with support for multiple formats"""
    try:
        # Thử format 1: YYYY-MM-DD HH:MM (ACEUSDT/TradingView/BOME format)
        dt = pd.to_datetime(s, format='%Y-%m-%d %H:%M', errors='coerce')
        if not pd.isna(dt):
            # Ensure timezone-naive datetime
            if dt.tz is not None:
                dt = dt.tz_localize(None)
            return dt
    except:
        pass
    
    try:
        # Thử format 2: MM/DD/YYYY HH:MM (Legacy BTC format)
        dt = pd.to_datetime(s, format='%m/%d/%Y %H:%M', errors='coerce')
        if not pd.isna(dt):
            # Ensure timezone-naive datetime
            if dt.tz is not None:
                dt = dt.tz_localize(None)
            return dt
    except:
        pass
    
    try:
        # Fallback: Auto-detect format
        dt = pd.to_datetime(s, errors='coerce')
        if not pd.isna(dt):
            # Ensure timezone-naive datetime
            if dt.tz is not None:
                dt = dt.tz_localize(None)
            return dt
    except:
        pass
        
    return pd.NaT

def normalize_candle_date(s):
    """Normalize candle date with support for multiple formats"""
    try:
        # Thử format 1: YYYY-MM-DD HH:MM (Standard TradingView format)
        dt = pd.to_datetime(s, format='%Y-%m-%d %H:%M', errors='coerce')
        if not pd.isna(dt):
            # Ensure timezone-naive datetime
            if dt.tz is not None:
                dt = dt.tz_localize(None)
            return dt
    except:
        pass
        
    try:
        # Auto-detect other formats
        dt = pd.to_datetime(s, errors='coerce')
        if not pd.isna(dt):
            # Ensure timezone-naive datetime  
            if dt.tz is not None:
                dt = dt.tz_localize(None)
            return dt
    except:
        pass
        
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
    """Find candle index matching datetime with debug info"""
    try:
        arr = df_candle['time'].values
        idx = np.where(arr == np.datetime64(dt))[0]
        if len(idx) == 0:
            if DEBUG:
                print(f"⚠️ DEBUG: Không tìm thấy candle cho {dt} (type: {type(dt)})")
                if len(arr) > 0:
                    print(f"   Sample candle times: {arr[:3]} (type: {type(arr[0])})")
                    print(f"   Target datetime: {pd.to_datetime(dt)} vs Sample: {pd.to_datetime(arr[0])}")
            return -1
        return idx[0]
    except Exception as e:
        if DEBUG:
            print(f"⚠️ ERROR in find_candle_idx: {e}")
        return -1

def simulate_trade(pair, df_candle, sl, be, ts_trig, ts_step):
    log = []
    entryIdx = find_candle_idx(pair['entryDt'], df_candle)
    exitIdx = find_candle_idx(pair['exitDt'], df_candle)
    if entryIdx==-1 or exitIdx==-1 or exitIdx <= entryIdx:
        if DEBUG:
            log.append(f"TradeNum {pair['num']}: Không khớp nến hoặc exit <= entry, bỏ qua")
        return None, log

    prices = df_candle.iloc[entryIdx:exitIdx+1]
    # Use provided prices if numeric, otherwise fall back to candle opens
    try:
        entryPrice = float(pair.get('entryPrice'))
        if np.isnan(entryPrice):
            raise ValueError
    except Exception:
        entryPrice = float(prices.iloc[0]['open'])
    try:
        exitPrice = float(pair.get('exitPrice'))
        if np.isnan(exitPrice):
            raise ValueError
    except Exception:
        exitPrice = float(prices.iloc[-1]['open'])
    side = pair['side']
    use_SL = (sl is not None and sl > 0)
    slPrice = entryPrice*(1-sl/100) if (use_SL and side=='LONG') else entryPrice*(1+sl/100) if (use_SL and side=='SHORT') else None
    use_BE = (be is not None and be > 0)
    use_TS = (ts_trig is not None and ts_trig > 0 and ts_step is not None and ts_step > 0)
    beTrigPrice = entryPrice*(1+be/100) if side=='LONG' else entryPrice*(1-be/100)
    beSLPrice = entryPrice if side=='LONG' else entryPrice
    tsTrigPrice = entryPrice*(1+ts_trig/100) if side=='LONG' else entryPrice*(1-ts_trig/100)
    BE_reached = False
    TS_reached = False
    trailingActive = False
    trailingSL = slPrice if use_SL else None
    finalExitIdx = exitIdx
    finalExitPrice = exitPrice
    finalExitDt = prices.iloc[-1]['time']
    exitType = "EXIT"

    for i in range(1, len(prices)):
        o = float(prices.iloc[i]['open'])
        h = float(prices.iloc[i]['high'])
        l = float(prices.iloc[i]['low'])
        c = float(prices.iloc[i]['close'])
        nowDt = prices.iloc[i]['time']
        if DEBUG:
            log.append(f"Nến {i} {nowDt}: O={o} H={h} L={l} C={c} | trailingSL={trailingSL if trailingSL is not None else 'None'} BE={BE_reached} TS={TS_reached}")
        price_seq = [('open', o), ('high', h), ('low', l), ('close', c)] if side == 'LONG' else [('open', o), ('low', l), ('high', h), ('close', c)]
        for step, price in price_seq:
            # Kiểm tra SL/trailing nếu được chọn
            if use_SL:
                current_active_sl = trailingSL if trailingActive else slPrice
                if current_active_sl is not None:
                    if side == 'LONG' and price <= current_active_sl:
                        finalExitIdx = entryIdx + i
                        # LONG SL Hit: Exit at market price (worse execution)
                        finalExitPrice = price
                        finalExitDt = nowDt
                        exitType = 'TS SL' if trailingActive else 'SL'
                        if DEBUG:
                            log.append(f"--> Hit {'TS' if trailingActive else ''}SL tại {step}={price:.4f} (SL={current_active_sl:.4f}), exit at market={price:.4f}")
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
                            'pnlPct': (finalExitPrice-entryPrice)/entryPrice*100 if side=='LONG' else (entryPrice-finalExitPrice)/entryPrice*100,
                            'sl': sl,
                            'be': be,
                            'tsTrig': ts_trig,
                            'tsStep': ts_step
                        }, log
                    elif side == 'SHORT' and price >= current_active_sl:
                        finalExitIdx = entryIdx + i
                        # SHORT SL Hit: Exit at market price (worse execution)
                        finalExitPrice = price
                        finalExitDt = nowDt
                        exitType = 'TS SL' if trailingActive else 'SL'
                        if DEBUG:
                            log.append(f"--> Hit {'TS' if trailingActive else ''}SL tại {step}={price:.4f} (SL={current_active_sl:.4f}), exit at market={price:.4f}")
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
                            'pnlPct': (finalExitPrice-entryPrice)/entryPrice*100 if side=='LONG' else (entryPrice-finalExitPrice)/entryPrice*100,
                            'sl': sl,
                            'be': be,
                            'tsTrig': ts_trig,
                            'tsStep': ts_step
                        }, log

            # Kích hoạt BE nếu đủ điều kiện và được phép dùng BE
            if use_BE and not BE_reached:
                if (side=='LONG' and price >= beTrigPrice) or (side=='SHORT' and price <= beTrigPrice):
                    BE_reached = True
                    if use_TS:
                        trailingActive = True
                    trailingSL = entryPrice  # BE: dời SL về entry
                    if DEBUG:
                        log.append(f"--> BE kích hoạt tại {step}={price:.4f}, trailingSL dời về entry={entryPrice:.4f}")
            # Kích hoạt trailing nếu đủ điều kiện và được phép dùng trailing
            if use_TS and not TS_reached:
                if (side=='LONG' and price >= tsTrigPrice) or (side=='SHORT' and price <= tsTrigPrice):
                    TS_reached = True
                    trailingActive = True
                    if DEBUG:
                        log.append(f"--> Trailing kích hoạt tại {step}={price:.4f}")
            # Update trailing SL nếu active và đã kích hoạt trailing và được phép dùng trailing
            if use_TS and trailingActive and TS_reached:
                if trailingSL is not None:
                    if side == 'LONG':
                        trailingSL = max(trailingSL, price * (1 - ts_step/100))
                    else:
                        trailingSL = min(trailingSL, price * (1 + ts_step/100))
                    if DEBUG:
                        log.append(f"--> trailingSL update tại {step}={price:.4f}, trailingSL={trailingSL:.4f}")
        if DEBUG:
            log.append(f"Kết thúc nến {i}: trailingSL={trailingSL if trailingSL is not None else 'None'} BE={BE_reached} TS={TS_reached}")

    # Nếu không bị cắt, đóng tại close cuối cùng
    if DEBUG:
        log.append(f"--> Không bị SL/TS, đóng tại close cuối cùng {prices.iloc[-1]['close']:.4f}")
    finalExitPrice = float(prices.iloc[-1]['close'])
    finalExitDt = prices.iloc[-1]['time']
    finalExitIdx = exitIdx
    exitType = "EXIT"
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
        'pnlPct': (finalExitPrice-entryPrice)/entryPrice*100 if side=='LONG' else (entryPrice-finalExitPrice)/entryPrice*100,
        'sl': sl,
        'be': be,
        'tsTrig': ts_trig,
        'tsStep': ts_step
    }, log

    # Kích hoạt BE nếu đủ điều kiện và được phép dùng BE
    if use_BE and not BE_reached:
        if (side=='LONG' and price >= beTrigPrice) or (side=='SHORT' and price <= beTrigPrice):
            BE_reached = True
            if use_TS:
                trailingActive = True
            trailingSL = entryPrice  # BE: dời SL về entry
            if DEBUG:
                log.append(f"--> BE kích hoạt tại {step}={price:.4f}, trailingSL dời về entry={entryPrice:.4f}")
    # Kích hoạt trailing nếu đủ điều kiện và được phép dùng trailing
    if use_TS and not TS_reached:
        if (side=='LONG' and price >= tsTrigPrice) or (side=='SHORT' and price <= tsTrigPrice):
            TS_reached = True
            trailingActive = True
            if DEBUG:
                log.append(f"--> Trailing kích hoạt tại {step}={price:.4f}")
    # Update trailing SL nếu active và đã kích hoạt trailing và được phép dùng trailing
    if use_TS and trailingActive and TS_reached:
        if trailingSL is not None:
            if side == 'LONG':
                trailingSL = max(trailingSL, price * (1 - ts_step/100))
            else:
                trailingSL = min(trailingSL, price * (1 + ts_step/100))
            if DEBUG:
                log.append(f"--> trailingSL update tại {step}={price:.4f}, trailingSL={trailingSL:.4f}")
    # Kết thúc nến, log trạng thái
    if DEBUG:
        log.append(f"Kết thúc nến {i}: trailingSL={trailingSL:.4f} BE={BE_reached} TS={TS_reached}")
    # Nếu không bị cắt, đóng tại close cuối cùng
    if DEBUG:
        log.append(f"--> Không bị SL/TS, đóng tại close cuối cùng {prices.iloc[-1]['close']:.4f}")
    finalExitPrice = float(prices.iloc[-1]['close'])
    finalExitDt = prices.iloc[-1]['time']
    finalExitIdx = exitIdx
    exitType = "EXIT"
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
        'pnlPct': (finalExitPrice-entryPrice)/entryPrice*100 if side=='LONG' else (entryPrice-finalExitPrice)/entryPrice*100,
        'sl': sl,
        'be': be,
        'tsTrig': ts_trig,
        'tsStep': ts_step
    }, log
# === TESTING FRAMEWORK ===
def sanity_check_results(entry_price, exit_price, side, pnl_reported):
    if side == 'LONG':
        expected_pnl = (exit_price - entry_price) / entry_price * 100
    else:
        expected_pnl = (entry_price - exit_price) / entry_price * 100
    if abs(pnl_reported - expected_pnl) > 0.01:
        raise ValueError(f"PnL calculation error: reported {pnl_reported}%, expected {expected_pnl}%")

def test_long_position():
    # Test case: LONG, trailing stop
    entry = 100
    candles = pd.DataFrame({
        'time': pd.date_range('2025-01-01', periods=5, freq='1T'),
        'open': [100,101,102,103,104],
        'high': [101,102,103,104,105],
        'low':  [99,100,101,102,103],
        'close':[100,101,102,103,104]
    })
    pair = {'num':999, 'side':'LONG', 'entryDt':candles.iloc[0]['time'], 'exitDt':candles.iloc[-1]['time'], 'entryPrice':100, 'exitPrice':104}
    res, _ = simulate_trade(pair, candles, sl=1, be=2, ts_trig=3, ts_step=0.5)
    sanity_check_results(res['entryPrice'], res['exitPrice'], res['side'], res['pnlPct'])
    print("LONG test passed.")

def test_short_position():
    # Test case: SHORT, trailing stop
    entry = 100
    candles = pd.DataFrame({
        'time': pd.date_range('2025-01-01', periods=5, freq='1T'),
        'open': [100,99,98,97,96],
        'high': [100,99,98,97,96],
        'low':  [99,98,97,96,95],
        'close':[99,98,97,96,95]
    })
    pair = {'num':998, 'side':'SHORT', 'entryDt':candles.iloc[0]['time'], 'exitDt':candles.iloc[-1]['time'], 'entryPrice':100, 'exitPrice':95}
    res, _ = simulate_trade(pair, candles, sl=1, be=2, ts_trig=3, ts_step=0.5)
    sanity_check_results(res['entryPrice'], res['exitPrice'], res['side'], res['pnlPct'])
    print("SHORT test passed.")



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
        if DEBUG:
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
    # Chỉ hiển thị tiến trình tổng thể bằng tqdm, không print từng tổ hợp
    with Pool(processes=cpu_count()) as pool:
        results = list(tqdm(pool.imap_unordered(run_one_setting, all_args), total=len(all_args), desc="GridSearch"))
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
    import sys
    # Quick debug mode: simulate a specific trade without running full grid search
    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        from backtest_gridsearch_slbe_ts_Version3 import load_trade_csv, load_candle_csv, get_trade_pairs, simulate_trade
        trade_num = int(sys.argv[2]) if len(sys.argv) > 2 else 139
        trades = load_trade_csv("tradelist-fullinfo.csv")
        candles = load_candle_csv("data chart full info.csv")
        pairs, _ = get_trade_pairs(trades)
        trade = next(p for p in pairs if p['num'] == trade_num)
        res, log = simulate_trade(trade, candles, 4.41, 1.76, 7.12, 0.26)
        print(f"🔧 DEBUG Trade #{trade_num} RESULT:", res)
        sys.exit(0)
    # Full grid search with profiling
    print("\n=== Đang chạy grid search, vui lòng chờ... ===")
    profiler = cProfile.Profile()
    profiler.enable()
    main_profile()
    profiler.disable()
    with open("profile_gridsearch.txt", "w") as f:
        ps = pstats.Stats(profiler, stream=f)
        ps.sort_stats("cumtime").print_stats(40)
    print("\n=== Đã ghi profile vào profile_gridsearch.txt ===")
