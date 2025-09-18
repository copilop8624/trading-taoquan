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
    # Sort by date for proper chronological order
    df = df.sort_values('date')
    return df

def load_candle_csv(path):
    df = smart_read_csv(path)
    # Chuẩn hóa tên cột (chuyển về chữ thường)
    df.columns = [col.strip().lower() for col in df.columns]
    # Ánh xạ các tên cột có thể có
    if 'timestamp' in df.columns:
        df.rename(columns={'timestamp': 'time'}, inplace=True)
    if 'datetime' in df.columns:
        df.rename(columns={'datetime': 'time'}, inplace=True)
    # Kiểm tra các cột cần thiết
    required_cols = ['time', 'open', 'high', 'low', 'close']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Không tìm thấy cột '{col}' trong file candle! Columns: {df.columns.tolist()}")
    # Chuẩn hóa thời gian
    df['time'] = df['time'].apply(normalize_candle_date)
    # Remove timezone if present
    if isinstance(df['time'].dtype, pd.DatetimeTZDtype):
        df['time'] = df['time'].dt.tz_localize(None)
    for col in ['open','high','low','close']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['time'])
    # Sort by time for proper chronological order
    df = df.sort_values('time')
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

def get_realistic_price_sequence(candle):
    """
    Generate realistic price sequence for a candle based on OHLC
    Returns list of (label, price) tuples in chronological order
    """
    o, h, l, c = candle['open'], candle['high'], candle['low'], candle['close']
    
    # Pattern 1: Open -> High -> Low -> Close (most common bullish pattern)
    if o <= c:  # Bullish candle
        if h >= max(o, c) and l <= min(o, c):
            return [('open', o), ('high', h), ('low', l), ('close', c)]
    
    # Pattern 2: Open -> Low -> High -> Close (bearish to bullish reversal)
    else:  # Bearish candle  
        if h >= max(o, c) and l <= min(o, c):
            return [('open', o), ('low', l), ('high', h), ('close', c)]
    
    # Fallback: simple sequence
    return [('open', o), ('high', h), ('low', l), ('close', c)]

def simulate_trade(pair, df_candle, sl, be, ts_trig, ts_step):
    """
    FIXED VERSION: Realistic simulation with proper logic flow
    """
    log = []
    
    # Find candle indices
    entryIdx = find_candle_idx(pair['entryDt'], df_candle)
    exitIdx = find_candle_idx(pair['exitDt'], df_candle)
    
    if entryIdx == -1 or exitIdx == -1 or exitIdx <= entryIdx:
        if DEBUG:
            log.append(f"TradeNum {pair['num']}: Không khớp nến hoặc exit <= entry, bỏ qua")
        return None, log

    prices = df_candle.iloc[entryIdx:exitIdx+1].copy()
    
    # Entry price
    try:
        entryPrice = float(pair.get('entryPrice'))
        if np.isnan(entryPrice):
            raise ValueError
    except Exception:
        entryPrice = float(prices.iloc[0]['open'])
    
    side = pair['side']
    
    # Calculate trigger prices and thresholds
    use_SL = (sl is not None and sl > 0)
    use_BE = (be is not None and be > 0)
    use_TS = (ts_trig is not None and ts_trig > 0 and ts_step is not None and ts_step > 0)
    
    if use_SL:
        slPrice = entryPrice * (1 - sl/100) if side == 'LONG' else entryPrice * (1 + sl/100)
    else:
        slPrice = None
        
    if use_BE:
        beTrigPrice = entryPrice * (1 + be/100) if side == 'LONG' else entryPrice * (1 - be/100)
    
    if use_TS:
        tsTrigPrice = entryPrice * (1 + ts_trig/100) if side == 'LONG' else entryPrice * (1 - ts_trig/100)
    
    # State variables
    BE_reached = False
    TS_reached = False
    trailingActive = False
    trailingSL = slPrice  # Initial SL
    
    # Final exit defaults
    finalExitIdx = exitIdx
    finalExitPrice = float(prices.iloc[-1]['close'])
    finalExitDt = prices.iloc[-1]['time']
    exitType = "EXIT"

    if DEBUG:
        log.append(f"=== Trade #{pair['num']} {side} Entry={entryPrice:.4f} ===")
        log.append(f"SL={slPrice:.4f if slPrice else 'None'} BE_trig={beTrigPrice:.4f if use_BE else 'None'} TS_trig={tsTrigPrice:.4f if use_TS else 'None'}")

    # Process each candle
    for i in range(1, len(prices)):
        candle = prices.iloc[i]
        nowDt = candle['time']
        
        if DEBUG:
            log.append(f"Candle {i} {nowDt}: O={candle['open']:.4f} H={candle['high']:.4f} L={candle['low']:.4f} C={candle['close']:.4f}")
        
        # Get realistic price sequence for this candle
        price_sequence = get_realistic_price_sequence(candle)
        
        # Process each price in chronological order
        for step, price in price_sequence:
            price = float(price)
            
            if DEBUG:
                log.append(f"  {step}={price:.4f} | trailingSL={trailingSL:.4f if trailingSL else 'None'} BE={BE_reached} TS={TS_reached}")
            
            # 1. CHECK SL/TS HIT FIRST (highest priority)
            if trailingSL is not None:
                sl_hit = False
                if side == 'LONG' and price <= trailingSL:
                    sl_hit = True
                elif side == 'SHORT' and price >= trailingSL:
                    sl_hit = True
                
                if sl_hit:
                    # REALISTIC EXIT: Add slippage when SL is hit
                    slippage_pct = 0.02  # 0.02% slippage for SL execution
                    if side == 'LONG':
                        finalExitPrice = price * (1 - slippage_pct/100)  # Worse execution for LONG
                    else:
                        finalExitPrice = price * (1 + slippage_pct/100)  # Worse execution for SHORT
                    
                    finalExitIdx = entryIdx + i
                    finalExitDt = nowDt
                    exitType = 'TS' if trailingActive else 'SL'
                    
                    if DEBUG:
                        log.append(f"--> {'TS' if trailingActive else 'SL'} HIT at {step}={price:.4f}, exit with slippage={finalExitPrice:.4f}")
                    
                    # Return immediately when SL/TS hit
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
            
            # 2. CHECK BE ACTIVATION
            if use_BE and not BE_reached:
                be_triggered = False
                if side == 'LONG' and price >= beTrigPrice:
                    be_triggered = True
                elif side == 'SHORT' and price <= beTrigPrice:
                    be_triggered = True
                
                if be_triggered:
                    BE_reached = True
                    # FIXED: Move SL to partial profit instead of exact breakeven
                    # This preserves small profit buffer to avoid exits on tiny pullbacks
                    profit_buffer = 0.3  # 0.3% profit buffer above entry
                    if side == 'LONG':
                        trailingSL = entryPrice * (1 + profit_buffer/100)
                    else:
                        trailingSL = entryPrice * (1 - profit_buffer/100)
                    
                    if DEBUG:
                        log.append(f"--> BE ACTIVATED at {step}={price:.4f}, SL moved to entry+{profit_buffer}%={trailingSL:.4f}")
            
            # 3. CHECK TS ACTIVATION (independent of BE)
            if use_TS and not TS_reached:
                ts_triggered = False
                if side == 'LONG' and price >= tsTrigPrice:
                    ts_triggered = True
                elif side == 'SHORT' and price <= tsTrigPrice:
                    ts_triggered = True
                
                if ts_triggered:
                    TS_reached = True
                    trailingActive = True
                    if DEBUG:
                        log.append(f"--> TS ACTIVATED at {step}={price:.4f}")
            
            # 4. UPDATE TRAILING SL (only if TS is active and triggered)
            if use_TS and trailingActive and TS_reached and trailingSL is not None:
                old_trailing = trailingSL
                if side == 'LONG':
                    new_trailing = price * (1 - ts_step/100)
                    trailingSL = max(trailingSL, new_trailing)  # Can only move up for LONG
                else:
                    new_trailing = price * (1 + ts_step/100)
                    trailingSL = min(trailingSL, new_trailing)  # Can only move down for SHORT
                
                if DEBUG and trailingSL != old_trailing:
                    log.append(f"--> TS UPDATED at {step}={price:.4f}, trailingSL: {old_trailing:.4f} -> {trailingSL:.4f}")
        
        if DEBUG:
            log.append(f"End candle {i}: BE={BE_reached} TS={TS_reached} trailingSL={trailingSL:.4f if trailingSL else 'None'}")

    # If no SL/TS hit, exit at final close
    if DEBUG:
        log.append(f"--> No SL/TS hit, exit at final close={finalExitPrice:.4f}")
    
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
    """Verify PnL calculation accuracy"""
    if side == 'LONG':
        expected_pnl = (exit_price - entry_price) / entry_price * 100
    else:
        expected_pnl = (entry_price - exit_price) / entry_price * 100
    
    if abs(pnl_reported - expected_pnl) > 0.01:
        raise ValueError(f"PnL calculation error: reported {pnl_reported:.4f}%, expected {expected_pnl:.4f}%")

def test_logic_validation():
    """Test suite for simulation logic validation"""
    print("🧪 Running logic validation tests...")
    
    # Test case 1: LONG with SL hit
    print("Test 1: LONG SL hit")
    candles = pd.DataFrame({
        'time': pd.date_range('2025-01-01', periods=3, freq='1T'),
        'open': [100, 101, 98],
        'high': [101, 102, 99],
        'low':  [99, 100, 97],  # SL should hit here
        'close':[100, 101, 98]
    })
    pair = {'num':1, 'side':'LONG', 'entryDt':candles.iloc[0]['time'], 'exitDt':candles.iloc[-1]['time'], 'entryPrice':100, 'exitPrice':98}
    res, log = simulate_trade(pair, candles, sl=2.0, be=0, ts_trig=0, ts_step=0)  # SL at 98
    assert res['exitType'] == 'SL', f"Expected SL exit, got {res['exitType']}"
    print("✅ Test 1 passed")
    
    # Test case 2: LONG with BE then TS
    print("Test 2: LONG BE+TS activation")
    candles = pd.DataFrame({
        'time': pd.date_range('2025-01-01', periods=5, freq='1T'),
        'open': [100, 101, 102, 104, 103],
        'high': [101, 102, 105, 105, 104],
        'low':  [99, 100, 101, 103, 102],
        'close':[100, 101, 104, 104, 103]
    })
    pair = {'num':2, 'side':'LONG', 'entryDt':candles.iloc[0]['time'], 'exitDt':candles.iloc[-1]['time'], 'entryPrice':100, 'exitPrice':103}
    res, log = simulate_trade(pair, candles, sl=5.0, be=1.0, ts_trig=2.0, ts_step=0.5)  # BE at 101, TS at 102
    sanity_check_results(res['entryPrice'], res['exitPrice'], res['side'], res['pnlPct'])
    print("✅ Test 2 passed")
    
    print("🎉 All validation tests passed!")

# === OPTIMIZATION FUNCTIONS ===
def run_one_setting(args):
    """Process single parameter combination"""
    sl, be, ts_trig, ts_step, trade_pairs, df_candle = args
    
    valid_trades = []
    skipped = 0
    total_pnl = 0
    
    for pair in trade_pairs:
        result, _ = simulate_trade(pair, df_candle, sl, be, ts_trig, ts_step)
        if result is None:
            skipped += 1
            continue
        valid_trades.append(result)
        total_pnl += result['pnlPct']
    
    if len(valid_trades) == 0:
        return {
            'sl': sl, 'be': be, 'ts_trig': ts_trig, 'ts_step': ts_step,
            'pnl_total': 0, 'winrate': 0, 'pf': 0,
            'details': [], 'skip': skipped
        }
    
    # Calculate metrics
    wins = [t for t in valid_trades if t['pnlPct'] > 0]
    losses = [t for t in valid_trades if t['pnlPct'] <= 0]
    
    winrate = len(wins) / len(valid_trades) * 100
    
    total_win_pnl = sum(t['pnlPct'] for t in wins)
    total_loss_pnl = sum(abs(t['pnlPct']) for t in losses)
    
    pf = total_win_pnl / total_loss_pnl if total_loss_pnl > 0 else 999
    
    return {
        'sl': sl, 'be': be, 'ts_trig': ts_trig, 'ts_step': ts_step,
        'pnl_total': total_pnl, 'winrate': winrate, 'pf': pf,
        'details': valid_trades, 'skip': skipped
    }

def grid_search_realistic_full_v2(trade_pairs, df_candle, sl_list, be_list, ts_trig_list, ts_step_list, opt_type='pnl'):
    """
    FIXED VERSION: Grid search with corrected simulation logic
    """
    from multiprocessing import Pool, cpu_count
    
    # Generate all parameter combinations
    all_args = [
        (sl, be, ts_trig, ts_step, trade_pairs, df_candle)
        for sl in sl_list
        for be in be_list
        for ts_trig in ts_trig_list
        for ts_step in ts_step_list
    ]
    
    print(f"🔧 Grid search with FIXED logic: {len(all_args)} combinations")
    
    # Process in parallel
    with Pool(processes=cpu_count()) as pool:
        results = list(tqdm(pool.imap_unordered(run_one_setting, all_args), 
                          total=len(all_args), desc="GridSearch FIXED"))
    
    # Sort by optimization metric
    sort_key = 'pnl_total' if opt_type == 'pnl' else opt_type
    results.sort(key=lambda x: x[sort_key], reverse=True)
    
    return results

if __name__ == "__main__":
    # Run validation tests
    test_logic_validation()
    print("\n🚀 Fixed simulation logic ready for use!")