import pandas as pd
import sqlite3
import os
from datetime import datetime
import glob

DB_FILE = 'candlestick_data.db'
# Chỉ quét file csv trong thư mục tradelist
TRADELIST_PATTERN = os.path.join('tradelist', '*.csv')
REPORT_FILE = 'batch_tradelist_candle_report.txt'

# Lấy danh sách symbol, timeframe có trong DB
def get_db_symbols_timeframes(db_file):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('SELECT DISTINCT symbol, timeframe FROM candlestick_data')
    rows = c.fetchall()
    conn.close()
    return set((r[0], r[1]) for r in rows)

# Đoán symbol, timeframe từ tên file tradelist
# Ví dụ: TaoQuan_Strategy_Tester_BINANCE_1000FLOKIUSDT.P_2025-09-22.csv => symbol=FLOKIUSDT, timeframe=30m (nếu có trong DB)
def guess_symbol_timeframe(filename, db_symbols_timeframes):
    import re
    name = os.path.basename(filename).lower()
    name_no_ext = os.path.splitext(name)[0]
    # Loại bỏ prefix phổ biến
    name_clean = re.sub(r'(taoquan_strategy_tester_|strategy_tester_|tradelist_|binance_|tester_|test_)', '', name_no_ext, flags=re.IGNORECASE)
    # Loại bỏ các ký tự không phải chữ/số
    name_clean = re.sub(r'[^a-zA-Z0-9_]', '_', name_clean)
    # Tách các phần bằng _
    parts = name_clean.split('_')
    # Tạo các candidate symbol từ các phần dài >=6 ký tự, kết hợp các phần liên tiếp
    candidates = set()
    for i in range(len(parts)):
        for j in range(i+1, min(i+4, len(parts))+1):
            candidate = ''.join(parts[i:j])
            if len(candidate) >= 6:
                candidates.add(candidate.upper())
    # Tạo các candidate timeframe phổ biến
    tf_candidates = set(['1m','3m','5m','15m','30m','60m','1h','4h','1d'])
    for p in parts:
        if p.lower() in tf_candidates:
            tf_candidates.add(p.lower())
        if p.lower().endswith('m') or p.lower().endswith('h') or p.lower().endswith('d'):
            tf_candidates.add(p.lower())
    # Fuzzy match symbol/timeframe trong DB
    for symbol, timeframe in db_symbols_timeframes:
        symbol_l = symbol.lower()
        tf_l = timeframe.lower()
        # Match symbol gần đúng
        for cand in candidates:
            if cand in symbol or cand in symbol_l or symbol_l in cand.lower():
                # Match timeframe gần đúng
                for tf_cand in tf_candidates:
                    if tf_cand in tf_l or tf_l in tf_cand:
                        return symbol, timeframe
        # Nếu symbol match nhưng timeframe không rõ, thử match timeframe phổ biến
        for cand in candidates:
            if cand in symbol or cand in symbol_l or symbol_l in cand.lower():
                if tf_l in ['30m','60m','1h']:
                    return symbol, timeframe
    # Nếu vẫn không đoán được, thử match symbol chính xác, timeframe bất kỳ
    for symbol, timeframe in db_symbols_timeframes:
        symbol_l = symbol.lower()
        for cand in candidates:
            if cand == symbol or cand == symbol_l:
                return symbol, timeframe
    return None, None

# Kiểm tra từng tradelist với candle DB
def check_tradelist_vs_candle(tradelist_file, db_file, db_symbols_timeframes):
    try:
        df = pd.read_csv(tradelist_file)
        # Tìm cột thời gian
        for col in ['entry_time', 'date_time', 'open_time', 'time', 'Date/Time']:
            if col in df.columns:
                df['entry_time'] = df[col]
                break
        else:
            return f'{tradelist_file}: ❌ Không tìm thấy cột thời gian entry! Cột có: {list(df.columns)}\n'
        symbol, timeframe = guess_symbol_timeframe(tradelist_file, db_symbols_timeframes)
        if not symbol or not timeframe:
            return f'{tradelist_file}: ❌ Không đoán được symbol/timeframe phù hợp DB!\n'
        # Đọc candle từ DB
        conn = sqlite3.connect(db_file)
        query = "SELECT * FROM candlestick_data WHERE symbol = ? AND timeframe = ?"
        candle_df = pd.read_sql_query(query, conn, params=[symbol, timeframe])
        conn.close()
        if candle_df.empty:
            return f'{tradelist_file}: ❌ Không có dữ liệu nến trong DB cho symbol={symbol}, timeframe={timeframe}\n'
        # Chuẩn hóa candle time
        candle_times = set()
        for candle_time in candle_df['open_time'] if 'open_time' in candle_df.columns else candle_df['time']:
            try:
                if isinstance(candle_time, str) and candle_time.isdigit():
                    candle_times.add(int(candle_time))
                elif isinstance(candle_time, float) or isinstance(candle_time, int):
                    candle_times.add(int(candle_time))
                else:
                    candle_times.add(int(pd.to_datetime(candle_time).timestamp()))
            except Exception:
                continue
        # Kiểm tra từng trade
        missing = 0
        for idx, row in df.iterrows():
            entry_time = row['entry_time']
            try:
                if isinstance(entry_time, str) and entry_time.isdigit():
                    entry_ts = int(entry_time)
                elif isinstance(entry_time, float) or isinstance(entry_time, int):
                    entry_ts = int(entry_time)
                else:
                    entry_ts = int(pd.to_datetime(entry_time).timestamp())
            except Exception:
                continue
            # Cho phép lệch 1h
            found = any(abs(candle_ts - entry_ts) < 60*60 for candle_ts in candle_times)
            if not found:
                missing += 1
        return f'{tradelist_file}: Tổng trade: {len(df)}, nến DB: {len(candle_times)}, trade khớp: {len(df)-missing}, thiếu nến: {missing}\n'
    except Exception as e:
        return f'{tradelist_file}: ❌ Lỗi: {e}\n'

if __name__ == '__main__':
    db_symbols_timeframes = get_db_symbols_timeframes(DB_FILE)
    tradelist_files = glob.glob(TRADELIST_PATTERN)
    report_lines = []
    for tradelist_file in tradelist_files:
        # Bỏ qua các file không phải tradelist thực sự (ví dụ: candle csv, log, v.v.)
        if 'tradelist' not in tradelist_file.lower() and 'strategy' not in tradelist_file.lower():
            continue
        result = check_tradelist_vs_candle(tradelist_file, DB_FILE, db_symbols_timeframes)
        print(result.strip())
        report_lines.append(result)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.writelines(report_lines)
    print(f'\n==> Đã xuất báo cáo tổng hợp: {REPORT_FILE}')
