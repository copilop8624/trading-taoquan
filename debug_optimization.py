import requests
import json

def debug_optimization_issue():
    """Debug the specific optimization issue"""
    
    print("🔍 Debugging optimization candle loading issue...")
    
    # Get strategies
    response = requests.get("http://localhost:5000/list_strategies")
    strategies = response.json()['strategies']
    
    # Find DOGSUSDT strategy (has trade data)
    dogs_strategy = None
    for strategy in strategies:
        if strategy.get('trade_count', 0) > 0 and 'DOGS' in strategy['symbol']:
            dogs_strategy = strategy
            break
    
    if not dogs_strategy:
        print("❌ No DOGSUSDT strategy found")
        return
    
    # Get candle files
    response = requests.get("http://localhost:5000/list_candle_files")
    candles = response.json()['files']
    
    # Find CSV candle file
    csv_candle = None
    for candle in candles:
        if '.csv' in candle and 'BTCUSDT' in candle:
            csv_candle = candle
            break
    
    if not csv_candle:
        print("❌ No CSV candle file found")
        return
    
    print(f"📊 Using strategy: {dogs_strategy}")
    print(f"📊 Using candle: {csv_candle}")
    
    # Test optimization with detailed logging
    data = {
        'use_selected_data': 'true',
        'strategy_symbol': dogs_strategy['symbol'],
        'strategy_timeframe': dogs_strategy['timeframe'],
        'strategy_name': dogs_strategy['strategy_name'],
        'strategy_version': dogs_strategy['version'],
        'selected_candle': csv_candle,
        'opt_type': 'slbe_ts',
        'sl_min': 15,
        'sl_max': 25,
        'sl_step': 10,
        'be_range_start': 10,
        'be_range_end': 20,
        'be_step': 10,
        'ts_range_start': 1.5,
        'ts_range_end': 2.0,
        'ts_trig_step': 0.5,
        'ts_step_min': 0.5,
        'ts_step_max': 1.0,
        'ts_step_step': 0.5,
        'step_count': 2
    }
    
    print(f"📡 Sending request with data:")
    for key, value in data.items():
        print(f"  {key}: {value}")
    
    response = requests.post("http://localhost:5000/optimize", data=data)
    print(f"\n✅ Response Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"📊 Response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ HTTP Error: {response.text}")

if __name__ == "__main__":
    debug_optimization_issue()