from strategy_manager import StrategyManager
import os

sm = StrategyManager()
strategies = sm.list_strategies()
saga_strategies = [s for s in strategies if 'SAGA' in s.symbol.upper()]

print('🔍 SAGA strategies found:')
for s in saga_strategies:
    print(f'  - {s.symbol} {s.timeframe} {s.strategy_name} {s.version}')
    print(f'    File: {s.file_path}')
    print(f'    Exists: {os.path.exists(s.file_path)}')
    print()

if not saga_strategies:
    print('❌ No SAGA strategies found')
    print('\n📋 Available strategies:')
    for s in strategies[:5]:  # Show first 5
        print(f'  - {s.symbol} {s.timeframe} {s.strategy_name} {s.version}')