
import pandas as pd
import numpy as np
from tqdm import tqdm
from backend.utils.common import safe_int

# DEBUG flag: set True để bật log chi tiết, False để giảm log tối đa
DEBUG = False



def find_candle_idx(dt, df_candle):
    """Tìm index của nến có thời gian chính xác khớp với dt"""
    if pd.isna(dt):
        return -1
        
    arr = df_candle['time'].values
    target_dt = np.datetime64(dt)
    
    # Kiểm tra xem target_dt có nằm trong khoảng dữ liệu không
    min_time = arr[0]
    max_time = arr[-1] 
    if target_dt < min_time or target_dt > max_time:
        return -1  # Nằm ngoài khoảng dữ liệu
    
    idx = np.where(arr == target_dt)[0]
    return idx[0] if len(idx) > 0 else -1

def simulate_trade_realistic(pair, df_candle, sl, be, ts_trig, ts_step):
    """
    REALISTIC TRADING SIMULATION với logic đúng thực tế:
    - Entry: Open của nến entry (vào lệnh ngay khi tín hiệu phát sinh)
    - Exit: Open của nến exit (exit ngay khi signal exit phát sinh)
    - SL/BE/TS: Check theo HIGH/LOW thực tế trong từng nến
    """
    log = []
    entryIdx = find_candle_idx(pair['entryDt'], df_candle)
    exitIdx = find_candle_idx(pair['exitDt'], df_candle)
    
    if entryIdx==-1 or exitIdx==-1 or exitIdx <= entryIdx:
        log.append(f"TradeNum {pair['num']}: Không khớp nến hoặc exit <= entry, bỏ qua")
        return None, log
    
    prices = df_candle.iloc[entryIdx:exitIdx+1]
    side = pair['side']
    
    # REALISTIC ENTRY LOGIC:
    # Entry tại OPEN của nến entry (tín hiệu phát sinh, vào lệnh ngay)
    entryPrice = float(prices.iloc[0]['open'])
    
    # REALISTIC EXIT LOGIC:  
    # Nếu không có SL/BE/TS hit, exit tại OPEN của nến exit
    originalExitPrice = float(prices.iloc[-1]['open'])
    
    # CALCULATE ALL TRIGGER LEVELS
    if sl > 0:
        slPrice = entryPrice * (1 - sl/100) if side == 'LONG' else entryPrice * (1 + sl/100)
    else:
        slPrice = None
    
    # BE logic: BE=0 means "immediate breakeven when profit exists"
    if be > 0:
        # BE>0: Trigger when profit reaches be%
        BE_reached = False
        beTriggerPrice = entryPrice * (1 + be/100) if side == 'LONG' else entryPrice * (1 - be/100)
        beSLPrice = entryPrice  # Move SL to entry price (breakeven)
    elif be == 0:
        # BE=0: Immediate breakeven when any profit exists
        BE_reached = False
        # For LONG: Any price > entry triggers BE
        # For SHORT: Any price < entry triggers BE
        beTriggerPrice = entryPrice  # Trigger at entry price (immediate)
        beSLPrice = entryPrice
    else:
        # BE<0: Disabled
        BE_reached = False
        beTriggerPrice = None
        beSLPrice = None
    
    # TS logic: TS=0 means "immediate trailing from entry"
    if ts_trig > 0:
        # TS>0: Trigger when profit reaches ts_trig%
        TS_reached = False
        tsTriggerPrice = entryPrice * (1 + ts_trig/100) if side == 'LONG' else entryPrice * (1 - ts_trig/100)
    elif ts_trig == 0 and ts_step > 0:
        # TS=0: Immediate trailing from entry
        TS_reached = False
        tsTriggerPrice = entryPrice  # Trigger at entry price (immediate)
    else:
        # TS<0 or ts_step=0: Disabled
        TS_reached = False
        tsTriggerPrice = None    # STATE VARIABLES  
    # Start with regular SL only
    current_sl = slPrice
    trailing_active = False
    highest_profit = 0
    
    # Log initial state chỉ khi DEBUG
    if DEBUG:
        log.append(f"=== TRADE {pair['num']} REALISTIC SIMULATION ===")
        log.append(f"Entry: {entryPrice:.6f} at {prices.iloc[0]['time']}")
        log.append(f"Original Exit: {originalExitPrice:.6f} at {prices.iloc[-1]['time']}")
        log.append(f"Side: {side}, SL: {sl}%, BE: {be}%, TS: {ts_trig}%/{ts_step}%")
        sl_str = f"{slPrice:.6f}" if slPrice is not None else "None"
        be_str = f"{beTriggerPrice:.6f}" if beTriggerPrice is not None else "Disabled"
        ts_str = f"{tsTriggerPrice:.6f}" if tsTriggerPrice is not None else "Disabled"
        current_sl_str = f"{current_sl:.6f}" if current_sl is not None else "None"
        log.append(f"SL Price: {sl_str}")
        log.append(f"BE: {'Enabled' if be > 0 else ('Immediate' if be == 0 else 'Disabled')} (trigger: {be_str})")
        log.append(f"TS: {'Enabled' if ts_trig > 0 else ('Immediate' if ts_trig == 0 and ts_step > 0 else 'Disabled')} (trigger: {ts_str})")
        log.append(f"Initial current_sl: {current_sl_str}, trailing_active: {trailing_active}")
    
    # SCAN THROUGH ALL CANDLES FOR REALISTIC PRICE ACTION
    for i in range(len(prices)):
        candle = prices.iloc[i]
        high = float(candle['high'])
        low = float(candle['low'])
        close = float(candle['close'])
        candle_time = candle['time']
        
        # REALISTIC PRICE MOVEMENT WITHIN CANDLE:
        # Giá di chuyển từ open -> high/low -> close
        # Cần check trigger theo thứ tự thực tế
        
        if i == 0:
            # Entry candle: bắt đầu từ open price
            start_price = entryPrice
        else:
            # Các candle sau: bắt đầu từ open của candle đó
            start_price = float(candle['open'])
        
        if DEBUG:
            log.append(f"Candle {i}: {candle_time}, O:{start_price:.6f} H:{high:.6f} L:{low:.6f} C:{close:.6f}")
        
        # TRONG MỖI CANDLE, CHECK TRIGGERS THEO THỨ TỰ REALISTIC:
        # 1. Check SL hit first (highest priority)
        # 2. Check BE/TS triggers 
        # 3. Update trailing SL if TS active
        
        # 1. CHECK SL HIT (nếu có SL và chưa bị override bởi BE/TS)
        if current_sl is not None:
            sl_hit = False
            if side == 'LONG' and low <= current_sl:
                # LONG SL hit: Giá chạm mức SL
                exit_price = max(current_sl, low)  # Thực tế có thể slippage
                exit_type = "TS SL" if trailing_active else ("BE SL" if BE_reached else "SL")
                if DEBUG:
                    log.append(f"  --> {exit_type} HIT at candle {i}: price {exit_price:.6f} (SL: {current_sl:.6f})")
                
                # Calculate final PnL
                pnl_pct = (exit_price - entryPrice) / entryPrice * 100
                
                return create_result(pair, entryPrice, exit_price, exit_type, pnl_pct, 
                                   sl, be, ts_trig, ts_step, candle_time), log
                
            elif side == 'SHORT' and high >= current_sl:
                # SHORT SL hit: Giá chạm mức SL  
                exit_price = min(current_sl, high)  # Thực tế có thể slippage
                exit_type = "TS SL" if trailing_active else ("BE SL" if BE_reached else "SL")
                if DEBUG:
                    log.append(f"  --> {exit_type} HIT at candle {i}: price {exit_price:.6f} (SL: {current_sl:.6f})")
                
                # Calculate final PnL
                pnl_pct = (entryPrice - exit_price) / entryPrice * 100
                
                return create_result(pair, entryPrice, exit_price, exit_type, pnl_pct,
                                   sl, be, ts_trig, ts_step, candle_time), log
        
        # 2. CHECK BE TRIGGER (nếu chưa đạt và be >= 0)
        if not BE_reached and beTriggerPrice is not None:
            be_triggered = False
            if be > 0:
                # BE>0: Normal trigger when profit reaches BE%
                if side == 'LONG' and high >= beTriggerPrice:
                    be_triggered = True
                    trigger_price = min(high, beTriggerPrice)
                elif side == 'SHORT' and low <= beTriggerPrice:
                    be_triggered = True  
                    trigger_price = max(low, beTriggerPrice)
            elif be == 0:
                # BE=0: Immediate trigger when any profit exists
                if side == 'LONG' and high > entryPrice:
                    be_triggered = True
                    trigger_price = high  # Any profit triggers
                elif side == 'SHORT' and low < entryPrice:
                    be_triggered = True  
                    trigger_price = low  # Any profit triggers
                
            if be_triggered:
                BE_reached = True
                # Update current SL to breakeven if no TS active
                if not trailing_active:
                    current_sl = beSLPrice
                if DEBUG:
                    log.append(f"  --> BE TRIGGERED at candle {i}: price {trigger_price:.6f}")
                    log.append(f"      SL moved to breakeven: {beSLPrice:.6f}")
        
        # 3. CHECK TS TRIGGER (nếu chưa đạt và ts_trig >= 0)
        if not TS_reached and tsTriggerPrice is not None:
            ts_triggered = False
            if ts_trig > 0:
                # TS>0: Normal trigger when profit reaches TS%
                if side == 'LONG' and high >= tsTriggerPrice:
                    ts_triggered = True
                    trigger_price = min(high, tsTriggerPrice)
                elif side == 'SHORT' and low <= tsTriggerPrice:
                    ts_triggered = True
                    trigger_price = max(low, tsTriggerPrice)
            elif ts_trig == 0:
                # TS=0: Immediate trigger when any profit exists
                if side == 'LONG' and high > entryPrice:
                    ts_triggered = True
                    trigger_price = high  # Any profit triggers
                elif side == 'SHORT' and low < entryPrice:
                    ts_triggered = True
                    trigger_price = low  # Any profit triggers
                
            if ts_triggered:
                TS_reached = True
                trailing_active = True
                # TS takes priority over BE
                current_sl = max(current_sl or 0, entryPrice) if side == 'LONG' else min(current_sl or float('inf'), entryPrice)
                if DEBUG:
                    log.append(f"  --> TS TRIGGERED at candle {i}: price {trigger_price:.6f}")
                    log.append(f"      Trailing SL activated with initial SL: {current_sl:.6f}")
        
        # 4. UPDATE TRAILING SL (nếu TS active và ts_step > 0)
        if trailing_active and ts_step > 0:
            # Tính profit hiện tại từ entry
            current_price = high if side == 'LONG' else low
            profit = (current_price - entryPrice) if side == 'LONG' else (entryPrice - current_price)
            profit_pct = profit / entryPrice * 100
            
            if profit_pct > highest_profit:
                highest_profit = profit_pct
                
                # Tính trailing level mới
                if profit_pct >= ts_trig:
                    trailing_steps = int((profit_pct - ts_trig) / ts_step)
                    new_sl_pct = ts_trig + trailing_steps * ts_step
                    
                    if side == 'LONG':
                        new_trailing_sl = entryPrice * (1 + new_sl_pct / 100)
                    else:
                        new_trailing_sl = entryPrice * (1 - new_sl_pct / 100)
                    
                    # Ensure trailing SL only moves favorably
                    if current_sl is None or \
                       (side == 'LONG' and new_trailing_sl > current_sl) or \
                       (side == 'SHORT' and new_trailing_sl < current_sl):
                        current_sl = new_trailing_sl
                        if DEBUG:
                            log.append(f"  --> Trailing SL updated: {current_sl:.6f} (profit: {profit_pct:.2f}%)")
    
    # 5. NO SL/BE/TS HIT - EXIT NORMALLY
    exit_price = originalExitPrice
    exit_type = "Signal"
    
    if side == 'LONG':
        pnl_pct = (exit_price - entryPrice) / entryPrice * 100
    else:
        pnl_pct = (entryPrice - exit_price) / entryPrice * 100
    
    if DEBUG:
        log.append(f"  --> Normal exit at signal: {exit_price:.6f}")
    
    return create_result(pair, entryPrice, exit_price, exit_type, pnl_pct,
                        sl, be, ts_trig, ts_step, prices.iloc[-1]['time']), log

def create_result(pair, entry_price, exit_price, exit_type, pnl_pct, sl, be, ts_trig, ts_step, exit_time):
    """Helper để tạo result object chuẩn"""
    # Calculate original PnL for comparison (from tradelist data)
    if pair['side'] == 'LONG':
        pnl_origin = (pair['exitPrice'] - pair['entryPrice']) / pair['entryPrice'] * 100
    else:
        pnl_origin = (pair['entryPrice'] - pair['exitPrice']) / pair['entryPrice'] * 100
    
    return {
        'num': pair['num'],
        'side': pair['side'],
        'entryDt': pair['entryDt'],
        'exitDt': exit_time,
        'entryPrice': float(entry_price),
        'exitPrice': float(exit_price),
        'exitType': exit_type,
        'pnlPct': float(pnl_pct),
        'pnlPctOrigin': float(pnl_origin),
        'sl': sl,
        'be': be,
        'ts_trig': ts_trig,
        'ts_step': ts_step
    }

# Wrapper function để maintain compatibility
def simulate_trade(pair, df_candle, sl, be, ts_trig, ts_step):
    """Wrapper function for backward compatibility"""
    return simulate_trade_realistic(pair, df_candle, sl, be, ts_trig, ts_step)

# Keep the rest of the functions unchanged for now...
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
    if DEBUG:
        print(f"Đang chạy {len(all_args):,} tổ hợp với REALISTIC SIMULATION...")
    with Pool(processes=cpu_count()) as pool:
        results = list(tqdm(pool.imap_unordered(run_one_setting, all_args), total=len(all_args)))
    results.sort(key=lambda x: x[opt_type if opt_type != 'pnl' else 'pnl_total'], reverse=True)
    return results
