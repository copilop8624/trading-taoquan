from strategy_manager import StrategyManager

sm = StrategyManager()
strategy = sm.get_strategy('ETHUSDT', '30m', 'RSI_MACD_ENHANCED_V2', 'v1')

if strategy:
    print(f"✅ Strategy found: {strategy.strategy_name}")
    print(f"📄 Filename: {strategy.filename}")
    print(f"📝 Notes: {strategy.metadata.get('notes', 'No notes')}")
else:
    print("❌ Strategy not found")
    
# List all ETHUSDT strategies
print("\n📋 All ETHUSDT strategies:")
strategies = sm.list_strategies(symbol='ETHUSDT')
for s in strategies:
    print(f"  - {s.strategy_name} {s.version}")