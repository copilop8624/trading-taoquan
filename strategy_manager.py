"""
Strategy Manager - Quản lý Strategy có hệ thống
Workflow: TradingView CSV → Auto-detect → Organize → Database
"""

import os
import re
import pandas as pd
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class StrategyInfo:
    """Strategy information"""
    filename: str
    symbol: str
    timeframe: str
    strategy_name: str
    version: str
    upload_date: datetime
    file_path: str
    trade_count: int
    date_range: str
    metadata: Dict[str, Any]

class StrategyManager:
    """
    🎯 Strategy Management System
    
    Features:
    - Auto-detect symbol/timeframe/strategy từ filename
    - Systematic organization vào database
    - Multiple tradelist per symbol/strategy
    - Version control và metadata tracking
    """
    
    def __init__(self, db_path: str = "strategy_management.db"):
        self.db_path = db_path
        self.tradelist_dir = "tradelist"
        self.strategy_patterns = self._init_naming_patterns()
        self._init_database()
    
    def _init_naming_patterns(self) -> List[Dict]:
        """Initialize các patterns để detect strategy info từ filename"""
        return [
            # Pattern 1: SYMBOL_TIMEFRAME_STRATEGY_VERSION.csv
            {
                'pattern': r'^([A-Z]+USDT?)_(\d+[mhd]?)_([A-Z_]+)_v?(\d+)\.csv$',
                'groups': ['symbol', 'timeframe', 'strategy', 'version']
            },
            # Pattern 2: BINANCE_SYMBOLUSDT.P, TIMEFRAME.csv
            {
                'pattern': r'^BINANCE_([A-Z]+USDT?)\.P,?\s*(\d+)\.csv$',
                'groups': ['symbol', 'timeframe', None, None]
            },
            # Pattern 3: BINANCE_SYMBOLUSDT_TIMEFRAME_STRATEGY.csv
            {
                'pattern': r'^BINANCE_([A-Z]+USDT?)_(\d+[mh]?)_([A-Z_]+)\.csv$',
                'groups': ['symbol', 'timeframe', 'strategy', None]
            },
            # Pattern 4: TIMEFRAME-tradelist-STRATEGY.csv
            {
                'pattern': r'^(\d+)-tradelist-([A-Z_]+)\.csv$',
                'groups': [None, 'timeframe', 'strategy', None]
            },
            # Pattern 5: Any file with SYMBOL_TIMEFRAME_anything
            {
                'pattern': r'([A-Z]{3,8}USDT?)_(\d+[mh]?)_',
                'groups': ['symbol', 'timeframe', None, None]
            },
            # Pattern 6: tradelist_SYMBOL_TIMEFRAME
            {
                'pattern': r'tradelist_([A-Z]+USDT?)_(\d+[mh]?)',
                'groups': ['symbol', 'timeframe', None, None]
            },
            # Pattern 7: anything_SYMBOL_TIMEFRAME
            {
                'pattern': r'_([A-Z]{3,8}USDT?)_(\d+[mh]?)_?',
                'groups': ['symbol', 'timeframe', None, None]
            }
        ]
    
    def _init_database(self):
        """Initialize strategy management database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    version TEXT DEFAULT 'v1',
                    upload_date TIMESTAMP NOT NULL,
                    file_path TEXT NOT NULL,
                    trade_count INTEGER DEFAULT 0,
                    date_range TEXT DEFAULT '',
                    metadata_json TEXT DEFAULT '{}',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    UNIQUE(symbol, timeframe, strategy_name, version)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol_strategy ON strategies(symbol, strategy_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timeframe ON strategies(timeframe)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_upload_date ON strategies(upload_date)")
            
            conn.commit()
    
    def detect_strategy_info(self, filename: str) -> StrategyInfo:
        """
        🔍 Auto-detect strategy information từ filename
        
        Returns:
            StrategyInfo với symbol, timeframe, strategy_name, version
        """
        # Try each pattern
        for pattern_info in self.strategy_patterns:
            pattern = pattern_info['pattern']
            groups = pattern_info['groups']
            
            match = re.match(pattern, filename, re.IGNORECASE)
            if match:
                values = match.groups()
                
                # Extract values theo groups mapping
                symbol = None
                timeframe = None
                strategy_name = None
                version = "v1"
                
                for i, group_name in enumerate(groups):
                    if group_name and i < len(values) and values[i]:
                        if group_name == 'symbol':
                            symbol = values[i].upper()
                        elif group_name == 'timeframe':
                            timeframe = self._normalize_timeframe(values[i])
                        elif group_name == 'strategy':
                            strategy_name = values[i].upper()
                        elif group_name == 'version':
                            version = f"v{values[i]}"
                
                # Set defaults nếu missing
                if not symbol:
                    symbol = self._extract_symbol_fallback(filename)
                if not timeframe:
                    timeframe = self._extract_timeframe_fallback(filename)
                if not strategy_name:
                    strategy_name = self._generate_strategy_name(filename)
                
                return StrategyInfo(
                    filename=filename,
                    symbol=symbol,
                    timeframe=timeframe,
                    strategy_name=strategy_name,
                    version=version,
                    upload_date=datetime.now(),
                    file_path="",
                    trade_count=0,
                    date_range="",
                    metadata={}
                )
        
        # Fallback: use heuristics
        return self._fallback_detection(filename)
    
    def _normalize_timeframe(self, tf_str: str) -> str:
        """Normalize timeframe string"""
        tf_str = tf_str.lower().strip()
        
        # Convert common formats
        conversions = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '60m', '4h': '240m', '1d': '1440m',
            '60': '60m', '240': '240m', '1440': '1440m'
        }
        
        # Try direct conversion
        if tf_str in conversions:
            return conversions[tf_str]
        
        # Extract number và add 'm' if missing
        numbers = re.findall(r'\d+', tf_str)
        if numbers:
            return f"{numbers[0]}m"
        
        return "60m"  # default
    
    def _extract_symbol_fallback(self, filename: str) -> str:
        """Extract symbol using fallback method"""
        # Remove extension first
        name = filename.replace('.csv', '').replace('.CSV', '')
        
        # Look for crypto symbols patterns (more comprehensive)
        crypto_patterns = [
            # BINANCE_SYMBOLUSDT format
            r'BINANCE_([A-Z]+USDT?)',
            r'BINANCE_([A-Z]+)',
            # Direct symbol patterns
            r'(BTC|ETH|BNB|ADA|XRP|SOL|DOT|LINK|UNI|ATOM|AVAX|MATIC|DOGE|SHIB|LTC|BOME|PERP|SAGA|HBAR|NOT|PEPE|WIF|FLOKI)USDT?',
            # Symbol at beginning
            r'^([A-Z]{3,8})USDT?',
            # Symbol in filename
            r'([A-Z]{3,8})USDT?',
        ]
        
        for pattern in crypto_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                symbol = match.group(1).upper()
                # Add USDT if not present
                if not symbol.endswith('USDT'):
                    symbol += 'USDT'
                return symbol
        
        # Try to extract from common filename patterns
        # Like: strategy_SYMBOL_timeframe.csv
        parts = name.split('_')
        for part in parts:
            if len(part) >= 3 and part.isalpha():
                part_upper = part.upper()
                if not part_upper.endswith('USDT'):
                    part_upper += 'USDT'
                return part_upper
        
        # Last resort: check if filename contains any recognizable symbol
        known_symbols = ['BTC', 'ETH', 'BNB', 'ADA', 'XRP', 'SOL', 'DOT', 'LINK', 'UNI', 
                        'ATOM', 'AVAX', 'MATIC', 'DOGE', 'SHIB', 'LTC', 'BOME', 'PERP', 
                        'SAGA', 'HBAR', 'NOT', 'PEPE', 'WIF', 'FLOKI']
        
        name_upper = name.upper()
        for symbol in known_symbols:
            if symbol in name_upper:
                return symbol + 'USDT'
        
        return "BTCUSDT"  # final default
    
    def _extract_timeframe_fallback(self, filename: str) -> str:
        """Extract timeframe using fallback method"""
        # Look for timeframe patterns
        tf_patterns = [
            r'(\d+)[mh]',
            r'(\d+)[\s,-]',
            r'(\d+)\.csv'
        ]
        
        for pattern in tf_patterns:
            match = re.search(pattern, filename)
            if match:
                return self._normalize_timeframe(match.group(1))
        
        return "60m"  # default
    
    def _generate_strategy_name(self, filename: str) -> str:
        """Generate strategy name từ filename"""
        # Remove extension và common prefixes
        name = filename.replace('.csv', '').replace('BINANCE_', '')
        
        # Look for strategy keywords
        strategy_keywords = [
            'MACD', 'RSI', 'BOLLINGER', 'SMA', 'EMA', 'STOCH',
            'TREND', 'BREAKOUT', 'SCALP', 'SWING', 'LONG', 'SHORT',
            'TRADELIST', 'SIGNALS', 'ENTRY', 'EXIT'
        ]
        
        found_keywords = []
        name_upper = name.upper()
        for keyword in strategy_keywords:
            if keyword in name_upper:
                found_keywords.append(keyword)
        
        if found_keywords:
            return '_'.join(found_keywords[:2])  # Max 2 keywords
        
        # Fallback: use cleaned filename
        clean_name = re.sub(r'[^A-Z0-9_]', '_', name_upper)
        clean_name = re.sub(r'_+', '_', clean_name).strip('_')
        
        return clean_name[:20] if clean_name else "CUSTOM_STRATEGY"
    
    def _fallback_detection(self, filename: str) -> StrategyInfo:
        """Fallback detection khi không match pattern nào"""
        return StrategyInfo(
            filename=filename,
            symbol=self._extract_symbol_fallback(filename),
            timeframe=self._extract_timeframe_fallback(filename),
            strategy_name=self._generate_strategy_name(filename),
            version="v1",
            upload_date=datetime.now(),
            file_path="",
            trade_count=0,
            date_range="",
            metadata={'detection_method': 'fallback'}
        )
    
    def upload_strategy_file(self, file_content: str, filename: str, 
                           symbol_override: str = None, 
                           strategy_override: str = None) -> StrategyInfo:
        """
        📤 Upload và organize strategy file
        
        Args:
            file_content: CSV content
            filename: Original filename
            symbol_override: Manual symbol override
            strategy_override: Manual strategy override
        
        Returns:
            StrategyInfo của file đã upload
        """
        # 1. Detect strategy info
        strategy_info = self.detect_strategy_info(filename)
        
        # 2. Apply overrides
        if symbol_override:
            strategy_info.symbol = symbol_override.upper()
        if strategy_override:
            strategy_info.strategy_name = strategy_override.upper()
        
        # 3. Load và analyze CSV data
        try:
            from io import StringIO
            df = pd.read_csv(StringIO(file_content))
            
            # Analyze trade data
            strategy_info.trade_count = len(df)
            
            # Try to extract date range
            date_columns = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
            if date_columns:
                try:
                    dates = pd.to_datetime(df[date_columns[0]], errors='coerce')
                    dates = dates.dropna()
                    if len(dates) > 0:
                        start_date = dates.min().strftime('%Y-%m-%d')
                        end_date = dates.max().strftime('%Y-%m-%d')
                        strategy_info.date_range = f"{start_date} to {end_date}"
                except:
                    pass
            
            # Add metadata
            strategy_info.metadata = {
                'columns': list(df.columns),
                'detection_method': 'auto',
                'file_size': len(file_content),
                'upload_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"⚠️ Warning: Could not analyze CSV data: {e}")
            strategy_info.metadata = {'error': str(e)}
        
        # 4. Generate organized filename
        organized_filename = self._generate_organized_filename(strategy_info)
        organized_path = os.path.join(self.tradelist_dir, organized_filename)
        
        # 5. Save file với organized name
        os.makedirs(self.tradelist_dir, exist_ok=True)
        with open(organized_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        strategy_info.file_path = organized_path
        
        # 6. Store in database
        self._store_strategy_info(strategy_info)
        
        print(f"✅ Strategy uploaded: {organized_filename}")
        print(f"   Symbol: {strategy_info.symbol}")
        print(f"   Timeframe: {strategy_info.timeframe}")
        print(f"   Strategy: {strategy_info.strategy_name}")
        print(f"   Trades: {strategy_info.trade_count}")
        
        return strategy_info
    
    def _generate_organized_filename(self, strategy_info: StrategyInfo) -> str:
        """Generate standardized filename"""
        return f"{strategy_info.symbol}_{strategy_info.timeframe}_{strategy_info.strategy_name}_{strategy_info.version}.csv"
    
    def _store_strategy_info(self, strategy_info: StrategyInfo):
        """Store strategy info trong database"""
        with sqlite3.connect(self.db_path) as conn:
            # Check if exists và increment version nếu cần
            existing = conn.execute("""
                SELECT version FROM strategies 
                WHERE symbol = ? AND timeframe = ? AND strategy_name = ?
                ORDER BY version DESC LIMIT 1
            """, (strategy_info.symbol, strategy_info.timeframe, strategy_info.strategy_name)).fetchone()
            
            if existing:
                # Increment version
                current_version = existing[0]
                version_num = int(current_version.replace('v', '')) + 1
                strategy_info.version = f"v{version_num}"
                
                # Update filename với new version
                strategy_info.filename = self._generate_organized_filename(strategy_info)
                # Rename file
                old_path = strategy_info.file_path
                new_path = os.path.join(self.tradelist_dir, strategy_info.filename)
                if os.path.exists(old_path) and old_path != new_path:
                    os.rename(old_path, new_path)
                    strategy_info.file_path = new_path
            
            # Insert vào database
            conn.execute("""
                INSERT OR REPLACE INTO strategies 
                (filename, symbol, timeframe, strategy_name, version, upload_date, 
                 file_path, trade_count, date_range, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                strategy_info.filename,
                strategy_info.symbol,
                strategy_info.timeframe,
                strategy_info.strategy_name,
                strategy_info.version,
                strategy_info.upload_date,
                strategy_info.file_path,
                strategy_info.trade_count,
                strategy_info.date_range,
                json.dumps(strategy_info.metadata)
            ))
    
    def list_strategies(self, symbol: str = None, strategy_name: str = None) -> List[StrategyInfo]:
        """List all strategies với optional filtering"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM strategies WHERE is_active = 1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol.upper())
            
            if strategy_name:
                query += " AND strategy_name = ?"
                params.append(strategy_name.upper())
            
            query += " ORDER BY symbol, strategy_name, version DESC"
            
            rows = conn.execute(query, params).fetchall()
            
            strategies = []
            for row in rows:
                strategy = StrategyInfo(
                    filename=row['filename'],
                    symbol=row['symbol'],
                    timeframe=row['timeframe'],
                    strategy_name=row['strategy_name'],
                    version=row['version'],
                    upload_date=datetime.fromisoformat(row['upload_date']),
                    file_path=row['file_path'],
                    trade_count=row['trade_count'],
                    date_range=row['date_range'],
                    metadata=json.loads(row['metadata_json'])
                )
                strategies.append(strategy)
            
            return strategies
    
    def get_strategy(self, symbol: str, timeframe: str, strategy_name: str, version: str = None) -> Optional[StrategyInfo]:
        """Get specific strategy"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if version:
                query = """
                    SELECT * FROM strategies 
                    WHERE symbol = ? AND timeframe = ? AND strategy_name = ? AND version = ?
                    AND is_active = 1
                """
                params = [symbol.upper(), timeframe, strategy_name.upper(), version]
            else:
                # Get latest version
                query = """
                    SELECT * FROM strategies 
                    WHERE symbol = ? AND timeframe = ? AND strategy_name = ?
                    AND is_active = 1
                    ORDER BY version DESC LIMIT 1
                """
                params = [symbol.upper(), timeframe, strategy_name.upper()]
            
            row = conn.execute(query, params).fetchone()
            
            if row:
                return StrategyInfo(
                    filename=row['filename'],
                    symbol=row['symbol'],
                    timeframe=row['timeframe'],
                    strategy_name=row['strategy_name'],
                    version=row['version'],
                    upload_date=datetime.fromisoformat(row['upload_date']),
                    file_path=row['file_path'],
                    trade_count=row['trade_count'],
                    date_range=row['date_range'],
                    metadata=json.loads(row['metadata_json'])
                )
            
            return None
    
    def get_strategy_details(self, symbol: str, timeframe: str, strategy_name: str, version: str) -> Optional[Dict]:
        """Get detailed strategy information for editing"""
        strategy = self.get_strategy(symbol, timeframe, strategy_name, version)
        if not strategy:
            return None
            
        # Convert to dict for JSON serialization
        return {
            'filename': strategy.filename,
            'symbol': strategy.symbol,
            'timeframe': strategy.timeframe,
            'strategy_name': strategy.strategy_name,
            'version': strategy.version,
            'upload_date': strategy.upload_date.isoformat(),
            'file_path': strategy.file_path,
            'trade_count': strategy.trade_count,
            'date_range': strategy.date_range,
            'metadata': strategy.metadata
        }
    
    def update_strategy(self, symbol: str, timeframe: str, strategy_name: str, version: str, updates: Dict) -> bool:
        """Update strategy metadata"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # First check if strategy exists
                existing = self.get_strategy(symbol, timeframe, strategy_name, version)
                if not existing:
                    return False
                
                # Build update query dynamically
                update_fields = []
                params = []
                
                # Allow updating these fields
                updatable_fields = ['symbol', 'timeframe', 'strategy_name', 'version', 'metadata_json']
                
                for field, value in updates.items():
                    if field in updatable_fields:
                        if field == 'metadata_json' and isinstance(value, dict):
                            update_fields.append(f"{field} = ?")
                            params.append(json.dumps(value))
                        else:
                            update_fields.append(f"{field} = ?")
                            params.append(value)
                
                if not update_fields:
                    return True  # No updates needed
                
                # Add WHERE conditions
                params.extend([symbol.upper(), timeframe, strategy_name.upper(), version])
                
                query = f"""
                    UPDATE strategies 
                    SET {', '.join(update_fields)}
                    WHERE symbol = ? AND timeframe = ? AND strategy_name = ? AND version = ?
                    AND is_active = 1
                """
                
                cursor = conn.execute(query, params)
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"❌ Error updating strategy: {e}")
            return False

    def update_strategy_info(self, original_symbol: str, original_timeframe: str, 
                           original_strategy_name: str, original_version: str,
                           updates: dict) -> bool:
        """Update strategy information and optionally rename file"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get current strategy
                strategy = self.get_strategy(original_symbol, original_timeframe, 
                                           original_strategy_name, original_version)
                if not strategy:
                    return False
                
                # Prepare update data
                new_symbol = updates.get('symbol', strategy.symbol).upper()
                new_timeframe = updates.get('timeframe', strategy.timeframe)
                new_strategy_name = updates.get('strategy_name', strategy.strategy_name).upper()
                new_version = updates.get('version', strategy.version)
                
                # Update metadata with notes if provided
                metadata = strategy.metadata.copy()
                if 'notes' in updates:
                    metadata['notes'] = updates['notes']
                    metadata['last_edited'] = datetime.now().isoformat()
                
                # Check if we need to rename file
                filename_changed = (new_symbol != strategy.symbol or 
                                  new_timeframe != strategy.timeframe or
                                  new_strategy_name != strategy.strategy_name or
                                  new_version != strategy.version)
                
                new_filename = strategy.filename
                new_file_path = strategy.file_path
                
                if filename_changed:
                    # Generate new filename
                    temp_strategy = StrategyInfo(
                        filename="", symbol=new_symbol, timeframe=new_timeframe,
                        strategy_name=new_strategy_name, version=new_version,
                        upload_date=datetime.now(), file_path="", trade_count=0,
                        date_range="", metadata={}
                    )
                    new_filename = self._generate_organized_filename(temp_strategy)
                    new_file_path = os.path.join(self.tradelist_dir, new_filename)
                    
                    # Rename physical file
                    if os.path.exists(strategy.file_path):
                        os.rename(strategy.file_path, new_file_path)
                
                # Update database
                conn.execute("""
                    UPDATE strategies 
                    SET filename = ?, symbol = ?, timeframe = ?, strategy_name = ?, 
                        version = ?, file_path = ?, metadata_json = ?
                    WHERE symbol = ? AND timeframe = ? AND strategy_name = ? AND version = ?
                """, (
                    new_filename, new_symbol, new_timeframe, new_strategy_name,
                    new_version, new_file_path, json.dumps(metadata),
                    original_symbol, original_timeframe, original_strategy_name, original_version
                ))
                
                return True
                
        except Exception as e:
            print(f"❌ Error updating strategy: {e}")
            return False
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT DISTINCT symbol FROM strategies WHERE is_active = 1 ORDER BY symbol").fetchall()
            return [row[0] for row in rows]
    
    def get_available_strategies(self, symbol: Optional[str] = None) -> List[str]:
        """Get list of available strategy names"""
        with sqlite3.connect(self.db_path) as conn:
            if symbol:
                query = "SELECT DISTINCT strategy_name FROM strategies WHERE symbol = ? AND is_active = 1 ORDER BY strategy_name"
                params = [symbol.upper()]
            else:
                query = "SELECT DISTINCT strategy_name FROM strategies WHERE is_active = 1 ORDER BY strategy_name"
                params = []
            
            rows = conn.execute(query, params).fetchall()
            return [row[0] for row in rows]
    
    def delete_strategy(self, symbol: str, timeframe: str, strategy_name: str, version: str) -> bool:
        """Soft delete strategy"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE strategies SET is_active = 0 
                WHERE symbol = ? AND timeframe = ? AND strategy_name = ? AND version = ?
            """, (symbol.upper(), timeframe, strategy_name.upper(), version))
            
            return cursor.rowcount > 0
    
    def get_strategy_summary(self) -> Dict[str, Any]:
        """Get overall strategy summary"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Total strategies
            stats['total_strategies'] = conn.execute("SELECT COUNT(*) FROM strategies WHERE is_active = 1").fetchone()[0]
            
            # Symbols count
            stats['total_symbols'] = conn.execute("SELECT COUNT(DISTINCT symbol) FROM strategies WHERE is_active = 1").fetchone()[0]
            
            # Strategy types count
            stats['total_strategy_types'] = conn.execute("SELECT COUNT(DISTINCT strategy_name) FROM strategies WHERE is_active = 1").fetchone()[0]
            
            # Recent uploads
            recent = conn.execute("""
                SELECT filename, symbol, strategy_name, upload_date 
                FROM strategies WHERE is_active = 1 
                ORDER BY upload_date DESC LIMIT 5
            """).fetchall()
            
            stats['recent_uploads'] = [
                {
                    'filename': row[0],
                    'symbol': row[1],
                    'strategy': row[2],
                    'upload_date': row[3]
                } for row in recent
            ]
            
            return stats

# Global instance
strategy_manager = StrategyManager()

def get_strategy_manager() -> StrategyManager:
    """Get global strategy manager instance"""
    return strategy_manager

if __name__ == "__main__":
    # Test the strategy manager
    sm = StrategyManager()
    
    print("\n=== Strategy Manager Test ===")
    
    # Test filename detection
    test_files = [
        "BTCUSDT_30m_MACD_RSI_v1.csv",
        "BINANCE_ETHUSDT.P, 60.csv",
        "240-tradelist-LONGSHORT.csv",
        "my_custom_strategy_BTC_1h.csv"
    ]
    
    for filename in test_files:
        info = sm.detect_strategy_info(filename)
        print(f"\n📄 {filename}")
        print(f"   Symbol: {info.symbol}")
        print(f"   Timeframe: {info.timeframe}")
        print(f"   Strategy: {info.strategy_name}")
        print(f"   Version: {info.version}")
    
    # Test upload (với sample data)
    sample_csv = """Date,Time,Side,Price,Qty,PnL
2024-01-01,10:00:00,BUY,45000,0.1,0
2024-01-01,11:00:00,SELL,45100,0.1,100"""
    
    try:
        strategy_info = sm.upload_strategy_file(sample_csv, "BTCUSDT_60m_TEST_v1.csv")
        print(f"\n✅ Upload success: {strategy_info.filename}")
    except Exception as e:
        print(f"\n❌ Upload failed: {e}")
    
    # Test listing
    strategies = sm.list_strategies()
    print(f"\n📋 Total strategies: {len(strategies)}")
    
    # Summary
    summary = sm.get_strategy_summary()
    print(f"\n📊 Summary: {summary}")