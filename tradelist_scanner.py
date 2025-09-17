#!/usr/bin/env python3
"""
Manual Tradelist Scanner - Tự động scan và import tradelist files
"""
from strategy_manager import StrategyManager
import os
from pathlib import Path

class TradelistScanner:
    """
    🔍 Auto-scan tradelist folder và import vào database
    Tương tự như CSV migration cho candle data
    """
    
    def __init__(self):
        self.sm = StrategyManager()
        self.tradelist_dir = "tradelist"
        
    def scan_and_import(self):
        """Scan folder và import tất cả tradelist chưa có trong database"""
        print("🔍 Scanning tradelist folder for manual imports...")
        
        if not os.path.exists(self.tradelist_dir):
            print("❌ Tradelist folder not found")
            return
            
        # Get existing strategies from database
        existing = {f"{s.symbol}_{s.timeframe}_{s.strategy_name}" for s in self.sm.list_strategies()}
        
        # Scan files
        files = [f for f in os.listdir(self.tradelist_dir) if f.endswith('.csv')]
        print(f"📁 Found {len(files)} CSV files")
        
        imported = 0
        for filename in files:
            try:
                # Detect strategy info
                info = self.sm.detect_strategy_info(filename)
                strategy_key = f"{info.symbol}_{info.timeframe}_{info.strategy_name}"
                
                if strategy_key not in existing:
                    # Import to database
                    file_path = os.path.join(self.tradelist_dir, filename)
                    result = self.sm.upload_strategy_file(file_path, filename)
                    print(f"✅ Imported: {info.symbol} {info.timeframe} {info.strategy_name}")
                    imported += 1
                else:
                    print(f"⏭️ Already exists: {info.symbol} {info.timeframe} {info.strategy_name}")
                    
            except Exception as e:
                print(f"❌ Error with {filename}: {e}")
                
        print(f"\n🎉 Import completed: {imported} new strategies")
        return imported

if __name__ == "__main__":
    scanner = TradelistScanner()
    scanner.scan_and_import()