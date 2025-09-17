#!/usr/bin/env python3
"""
🚀 Binance Data Fetcher
Fetch real-time candlestick data from Binance API and update database
"""

import requests
import time
import json
from datetime import datetime, timedelta
from candlestick_db import init_db, insert_candles, get_candles
import sqlite3

class BinanceFetcher:
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TradingBot/1.0'
        })
    
    def get_symbol_info(self, symbol):
        """Get symbol information from Binance"""
        try:
            url = f"{self.base_url}/exchangeInfo"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            for s in data['symbols']:
                if s['symbol'] == symbol.replace('BINANCE_', ''):
                    return s
            return None
        except Exception as e:
            print(f"❌ Error getting symbol info: {e}")
            return None
    
    def timeframe_to_binance_interval(self, timeframe):
        """Convert internal timeframe to Binance interval"""
        mapping = {
            '1m': '1m',
            '3m': '3m', 
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '60m': '1h',
            '240m': '4h',
            '1440m': '1d'
        }
        return mapping.get(timeframe, '1h')
    
    def fetch_klines(self, symbol, interval, start_time=None, end_time=None, limit=1000):
        """Fetch klines from Binance API"""
        try:
            # Remove BINANCE_ prefix for API call
            api_symbol = symbol.replace('BINANCE_', '')
            
            url = f"{self.base_url}/klines"
            params = {
                'symbol': api_symbol,
                'interval': interval,
                'limit': min(limit, 1000)  # Binance max is 1000
            }
            
            if start_time:
                params['startTime'] = int(start_time * 1000)  # Binance uses milliseconds
            if end_time:
                params['endTime'] = int(end_time * 1000)
            
            print(f"📡 Fetching {api_symbol} {interval} from Binance API...")
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            klines = response.json()
            
            # Convert to our format
            candles = []
            for k in klines:
                candles.append((
                    int(k[0]) // 1000,  # open_time (convert from ms to seconds)
                    float(k[1]),        # open
                    float(k[2]),        # high  
                    float(k[3]),        # low
                    float(k[4]),        # close
                    float(k[5])         # volume
                ))
            
            print(f"✅ Fetched {len(candles)} candles")
            return candles
            
        except Exception as e:
            print(f"❌ Error fetching klines: {e}")
            return []
    
    def get_last_candle_time(self, symbol, timeframe):
        """Get timestamp of last candle in database"""
        try:
            conn = sqlite3.connect('candlestick_data.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT MAX(open_time) FROM candlestick_data 
                WHERE symbol = ? AND timeframe = ?
            """, (symbol, timeframe))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result[0] else None
            
        except Exception as e:
            print(f"❌ Error getting last candle time: {e}")
            return None
    
    def update_symbol(self, symbol, timeframe, days_back=30):
        """Update a specific symbol/timeframe"""
        print(f"\n🔄 Updating {symbol} {timeframe}...")
        
        # Check if symbol exists on Binance
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            print(f"❌ Symbol {symbol} not found on Binance")
            return False
        
        # Convert timeframe to Binance interval
        interval = self.timeframe_to_binance_interval(timeframe)
        
        # Get last candle time from database
        last_time = self.get_last_candle_time(symbol, timeframe)
        
        if last_time:
            # Fetch from last candle + 1 interval
            start_time = last_time + 1
            print(f"📅 Updating from {datetime.fromtimestamp(start_time)}")
        else:
            # Fetch last N days if no data
            start_time = int((datetime.now() - timedelta(days=days_back)).timestamp())
            print(f"📅 Fetching last {days_back} days")
        
        # Fetch new data
        candles = self.fetch_klines(symbol, interval, start_time=start_time)
        
        if candles:
            # Insert into database
            try:
                insert_candles(symbol, timeframe, candles)
                print(f"✅ Updated {len(candles)} candles for {symbol} {timeframe}")
                return True
            except Exception as e:
                print(f"❌ Error inserting candles: {e}")
                return False
        else:
            print(f"⚠️ No new candles to update for {symbol} {timeframe}")
            return True
    
    def update_all_symbols(self):
        """Update all symbols in database"""
        print("🚀 Starting update for all symbols...")
        
        try:
            conn = sqlite3.connect('candlestick_data.db')
            cursor = conn.cursor()
            
            # Get all unique symbol/timeframe combinations
            cursor.execute("""
                SELECT DISTINCT symbol, timeframe FROM candlestick_data
                ORDER BY symbol, timeframe
            """)
            
            symbols = cursor.fetchall()
            conn.close()
            
            success_count = 0
            error_count = 0
            
            for symbol, timeframe in symbols:
                try:
                    if self.update_symbol(symbol, timeframe):
                        success_count += 1
                    else:
                        error_count += 1
                    
                    # Rate limiting - be nice to Binance API
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"❌ Error updating {symbol} {timeframe}: {e}")
                    error_count += 1
            
            print(f"\n🎉 Update completed!")
            print(f"✅ Success: {success_count}")
            print(f"❌ Errors: {error_count}")
            
        except Exception as e:
            print(f"❌ Error getting symbols from database: {e}")
    
    def add_new_symbol(self, symbol, timeframe, days_back=365):
        """Add a completely new symbol to database"""
        print(f"\n➕ Adding new symbol: {symbol} {timeframe}")
        
        # Check if already exists
        existing = get_candles(symbol, timeframe)
        if not existing.empty:
            print(f"⚠️ Symbol {symbol} {timeframe} already exists with {len(existing)} candles")
            return False
        
        # Fetch historical data
        interval = self.timeframe_to_binance_interval(timeframe)
        start_time = int((datetime.now() - timedelta(days=days_back)).timestamp())
        
        print(f"📅 Fetching {days_back} days of historical data...")
        
        all_candles = []
        current_start = start_time
        
        # Fetch in chunks (Binance limit is 1000 candles per request)
        while current_start < int(datetime.now().timestamp()):
            candles = self.fetch_klines(symbol, interval, start_time=current_start, limit=1000)
            
            if not candles:
                break
            
            all_candles.extend(candles)
            
            # Move to next chunk
            current_start = candles[-1][0] + 1
            
            # Rate limiting
            time.sleep(0.1)
        
        if all_candles:
            try:
                insert_candles(symbol, timeframe, all_candles)
                print(f"✅ Added {len(all_candles)} candles for new symbol {symbol} {timeframe}")
                return True
            except Exception as e:
                print(f"❌ Error inserting new symbol data: {e}")
                return False
        else:
            print(f"❌ No data found for {symbol} {timeframe}")
            return False

def main():
    """Main function with command line interface"""
    import sys
    
    init_db()
    fetcher = BinanceFetcher()
    
    if len(sys.argv) == 1:
        # Default: update all existing symbols
        fetcher.update_all_symbols()
    
    elif sys.argv[1] == 'update':
        if len(sys.argv) >= 4:
            # Update specific symbol
            symbol = sys.argv[2]
            timeframe = sys.argv[3]
            fetcher.update_symbol(symbol, timeframe)
        else:
            fetcher.update_all_symbols()
    
    elif sys.argv[1] == 'add':
        if len(sys.argv) >= 4:
            # Add new symbol
            symbol = sys.argv[2]
            timeframe = sys.argv[3]
            days = int(sys.argv[4]) if len(sys.argv) >= 5 else 365
            fetcher.add_new_symbol(symbol, timeframe, days)
        else:
            print("Usage: python binance_fetcher.py add SYMBOL TIMEFRAME [DAYS]")
    
    elif sys.argv[1] == 'status':
        # Show database status
        from csv_to_db import show_database_status
        show_database_status()
    
    else:
        print("""
🚀 Binance Data Fetcher

Commands:
  python binance_fetcher.py                           # Update all symbols
  python binance_fetcher.py update                    # Update all symbols  
  python binance_fetcher.py update SYMBOL TIMEFRAME   # Update specific symbol
  python binance_fetcher.py add SYMBOL TIMEFRAME [DAYS] # Add new symbol
  python binance_fetcher.py status                    # Show database status

Examples:
  python binance_fetcher.py update BINANCE_BTCUSDT 30m
  python binance_fetcher.py add BINANCE_ETHUSDT 1h 180
        """)

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 BINANCE DATA FETCHER")
    print("=" * 60)
    main()