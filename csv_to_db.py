#!/usr/bin/env python3
"""
📊 CSV to Database Migration Tool
Chuyển đổi file CSV nến từ thư mục candles/ vào SQLite database
"""

import os
import sys
import pandas as pd
import glob
import re
from datetime import datetime
from candlestick_db import init_db, insert_candles, get_candles
import sqlite3

def parse_csv_filename(filename):
    """Parse filename to extract symbol and timeframe"""
    # BINANCE_SYMBOL.P, timeframe.csv or BINANCE_SYMBOL, timeframe.csv
    match = re.match(r'BINANCE_([A-Z]+)\.?P?,?\s*(\d+)\.csv', filename)
    if match:
        symbol = f"BINANCE_{match.group(1)}"
        timeframe = f"{match.group(2)}m"  # Add 'm' suffix for minutes
        return symbol, timeframe
    return None, None

def convert_csv_to_timestamp(date_str):
    """Convert various date formats to timestamp"""
    # Common formats in trading CSV files
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y.%m.%d %H:%M:%S', 
        '%m/%d/%Y %H:%M',
        '%d/%m/%Y %H:%M',
        '%Y-%m-%d %H:%M',
        '%d.%m.%Y %H:%M',
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%m/%d/%Y'
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return int(dt.timestamp())
        except ValueError:
            continue
    
    # If all formats fail, try pandas
    try:
        dt = pd.to_datetime(date_str)
        return int(dt.timestamp())
    except:
        raise ValueError(f"Cannot parse date: {date_str}")

def read_candle_csv(file_path):
    """Read CSV file and return standardized DataFrame"""
    try:
        # Try different encodings and separators
        for encoding in ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']:
            try:
                for sep in [',', ';', '\t']:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding, sep=sep)
                        if len(df.columns) >= 5:  # Need at least OHLC + time
                            break
                    except:
                        continue
                if len(df.columns) >= 5:
                    break
            except:
                continue
        
        print(f"  📄 Read {len(df)} rows, columns: {list(df.columns)}")
        
        # Detect column mapping
        col_mapping = {}
        for col in df.columns:
            col_lower = col.lower().strip()
            
            # Date/Time column
            if any(x in col_lower for x in ['time', 'date', 'datetime', 'timestamp']):
                col_mapping['datetime'] = col
            # OHLCV columns
            elif 'open' in col_lower and 'time' not in col_lower:
                col_mapping['open'] = col
            elif 'high' in col_lower:
                col_mapping['high'] = col
            elif 'low' in col_lower:
                col_mapping['low'] = col
            elif 'close' in col_lower:
                col_mapping['close'] = col
            elif 'volume' in col_lower or 'vol' in col_lower:
                col_mapping['volume'] = col
        
        # If no datetime column found, try first column
        if 'datetime' not in col_mapping:
            col_mapping['datetime'] = df.columns[0]
        
        # If no volume column, use 0
        if 'volume' not in col_mapping:
            df['volume'] = 0
            col_mapping['volume'] = 'volume'
        
        print(f"  🔍 Column mapping: {col_mapping}")
        
        # Create standardized DataFrame
        try:
            result_df = pd.DataFrame({
                'open_time': df[col_mapping['datetime']],
                'open': pd.to_numeric(df[col_mapping['open']], errors='coerce'),
                'high': pd.to_numeric(df[col_mapping['high']], errors='coerce'),
                'low': pd.to_numeric(df[col_mapping['low']], errors='coerce'),
                'close': pd.to_numeric(df[col_mapping['close']], errors='coerce'),
                'volume': pd.to_numeric(df[col_mapping['volume']], errors='coerce')
            })
        except Exception as e:
            print(f"  ❌ Error mapping columns: {e}")
            return None
        
        # Convert datetime to timestamp
        if not pd.api.types.is_numeric_dtype(result_df['open_time']):
            try:
                result_df['open_time'] = result_df['open_time'].apply(convert_csv_to_timestamp)
            except Exception as e:
                print(f"  ❌ Error converting timestamps: {e}")
                return None
        
        # Remove invalid rows
        result_df = result_df.dropna()
        
        print(f"  ✅ Processed {len(result_df)} valid rows")
        return result_df
        
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return None

def migrate_csv_to_db():
    """Main migration function"""
    print("🚀 Starting CSV to Database Migration...")
    
    # Initialize database
    init_db()
    
    # Get all CSV files from candles directory
    candles_dir = 'candles'
    if not os.path.exists(candles_dir):
        print(f"❌ Directory {candles_dir} not found!")
        return
    
    csv_files = glob.glob(os.path.join(candles_dir, '*.csv'))
    print(f"📁 Found {len(csv_files)} CSV files in {candles_dir}/")
    
    success_count = 0
    error_count = 0
    
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        print(f"\n📊 Processing: {filename}")
        
        # Parse symbol and timeframe
        symbol, timeframe = parse_csv_filename(filename)
        if not symbol or not timeframe:
            print(f"  ⚠️ Cannot parse filename: {filename}")
            error_count += 1
            continue
        
        print(f"  📈 Symbol: {symbol}, Timeframe: {timeframe}")
        
        # Read CSV
        df = read_candle_csv(file_path)
        if df is None or df.empty:
            print(f"  ❌ Failed to read or empty file")
            error_count += 1
            continue
        
        # Convert to tuples for database insertion
        try:
            candles_data = []
            for _, row in df.iterrows():
                candles_data.append((
                    int(row['open_time']),
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    float(row['volume'])
                ))
            
            # Insert into database
            insert_candles(symbol, timeframe, candles_data)
            print(f"  ✅ Successfully inserted {len(candles_data)} candles")
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ Error inserting to database: {e}")
            error_count += 1
    
    print(f"\n🎉 Migration completed!")
    print(f"✅ Success: {success_count} files")
    print(f"❌ Errors: {error_count} files")
    
    # Show database status
    show_database_status()

def show_database_status():
    """Show current database contents"""
    print(f"\n📊 DATABASE STATUS:")
    
    try:
        conn = sqlite3.connect('candlestick_data.db')
        cursor = conn.cursor()
        
        # Get all symbols and timeframes
        cursor.execute("""
            SELECT symbol, timeframe, COUNT(*) as candle_count, 
                   MIN(open_time) as first_candle, 
                   MAX(open_time) as last_candle
            FROM candlestick_data 
            GROUP BY symbol, timeframe 
            ORDER BY symbol, timeframe
        """)
        
        results = cursor.fetchall()
        
        if results:
            print("📈 Symbols in database:")
            for row in results:
                symbol, timeframe, count, first_time, last_time = row
                first_date = datetime.fromtimestamp(first_time).strftime('%Y-%m-%d %H:%M')
                last_date = datetime.fromtimestamp(last_time).strftime('%Y-%m-%d %H:%M')
                print(f"   {symbol} {timeframe}: {count:,} candles ({first_date} → {last_date})")
        else:
            print("   (Empty database)")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")

def test_database_read(symbol, timeframe):
    """Test reading data from database"""
    print(f"\n🧪 Testing database read for {symbol} {timeframe}:")
    
    try:
        df = get_candles(symbol, timeframe)
        if not df.empty:
            print(f"✅ Successfully read {len(df)} candles")
            print(f"📊 Sample data:")
            print(df.head())
        else:
            print("❌ No data found")
    except Exception as e:
        print(f"❌ Error reading from database: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("📊 CSV TO DATABASE MIGRATION TOOL")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'status':
            show_database_status()
        elif sys.argv[1] == 'test':
            if len(sys.argv) >= 4:
                test_database_read(sys.argv[2], sys.argv[3])
            else:
                print("Usage: python csv_to_db.py test SYMBOL TIMEFRAME")
        else:
            print("Available commands: migrate (default), status, test")
    else:
        migrate_csv_to_db()