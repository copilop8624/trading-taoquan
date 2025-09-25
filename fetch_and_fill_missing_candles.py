import os
import glob
import pandas as pd
from datetime import datetime, timedelta
from binance.client import Client
import time

# --- CONFIG ---
TRADLIST_DIR = 'tradelist'
CANDLE_DIR = 'candles'
API_KEY = os.getenv('BINANCE_API_KEY', '')
API_SECRET = os.getenv('BINANCE_API_SECRET', '')

# --- Helper: Parse timeframe string to Binance interval ---
TIMEFRAME_MAP = {
    '30m': Client.KLINE_INTERVAL_30MINUTE,
    '60m': Client.KLINE_INTERVAL_1HOUR,
    '1h': Client.KLINE_INTERVAL_1HOUR,
    '1d': Client.KLINE_INTERVAL_1DAY,
    '15m': Client.KLINE_INTERVAL_15MINUTE,
    '5m': Client.KLINE_INTERVAL_5MINUTE,
    '4h': Client.KLINE_INTERVAL_4HOUR,
    '1m': Client.KLINE_INTERVAL_1MINUTE,
}

def parse_tradelist_info(filename):
    # Try to extract symbol and timeframe from filename
    base = os.path.basename(filename)
    for tf in TIMEFRAME_MAP:
        if tf in base.lower():
            symbol = base.split('_')[0].replace('BINANCE_', '').replace('.csv','').upper()
            return symbol, tf
    # fallback: try to parse from content
    return None, None

def get_tradelist_min_time(filepath):
    df = pd.read_csv(filepath)
    for col in ['Date/Time', 'date', 'datetime', 'Date']:
        if col in df.columns:
            dt_col = col
            break
    else:
        raise Exception(f'No datetime column found in {filepath}')
    # parse to datetime
    min_time = pd.to_datetime(df[dt_col], errors='coerce').min()
    return min_time

def get_candle_min_time(filepath):
    df = pd.read_csv(filepath)
    if 'time' in df.columns:
        min_time = pd.to_datetime(df['time'], errors='coerce').min()
        return min_time
    return None

def fetch_binance_klines(symbol, interval, start_time, end_time):
    client = Client(API_KEY, API_SECRET)
    all_klines = []
    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(end_time.timestamp() * 1000)
    while start_ts < end_ts:
        klines = client.get_historical_klines(symbol, interval, start_ts, min(start_ts + 1000*1800, end_ts))
        if not klines:
            break
        all_klines.extend(klines)
        last = klines[-1][0]
        start_ts = last + 1800*1000  # 30m in ms
        time.sleep(0.2)
    return all_klines

def main():
    tradelist_files = glob.glob(os.path.join(TRADLIST_DIR, '*.csv'))
    for tradelist_file in tradelist_files:
        symbol, tf = parse_tradelist_info(tradelist_file)
        if not symbol or not tf:
            print(f'Skip {tradelist_file}: cannot parse symbol/timeframe')
            continue
        print(f'Processing {tradelist_file} | Symbol: {symbol}, TF: {tf}')
        min_trade_time = get_tradelist_min_time(tradelist_file)
        candle_file = os.path.join(CANDLE_DIR, f'BINANCE_{symbol}, {tf.replace("m","0")}.csv')
        if not os.path.exists(candle_file):
            print(f'No candle file for {symbol} {tf}, skip')
            continue
        min_candle_time = get_candle_min_time(candle_file)
        if min_candle_time is None or min_candle_time > min_trade_time:
            print(f'Need to fetch candles for {symbol} {tf}: {min_trade_time} -> {min_candle_time}')
            # Fetch and append
            interval = TIMEFRAME_MAP[tf]
            klines = fetch_binance_klines(symbol, interval, min_trade_time, min_candle_time)
            if klines:
                # Convert to DataFrame and append to file
                df_new = pd.DataFrame(klines, columns=[
                    'open_time','open','high','low','close','volume','close_time','quote_asset_volume','number_of_trades','taker_buy_base','taker_buy_quote','ignore'])
                df_new['time'] = pd.to_datetime(df_new['open_time'], unit='ms')
                df_new = df_new[['time','open','high','low','close','volume']]
                df_new.to_csv(candle_file, mode='a', header=False, index=False)
                print(f'Appended {len(df_new)} candles to {candle_file}')
            else:
                print(f'No candles fetched for {symbol} {tf}')
        else:
            print(f'No missing candles for {symbol} {tf}')

if __name__ == '__main__':
    main()
