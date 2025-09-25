
import pandas as pd
import sqlite3
import os
from datetime import datetime

# === CONFIG THỰC TẾ CHO FLOKIUSDT 30M ===
# File tradelist thực tế (KHÔNG có đường dẫn, chỉ tên file trong thư mục hiện tại)
TRADELIST_FILE = 'TaoQuan_Strategy_Tester_BINANCE_1000FLOKIUSDT.P_2025-09-22.csv'  # Đổi đúng tên file tradelist bạn đang dùng

# Nếu dùng database candle:
CANDLE_DB = 'candlestick_data.db'  # Đúng tên file DB trong workspace
CANDLE_SYMBOL = 'FLOKIUSDT'      # Đúng symbol trong DB (chú ý: có thể là 'BINANCE_FLOKIUSDT' hoặc 'BINANCE_1000FLOKIUSDT.P')
CANDLE_TIMEFRAME = '30m'                        # Đúng timeframe trong DB (chuỗi, ví dụ '30' hoặc '30m')


# === Đọc tradelist ===
def load_tradelist(tradelist_file):
    try:
        df = pd.read_csv(tradelist_file)
        # Ưu tiên các cột thời gian phổ biến
        for col in ['entry_time', 'date_time', 'open_time', 'time', 'Date/Time']:
            if col in df.columns:
                df['entry_time'] = df[col]
                break
        else:
            # Nếu không có cột thời gian phổ biến, báo lỗi rõ ràng
            print(f"❌ Không tìm thấy cột thời gian entry! Các cột có trong file: {list(df.columns)}")
            raise Exception('Không tìm thấy cột thời gian entry trong tradelist!')
        return df
    except Exception as e:
        print(f'❌ Lỗi đọc tradelist: {e}')
        return None

# === Đọc candle từ file CSV ===
def load_candle_csv(candle_file):
    try:
        df = pd.read_csv(candle_file)
        for col in ['open_time', 'time', 'date_time']:
            if col in df.columns:
                df['candle_time'] = df[col]
                break
        else:
            raise Exception('Không tìm thấy cột thời gian trong file candle!')
        return df
    except Exception as e:
        print(f'❌ Lỗi đọc file candle CSV: {e}')
        return None

# === Đọc candle từ database ===
def load_candle_db(db_file, symbol, timeframe):
    try:
        conn = sqlite3.connect(db_file)
        query = "SELECT * FROM candlestick_data WHERE symbol = ? AND timeframe = ?"
        df = pd.read_sql_query(query, conn, params=[symbol, timeframe])
        conn.close()
        if 'open_time' in df.columns:
            df['candle_time'] = df['open_time']
        elif 'time' in df.columns:
            df['candle_time'] = df['time']
        else:
            raise Exception('Không tìm thấy cột thời gian trong bảng candle!')
        return df
    except Exception as e:
        print(f'❌ Lỗi đọc candle từ database: {e}')
        return None

# === So khớp từng trade với candle ===
def check_trades_vs_candles(trade_df, candle_df):
    print(f'🔍 Tổng số trade: {len(trade_df)}')
    print(f'🔍 Tổng số nến: {len(candle_df)}')
    # Chuẩn hóa candle time về int timestamp
    candle_times = []
    for candle_time in candle_df['candle_time']:
        try:
            if isinstance(candle_time, str) and candle_time.isdigit():
                candle_times.append(int(candle_time))
            elif isinstance(candle_time, float) or isinstance(candle_time, int):
                candle_times.append(int(candle_time))
            else:
                candle_times.append(int(pd.to_datetime(candle_time).timestamp()))
        except Exception:
            candle_times.append(None)
    # Thử các offset phổ biến (giờ): 0, +7, -7, +8, -8, +9, -9
    offsets = [0, 7, -7, 8, -8, 9, -9]
    best_offset = 0
    best_matched = 0
    offset_results = {}
    for offset in offsets:
        matched = 0
        for idx, row in trade_df.iterrows():
            entry_time = row['entry_time']
            try:
                if isinstance(entry_time, str) and entry_time.isdigit():
                    entry_ts = int(entry_time)
                elif isinstance(entry_time, float) or isinstance(entry_time, int):
                    entry_ts = int(entry_time)
                else:
                    entry_ts = int(pd.to_datetime(entry_time).timestamp())
                entry_ts = entry_ts - offset*3600  # Trừ offset giờ
            except Exception:
                continue
            found = False
            for candle_ts in candle_times:
                if candle_ts is not None and abs(candle_ts - entry_ts) < 60*60:
                    found = True
                    break
            if found:
                matched += 1
        offset_results[offset] = matched
        if matched > best_matched:
            best_matched = matched
            best_offset = offset
    print('==== TỰ ĐỘNG DÒ TIMEZONE/OFFSET ===')
    for offset in offsets:
        print(f'Offset {offset:+}h: matched {offset_results[offset]}/{len(trade_df)}')
    print(f'==> Offset khớp nhiều nhất: {best_offset:+}h ({best_matched}/{len(trade_df)} trade)')
    if best_matched == 0:
        print('❌ Không khớp được trade nào với candle! Kiểm tra lại symbol, timeframe, hoặc dữ liệu candle.')
    elif best_matched < len(trade_df):
        print('⚠️ Một số trade vẫn bị thiếu nến. Có thể dữ liệu candle bị thiếu hoặc lệch thêm timezone.')
    else:
        print('✅ Đã khớp đủ nến cho toàn bộ trade với offset này.')

if __name__ == '__main__':
    # Đọc tradelist
    trade_df = load_tradelist(TRADELIST_FILE)
    if trade_df is None:
        exit(1)
    # Ưu tiên đọc candle từ DB nếu có, nếu không thì từ file CSV
    if os.path.exists(CANDLE_DB):
        print(f'Đang dùng database: {CANDLE_DB} | symbol: {CANDLE_SYMBOL} | timeframe: {CANDLE_TIMEFRAME}')
        candle_df = load_candle_db(CANDLE_DB, CANDLE_SYMBOL, CANDLE_TIMEFRAME)
    elif os.path.exists(CANDLE_FILE):
        print(f'Đang dùng file candle: {CANDLE_FILE}')
        candle_df = load_candle_csv(CANDLE_FILE)
    else:
        print('❌ Không tìm thấy nguồn dữ liệu candle!')
        exit(1)
    if candle_df is None:
        exit(1)
    # Kiểm tra từng trade
    check_trades_vs_candles(trade_df, candle_df)
