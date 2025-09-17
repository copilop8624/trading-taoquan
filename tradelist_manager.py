"""
Tradelist Manager - Layer 1: Data Management
Quản lý tradelist, format detection, standardization
Hỗ trợ tất cả format: BTC legacy, ACEUSDT, BOME, và các format mới
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
import io
import os
import re

class TradelistManager:
    """
    Centralized tradelist management
    - Auto-detect format (BTC legacy, ACEUSDT TradingView, BOME)
    - Standardize to common DataFrame format
    - Validate and clean data
    - Support batch processing
    """
    
    def __init__(self):
        self.supported_formats = ['BTC_LEGACY', 'ACEUSDT_TV', 'BOME_TV', 'GENERIC']
        self.standard_columns = ['trade', 'type', 'date', 'price', 'side']
        
    def detect_format(self, df: pd.DataFrame) -> str:
        """Auto-detect tradelist format based on columns and data patterns"""
        
        # Clean column names for detection
        cols = [col.strip().lower().replace(' ', '_').replace('/', '_').replace('#', '') for col in df.columns]
        
        # ACEUSDT TradingView format detection
        aceusdt_indicators = [
            'signal' in cols,
            'pl_usdt' in cols or 'p&l_usdt' in cols,
            any('qty' in col or 'quantity' in col for col in cols),
            'date_time' in cols or 'datetime' in cols
        ]
        
        if sum(aceusdt_indicators) >= 2:
            return 'ACEUSDT_TV'
        
        # BOME format detection (TradingView but different characteristics)
        bome_indicators = [
            'signal' in cols,
            any('price' in col for col in cols),
            self._has_small_prices(df)  # BOME has very small prices (~0.009)
        ]
        
        if sum(bome_indicators) >= 2:
            return 'BOME_TV'
        
        # BTC Legacy format detection
        btc_indicators = [
            'trade' in cols or 'trade_' in cols,
            'type' in cols,
            'date' in cols,
            'price' in cols or 'price_usdt' in cols,
            not any('signal' in col for col in cols)  # No signal column
        ]
        
        if sum(btc_indicators) >= 3:
            return 'BTC_LEGACY'
        
        return 'GENERIC'
    
    def _has_small_prices(self, df: pd.DataFrame) -> bool:
        """Check if DataFrame contains very small prices (BOME characteristic)"""
        price_cols = [col for col in df.columns if 'price' in col.lower()]
        if not price_cols:
            return False
        
        try:
            for col in price_cols:
                prices = pd.to_numeric(df[col].head(10), errors='coerce').dropna()
                if len(prices) > 0 and prices.mean() < 0.1:
                    return True
        except:
            pass
        
        return False
    
    def load_from_content(self, content: str) -> pd.DataFrame:
        """Load tradelist from CSV content string"""
        try:
            # Try comma separator first
            df = pd.read_csv(io.StringIO(content), sep=",")
            if len(df.columns) == 1:
                df = pd.read_csv(io.StringIO(content), sep="\t")
        except Exception:
            df = pd.read_csv(io.StringIO(content), sep="\t")
        
        return self.standardize_tradelist(df)
    
    def load_from_file(self, file_path: str) -> pd.DataFrame:
        """Load tradelist from CSV file"""
        try:
            # Try comma separator first
            df = pd.read_csv(file_path, sep=",")
            if len(df.columns) == 1:
                df = pd.read_csv(file_path, sep="\t")
        except Exception:
            df = pd.read_csv(file_path, sep="\t")
        
        return self.standardize_tradelist(df)
    
    def standardize_tradelist(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize tradelist to common format regardless of input format"""
        
        if len(df) == 0:
            return self._create_empty_standard_df()
        
        # Clean column names
        df.columns = [col.strip().lower().replace(' ', '_').replace('/', '_').replace('#', '').replace('&', '') for col in df.columns]
        
        # Detect format
        format_type = self.detect_format(df)
        print(f"🔍 Detected format: {format_type}")
        
        # Apply format-specific processing
        if format_type == 'ACEUSDT_TV':
            return self._process_aceusdt_format(df)
        elif format_type == 'BOME_TV':
            return self._process_bome_format(df)
        elif format_type == 'BTC_LEGACY':
            return self._process_btc_legacy_format(df)
        else:
            return self._process_generic_format(df)
    
    def _process_aceusdt_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process ACEUSDT TradingView format"""
        
        # Column mapping for ACEUSDT
        column_map = {
            'trade_': 'trade',
            'trade_number': 'trade', 
            'date_time': 'date',
            'datetime': 'date',
            'price_usdt': 'price'
        }
        
        df.rename(columns=column_map, inplace=True)
        
        # Validate required columns
        required = ['trade', 'type', 'signal', 'date', 'price']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"ACEUSDT format missing columns: {missing}")
        
        # Create side column from signal
        df['side'] = df['signal'].apply(self._extract_side_from_signal)
        
        # Normalize datetime (ACEUSDT uses YYYY-MM-DD HH:MM format)
        df['date'] = df['date'].apply(self._normalize_aceusdt_date)
        
        # Normalize price
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        
        # Filter entry/exit rows only
        df = df[df['type'].str.lower().str.contains('entry|exit', na=False)]
        
        return self._finalize_standard_format(df)
    
    def _process_bome_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process BOME TradingView format"""
        
        # Similar to ACEUSDT but with different characteristics
        column_map = {
            'trade_': 'trade',
            'trade_number': 'trade',
            'date_time': 'date',
            'datetime': 'date'
        }
        
        df.rename(columns=column_map, inplace=True)
        
        # Find price column
        price_cols = [col for col in df.columns if 'price' in col.lower()]
        if price_cols:
            df['price'] = df[price_cols[0]]
        
        # Create side column from signal if available
        if 'signal' in df.columns:
            df['side'] = df['signal'].apply(self._extract_side_from_signal)
        else:
            df['side'] = 'LONG'  # Default assumption
        
        # Normalize datetime
        df['date'] = df['date'].apply(self._normalize_aceusdt_date)
        
        # Normalize price
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        
        # Filter entry/exit rows
        if 'type' in df.columns:
            df = df[df['type'].str.lower().str.contains('entry|exit', na=False)]
        
        return self._finalize_standard_format(df)
    
    def _process_btc_legacy_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process BTC legacy format"""
        
        # Column mapping for BTC legacy
        column_map = {
            'trade_': 'trade',
            'trade_number': 'trade',
            'price_usdt': 'price'
        }
        
        df.rename(columns=column_map, inplace=True)
        
        # Validate required columns
        required = ['trade', 'type', 'date', 'price']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"BTC legacy format missing columns: {missing}")
        
        # Extract side from type column (e.g., "Long Entry", "Short Exit")
        df['side'] = df['type'].apply(self._extract_side_from_type)
        
        # Normalize datetime (BTC uses MM/DD/YYYY HH:MM format)
        df['date'] = df['date'].apply(self._normalize_btc_legacy_date)
        
        # Normalize price (remove commas, quotes)
        df['price'] = df['price'].astype(str).str.replace(',', '').str.replace('"', '')
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        
        # Filter entry/exit rows
        df = df[df['type'].str.lower().str.contains('entry|exit', na=False)]
        
        return self._finalize_standard_format(df)
    
    def _process_generic_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process generic/unknown format with best effort"""
        
        # Try to map common variations
        column_map = {}
        
        # Find trade number column
        trade_cols = [col for col in df.columns if 'trade' in col.lower()]
        if trade_cols:
            column_map[trade_cols[0]] = 'trade'
        
        # Find price column
        price_cols = [col for col in df.columns if 'price' in col.lower()]
        if price_cols:
            column_map[price_cols[0]] = 'price'
        
        # Find date/time column
        date_cols = [col for col in df.columns if any(x in col.lower() for x in ['date', 'time'])]
        if date_cols:
            column_map[date_cols[0]] = 'date'
        
        df.rename(columns=column_map, inplace=True)
        
        # Set defaults for missing columns
        if 'type' not in df.columns:
            # Try to infer from other columns or set default
            df['type'] = 'Entry'  # Default
        
        if 'side' not in df.columns:
            df['side'] = 'LONG'  # Default
        
        if 'trade' not in df.columns:
            df['trade'] = range(1, len(df) + 1)  # Generate trade numbers
        
        # Basic datetime normalization
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        return self._finalize_standard_format(df)
    
    def _extract_side_from_signal(self, signal: str) -> str:
        """Extract LONG/SHORT from signal column"""
        if pd.isna(signal):
            return 'LONG'
        
        signal_str = str(signal).upper()
        if 'SHORT' in signal_str or 'SELL' in signal_str:
            return 'SHORT'
        else:
            return 'LONG'
    
    def _extract_side_from_type(self, type_str: str) -> str:
        """Extract LONG/SHORT from type column (BTC legacy)"""
        if pd.isna(type_str):
            return 'LONG'
        
        type_upper = str(type_str).upper()
        if 'SHORT' in type_upper:
            return 'SHORT'
        else:
            return 'LONG'
    
    def _normalize_aceusdt_date(self, date_str: str) -> pd.Timestamp:
        """Normalize ACEUSDT date format (YYYY-MM-DD HH:MM)"""
        try:
            dt = pd.to_datetime(date_str, format='%Y-%m-%d %H:%M', errors='coerce')
            if not pd.isna(dt):
                # Assume UTC for ACEUSDT format
                if dt.tz is None:
                    dt = dt.tz_localize('UTC').tz_localize(None)
                return dt
        except:
            pass
        
        # Fallback to auto-detect
        try:
            dt = pd.to_datetime(date_str, errors='coerce')
            if not pd.isna(dt):
                if dt.tz is None:
                    dt = dt.tz_localize('UTC').tz_localize(None)
                return dt
        except:
            pass
        
        return pd.NaT
    
    def _normalize_btc_legacy_date(self, date_str: str) -> pd.Timestamp:
        """Normalize BTC legacy date format (MM/DD/YYYY HH:MM)"""
        try:
            dt = pd.to_datetime(date_str, format='%m/%d/%Y %H:%M', errors='coerce')
            if not pd.isna(dt):
                # Assume Bangkok timezone for legacy BTC format
                if dt.tz is None:
                    dt = dt.tz_localize('Asia/Bangkok').tz_convert('UTC').tz_localize(None)
                return dt
        except:
            pass
        
        # Fallback to auto-detect
        try:
            dt = pd.to_datetime(date_str, errors='coerce')
            if not pd.isna(dt):
                if dt.tz is None:
                    dt = dt.tz_localize('UTC').tz_localize(None)
                return dt
        except:
            pass
        
        return pd.NaT
    
    def _finalize_standard_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """Finalize and validate standard format"""
        
        # Ensure all standard columns exist
        for col in self.standard_columns:
            if col not in df.columns:
                if col == 'side':
                    df[col] = 'LONG'  # Default
                else:
                    df[col] = None
        
        # Select only standard columns
        df = df[self.standard_columns].copy()
        
        # Remove rows with invalid data
        df = df.dropna(subset=['trade', 'date', 'price'])
        
        # Sort by trade number and date
        df = df.sort_values(['trade', 'date']).reset_index(drop=True)
        
        print(f"✅ Standardized tradelist: {len(df)} records")
        return df
    
    def _create_empty_standard_df(self) -> pd.DataFrame:
        """Create empty DataFrame with standard columns"""
        return pd.DataFrame(columns=self.standard_columns)
    
    def get_trade_pairs(self, df: pd.DataFrame) -> Tuple[List[Dict], List[str]]:
        """Convert standardized tradelist to trade pairs for backtest engine"""
        
        if len(df) == 0:
            return [], ["No trade data available"]
        
        pairs = []
        log = []
        
        for trade_num in df['trade'].unique():
            trade_group = df[df['trade'] == trade_num]
            
            # Find entry and exit
            entry_rows = trade_group[trade_group['type'].str.lower().str.contains('entry', na=False)]
            exit_rows = trade_group[trade_group['type'].str.lower().str.contains('exit', na=False)]
            
            if len(entry_rows) == 0:
                log.append(f"Trade {trade_num}: No entry found")
                continue
            
            if len(exit_rows) == 0:
                log.append(f"Trade {trade_num}: No exit found")
                continue
            
            entry = entry_rows.iloc[0]
            exit = exit_rows.iloc[0]
            
            # Create trade pair
            pair = {
                'num': trade_num,
                'entryDt': entry['date'],
                'exitDt': exit['date'],
                'side': entry['side'],
                'entryPrice': entry['price'],
                'exitPrice': exit['price']
            }
            
            pairs.append(pair)
        
        print(f"📊 Generated {len(pairs)} trade pairs from {len(df)} records")
        return pairs, log
    
    def validate_tradelist(self, df: pd.DataFrame) -> Dict:
        """Validate tradelist quality and completeness"""
        
        if len(df) == 0:
            return {'status': 'error', 'message': 'Empty tradelist'}
        
        issues = []
        warnings = []
        
        # Check for required columns
        missing_cols = [col for col in self.standard_columns if col not in df.columns]
        if missing_cols:
            issues.append(f"Missing columns: {missing_cols}")
        
        # Check for null values in critical columns
        for col in ['trade', 'date', 'price']:
            if col in df.columns:
                null_count = df[col].isna().sum()
                if null_count > 0:
                    warnings.append(f"{col}: {null_count} null values")
        
        # Check trade completeness (entry/exit pairs)
        trade_pairs, pair_log = self.get_trade_pairs(df)
        incomplete_trades = len(pair_log)
        if incomplete_trades > 0:
            warnings.append(f"{incomplete_trades} incomplete trades")
        
        # Check date range
        if 'date' in df.columns and not df['date'].isna().all():
            date_range = {
                'start': df['date'].min(),
                'end': df['date'].max(),
                'span_days': (df['date'].max() - df['date'].min()).days
            }
        else:
            date_range = None
            issues.append("No valid dates found")
        
        status = 'error' if issues else ('warning' if warnings else 'ok')
        
        return {
            'status': status,
            'total_records': len(df),
            'total_trades': len(df['trade'].unique()) if 'trade' in df.columns else 0,
            'complete_pairs': len(trade_pairs),
            'date_range': date_range,
            'issues': issues,
            'warnings': warnings
        }

# Global instance
tradelist_manager = TradelistManager()

def get_tradelist_manager() -> TradelistManager:
    """Get global tradelist manager instance"""
    return tradelist_manager

if __name__ == "__main__":
    # Test the tradelist manager
    tm = TradelistManager()
    
    print("\n=== Tradelist Manager Test ===")
    
    # Test with sample files if available
    test_files = [
        "sample_tradelist.csv",
        "60-tradelist-LONGSHORT.csv",
        "30-tradelist-BS4.csv"
    ]
    
    for filename in test_files:
        if os.path.exists(filename):
            print(f"\n--- Testing {filename} ---")
            try:
                df = tm.load_from_file(filename)
                validation = tm.validate_tradelist(df)
                
                print(f"Status: {validation['status']}")
                print(f"Records: {validation['total_records']}")
                print(f"Complete pairs: {validation['complete_pairs']}")
                
                if validation['warnings']:
                    print(f"Warnings: {validation['warnings']}")
                
                if validation['issues']:
                    print(f"Issues: {validation['issues']}")
                    
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    print("\nTest completed!")