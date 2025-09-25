"""
Data Manager - Layer 1: Data Management
Quản lý dữ liệu nến và cache, chuẩn hóa format, tích hợp với SQLite DB
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sqlite3
from candlestick_db import get_connection, init_db, insert_candles, get_candles, resample_candles
import glob
import re

class DataManager:
    def auto_fill_all_missing_candles_from_tradelists(self, tradelist_dir='tradelist', candle_dir='candles', api_key=None, api_secret=None):
        """
        Scan all tradelist CSVs, determine required time ranges for each symbol/timeframe,
        check for missing candles, fetch from Binance, and fill gaps in DB/CSV.
        """
        import glob
        import pandas as pd
        from datetime import datetime
        try:
            from binance.client import Client
        except ImportError:
            print("python-binance not installed. Please install it to use this feature.")
            return
        api_key = api_key or os.getenv('BINANCE_API_KEY', '')
        api_secret = api_secret or os.getenv('BINANCE_API_SECRET', '')
        TIMEFRAME_MAP = {
            '5': Client.KLINE_INTERVAL_5MINUTE,
            '15': Client.KLINE_INTERVAL_15MINUTE,
            '30': Client.KLINE_INTERVAL_30MINUTE,
            '60': Client.KLINE_INTERVAL_1HOUR,
            '240': Client.KLINE_INTERVAL_4HOUR,
            '1d': Client.KLINE_INTERVAL_1DAY,
        }
        def parse_tradelist_info(filename):
            base = os.path.basename(filename)
            for tf in TIMEFRAME_MAP:
                if tf in base:
                    symbol = base.split('_')[0].replace('BINANCE_', '').replace('.csv','').upper()
                    return symbol, tf
            return None, None
        def get_tradelist_min_time(filepath):
            df = pd.read_csv(filepath)
            for col in ['Date/Time', 'date', 'datetime', 'Date']:
                if col in df.columns:
                    dt_col = col
                    break
            else:
                raise Exception(f'No datetime column found in {filepath}')
            min_time = pd.to_datetime(df[dt_col], errors='coerce').min()
            return min_time
        def fetch_binance_klines(symbol, interval, start_time, end_time):
            client = Client(api_key, api_secret)
            all_klines = []
            start_ts = int(start_time.timestamp() * 1000)
            end_ts = int(end_time.timestamp() * 1000)
            while start_ts < end_ts:
                klines = client.get_historical_klines(symbol, interval, start_ts, min(start_ts + 1000*1800, end_ts))
                if not klines:
                    break
                all_klines.extend(klines)
                last = klines[-1][0]
                start_ts = last + 1800*1000
                import time; time.sleep(0.2)
            return all_klines
        tradelist_files = glob.glob(os.path.join(tradelist_dir, '*.csv'))
        for tradelist_file in tradelist_files:
            symbol, tf = parse_tradelist_info(tradelist_file)
            if not symbol or not tf:
                print(f'Skip {tradelist_file}: cannot parse symbol/timeframe')
                continue
            print(f'Processing {tradelist_file} | Symbol: {symbol}, TF: {tf}')
            min_trade_time = get_tradelist_min_time(tradelist_file)
            # Check DB for earliest candle
            df_candles = self.load_candle_data(symbol, tf)
            if df_candles.empty or df_candles["time"].min() > min_trade_time:
                min_candle_time = df_candles["time"].min() if not df_candles.empty else datetime.now()
                print(f'Need to fetch candles for {symbol} {tf}: {min_trade_time} -> {min_candle_time}')
                interval = TIMEFRAME_MAP[tf]
                klines = fetch_binance_klines(symbol, interval, min_trade_time, min_candle_time)
                if klines:
                    df_new = pd.DataFrame(klines, columns=[
                        'open_time','open','high','low','close','volume','close_time','quote_asset_volume','number_of_trades','taker_buy_base','taker_buy_quote','ignore'])
                    df_new['time'] = pd.to_datetime(df_new['open_time'], unit='ms')
                    df_new = df_new[['time','open','high','low','close','volume']]
                    # Append to DB
                    self._cache_to_database(symbol, tf, df_new)
                    print(f'Appended {len(df_new)} candles to DB for {symbol} {tf}')
                else:
                    print(f'No candles fetched for {symbol} {tf}')
            else:
                print(f'No missing candles for {symbol} {tf}')
    """
    Centralized data management for candle data
    - Load from CSV files (existing BINANCE_* files)
    - Cache in SQLite database
    - Normalize formats and timeframes
    - Provide unified API for backtest engine
    """
    
    def __init__(self, data_directory: str = "."):
        self.data_directory = data_directory
        self.supported_exchanges = ["BINANCE"]
        self.supported_timeframes = ["5", "30", "60", "240", "1d"]
        
        # Initialize database
        init_db()
        
        # Auto-discover available data files
        self._discover_data_files()
    
    def _discover_data_files(self) -> Dict[str, Dict[str, str]]:
        """Auto-discover candle CSV files in workspace"""
        self.available_data = {}
        
        # Search in current directory and candles subfolder
        search_paths = [
            self.data_directory,
            os.path.join(self.data_directory, "candles"),
            os.path.join(self.data_directory, "data_organized", "candles")
        ]
        
        # Pattern: BINANCE_SYMBOL, TIMEFRAME.csv or BINANCE_SYMBOL.P, TIMEFRAME.csv
        patterns = [
            "BINANCE_*.csv",
            "*.csv"
        ]
        
        for search_path in search_paths:
            if os.path.exists(search_path):
                for pattern in patterns:
                    files = glob.glob(os.path.join(search_path, pattern))
                    for file_path in files:
                        filename = os.path.basename(file_path)
                        symbol_info = self._parse_filename(filename)
                        if symbol_info:
                            symbol, timeframe, exchange = symbol_info
                            key = f"{exchange}_{symbol}"
                            if key not in self.available_data:
                                self.available_data[key] = {}
                            self.available_data[key][timeframe] = file_path
        
        print(f"📊 Discovered {len(self.available_data)} symbols with data:")
        for symbol, timeframes in self.available_data.items():
            tf_list = list(timeframes.keys())
            print(f"   {symbol}: {tf_list}")
        
        return self.available_data
    
    def _parse_filename(self, filename: str) -> Optional[Tuple[str, str, str]]:
        """Parse filename to extract symbol, timeframe, exchange"""
        # BINANCE_BTCUSDT, 60.csv
        # BINANCE_BTCUSDT.P, 30.csv  
        patterns = [
            r"BINANCE_([A-Z]+USDT)\.?P?, (\d+)\.csv",
            r"BINANCE_([A-Z]+USDT), (\d+)\.csv",
            r"([A-Z]+USDT)\.?P?[-_](\d+)\.csv"
        ]
        
        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                symbol = match.group(1)
                timeframe = match.group(2)
                exchange = "BINANCE"
                return (symbol, timeframe, exchange)
        
        return None
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols"""
        return list(self.available_data.keys())
    
    def get_available_timeframes(self, symbol: str) -> List[str]:
        """Get available timeframes for a symbol"""
        if symbol in self.available_data:
            return list(self.available_data[symbol].keys())
        return []
    
    def load_candle_data(self, symbol: str, timeframe: str, 
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        force_reload: bool = False) -> pd.DataFrame:
        """
        Load candle data with caching
        Priority: DB cache -> CSV file -> empty DataFrame
        """
        exchange = "BINANCE"
        symbol_key = f"{exchange}_{symbol}"
        
        # Try to load from database first (if not forcing reload)
        if not force_reload:
            try:
                start_ts = int(start_time.timestamp()) if start_time else None
                end_ts = int(end_time.timestamp()) if end_time else None
                
                df_cached = get_candles(symbol, timeframe, start_ts, end_ts)
                if len(df_cached) > 0:
                    # Convert open_time back to datetime
                    df_cached['time'] = pd.to_datetime(df_cached['open_time'], unit='s')
                    df_cached = df_cached.drop('open_time', axis=1)
                    df_cached = df_cached[['time', 'open', 'high', 'low', 'close', 'volume']]
                    print(f"📈 Loaded {len(df_cached)} candles from DB: {symbol} {timeframe}m")
                    return df_cached
            except Exception as e:
                print(f"⚠️ DB load failed for {symbol} {timeframe}: {e}")
        
        # Load from CSV file
        if symbol_key in self.available_data and timeframe in self.available_data[symbol_key]:
            file_path = self.available_data[symbol_key][timeframe]
            try:
                df = self._load_csv_file(file_path)
                if len(df) > 0:
                    # Cache to database
                    self._cache_to_database(symbol, timeframe, df)
                    print(f"📈 Loaded {len(df)} candles from CSV: {symbol} {timeframe}m")
                    return df
            except Exception as e:
                print(f"❌ Failed to load CSV {file_path}: {e}")
        
        print(f"⚠️ No data found for {symbol} {timeframe}m")
        return pd.DataFrame(columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    
    def _load_csv_file(self, file_path: str) -> pd.DataFrame:
        """Load and normalize CSV candle file"""
        try:
            # Try comma separator first
            df = pd.read_csv(file_path, sep=",")
            if len(df.columns) == 1:
                df = pd.read_csv(file_path, sep="\t")
        except Exception:
            df = pd.read_csv(file_path, sep="\t")
        
        # Normalize column names
        df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
        
        # Map common column name variations
        column_mapping = {
            'd': 'time',
            'timestamp': 'time',
            'datetime': 'time',
            'date': 'time'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df.rename(columns={old_col: new_col}, inplace=True)
        
        # Ensure required columns exist
        required_cols = ['time', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Normalize datetime
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
        if df['time'].isna().all():
            raise ValueError("Could not parse time column")
        
        # Remove timezone info for consistency
        if df['time'].dt.tz is not None:
            df['time'] = df['time'].dt.tz_localize(None)
        
        # Convert price/volume columns to numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove rows with NaN values
        df = df.dropna()
        
        # Sort by time
        df = df.sort_values('time').reset_index(drop=True)
        
        return df[required_cols]
    
    def _cache_to_database(self, symbol: str, timeframe: str, df: pd.DataFrame):
        """Cache candle data to SQLite database"""
        try:
            # Convert DataFrame to format expected by database
            candles_data = []
            for _, row in df.iterrows():
                candles_data.append((
                    int(row['time'].timestamp()),
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    float(row['volume'])
                ))
            
            insert_candles(symbol, timeframe, candles_data)
            print(f"💾 Cached {len(candles_data)} candles to DB: {symbol} {timeframe}m")
            
        except Exception as e:
            print(f"⚠️ Failed to cache to DB: {e}")
    
    def get_symbol_summary(self) -> Dict:
        """Get summary of all available data"""
        summary = {
            'total_symbols': len(self.available_data),
            'symbols': {},
            'timeframes_available': set()
        }
        
        for symbol_key, timeframes in self.available_data.items():
            symbol = symbol_key.replace('BINANCE_', '')
            summary['symbols'][symbol] = {
                'timeframes': list(timeframes.keys()),
                'files': list(timeframes.values())
            }
            summary['timeframes_available'].update(timeframes.keys())
        
        summary['timeframes_available'] = sorted(summary['timeframes_available'])
        return summary
    
    def validate_data_integrity(self, symbol: str, timeframe: str) -> Dict:
        """Validate data integrity and completeness"""
        df = self.load_candle_data(symbol, timeframe)
        
        if len(df) == 0:
            return {'status': 'error', 'message': 'No data available'}
        
        # Check for data gaps
        df_sorted = df.sort_values('time')
        time_diffs = df_sorted['time'].diff().dt.total_seconds() / 60  # minutes
        expected_interval = int(timeframe)
        
        # Allow 10% tolerance for interval
        tolerance = expected_interval * 0.1
        irregular_intervals = time_diffs[(time_diffs > expected_interval + tolerance) | 
                                       (time_diffs < expected_interval - tolerance)]
        
        validation = {
            'status': 'ok',
            'total_records': len(df),
            'date_range': {
                'start': df['time'].min().strftime('%Y-%m-%d %H:%M'),
                'end': df['time'].max().strftime('%Y-%m-%d %H:%M')
            },
            'irregular_intervals': len(irregular_intervals),
            'missing_data_points': len(irregular_intervals),
            'data_quality_score': max(0, 100 - (len(irregular_intervals) / len(df) * 100))
        }
        
        return validation

# Global instance
data_manager = DataManager()

def get_data_manager() -> DataManager:
    """Get global data manager instance"""
    return data_manager

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DataManager CLI")
    parser.add_argument('--fill-missing', action='store_true', help='Auto-fill all missing candles from tradelists using Binance API')
    args = parser.parse_args()

    dm = DataManager()
    if args.fill_missing:
        dm.auto_fill_all_missing_candles_from_tradelists()
    else:
        print("\n=== Data Manager Test ===")
        summary = dm.get_symbol_summary()
        print(f"Available symbols: {summary['total_symbols']}")
        print(f"Timeframes: {summary['timeframes_available']}")
        for symbol_key in list(dm.available_data.keys())[:2]:
            symbol = symbol_key.replace('BINANCE_', '')
            timeframes = dm.get_available_timeframes(symbol_key)
            for tf in timeframes[:1]:
                print(f"\n--- Testing {symbol} {tf}m ---")
                df = dm.load_candle_data(symbol, tf)
                if len(df) > 0:
                    validation = dm.validate_data_integrity(symbol, tf)
                    print(f"Records: {validation['total_records']}")
                    print(f"Date range: {validation['date_range']['start']} to {validation['date_range']['end']}")
                    print(f"Quality score: {validation['data_quality_score']:.1f}%")