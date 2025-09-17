#!/usr/bin/env python3

import requests
import json
import sys

print("🔍 Testing Selected Data Mode Optimization...")

# Test 1: Get available strategies
print("\n1️⃣ Getting strategies...")
try:
    resp = requests.get('http://localhost:5000/list_strategies')
    if resp.status_code == 200:
        data = resp.json()
        print(f"📋 Raw response: {data}")
        
        if data.get('success') and 'strategies' in data:
            strategies = data['strategies']
            print(f"✅ Found {len(strategies)} strategies")
            print(f"📋 First strategy: {strategies[0] if strategies else 'None'}")
            
            # Find SAGA strategy
            saga_strategy = None
            for strategy in strategies:
                print(f"🔍 Checking strategy: {strategy}")
                if isinstance(strategy, dict):
                    if 'SAGAUSDT' in str(strategy.get('symbol', '')).upper():
                        saga_strategy = strategy
                        print(f"📋 SAGA strategy: {strategy}")
                        break
                elif isinstance(strategy, str):
                    if 'SAGAUSDT' in strategy.upper():
                        saga_strategy = strategy
                        print(f"📋 SAGA strategy (string): {strategy}")
                        break
        else:
            strategies = data  # Maybe it's just a list
            print(f"✅ Found {len(strategies)} strategies (direct list)")
            for strategy in strategies:
                print(f"🔍 Strategy: {strategy}")
            
            # Find SAGA strategy
            saga_strategy = None
            for strategy in strategies:
                if isinstance(strategy, str) and 'SAGAUSDT' in strategy.upper():
                    saga_strategy = strategy
                    break
        
        if not saga_strategy:
            print("❌ No SAGA strategy found")
            sys.exit(1)
    else:
        print(f"❌ Strategy API failed: {resp.status_code}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Strategy API error: {e}")
    sys.exit(1)

# Test 2: Get available candles
print("\n2️⃣ Getting candles...")
try:
    resp = requests.get('http://localhost:5000/list_candle_files')
    if resp.status_code == 200:
        data = resp.json()
        print(f"📋 Raw candle response: {data}")
        
        # Extract candle files from the response
        all_candles = []
        if 'files' in data:
            all_candles = data['files']
        elif 'csv_files' in data:
            all_candles = data['csv_files']
        else:
            all_candles = data if isinstance(data, list) else []
        
        print(f"✅ Found {len(all_candles)} candles")
        
        # Find SAGA candle
        saga_candle = None
        for candle in all_candles:
            print(f"🔍 Checking candle: {candle}")
            if 'SAGA' in candle.upper() and '.csv' in candle:
                saga_candle = candle
                print(f"🕯️ SAGA candle: {candle}")
                break
        
        if not saga_candle:
            print("❌ No SAGA candle found, using any available CSV candle for testing")
            # Use any available CSV candle for testing
            for candle in all_candles:
                if '.csv' in candle:
                    saga_candle = candle
                    print(f"🕯️ Using candle for testing: {candle}")
                    break
            
            if not saga_candle:
                print("❌ No CSV candles available")
                sys.exit(1)
    else:
        print(f"❌ Candle API failed: {resp.status_code}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Candle API error: {e}")
    sys.exit(1)

# Test 3: Run optimization with selected data
print("\n3️⃣ Running optimization...")
optimization_data = {
    'use_selected_data': 'true',
    'strategy_symbol': saga_strategy.get('symbol', '') if isinstance(saga_strategy, dict) else 'BTCUSDT',
    'strategy_timeframe': saga_strategy.get('timeframe', '') if isinstance(saga_strategy, dict) else '30m',
    'strategy_name': saga_strategy.get('strategy_name', '') if isinstance(saga_strategy, dict) else 'TRADELIST',
    'strategy_version': saga_strategy.get('version', '') if isinstance(saga_strategy, dict) else 'v1',
    'selected_candle': saga_candle,
    'opt_type': 'slbe_ts',
    'sl_min': 15,
    'sl_max': 25,
    'be_min': 0.5,
    'be_max': 2.5,
    'ts_trig_min': 3,
    'ts_trig_max': 7,
    'ts_step_min': 0.5,
    'ts_step_max': 2.5
}

print(f"📤 Sending optimization request:")
for key, value in optimization_data.items():
    print(f"   {key}: {value}")

try:
    resp = requests.post('http://localhost:5000/optimize', data=optimization_data, timeout=120)
    print(f"\n📥 Response status: {resp.status_code}")
    
    if resp.status_code == 200:
        result = resp.json()
        if result.get('success'):
            print(f"✅ Optimization successful!")
            if result.get('best_result'):
                best = result['best_result']
                print(f"   Best PnL: {best.get('pnl_total', 'N/A')}%")
                print(f"   Parameters: SL={best.get('sl')}% BE={best.get('be')}% TS={best.get('ts_trig')}/{best.get('ts_step')}%")
            else:
                print("⚠️ No best result found")
        else:
            print(f"❌ Optimization failed: {result.get('error', 'Unknown error')}")
    else:
        error_text = resp.text[:500]
        print(f"❌ HTTP {resp.status_code}: {error_text}")
        
except Exception as e:
    print(f"❌ Optimization request error: {e}")

print("\n🏁 Test complete!")