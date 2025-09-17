#!/usr/bin/env python3

import requests
import json

print("🔍 DEBUG: Kiểm tra SAGA Strategy issue...")

# 1. Kiểm tra strategies hiện có
print("\n1️⃣ Lấy danh sách strategies:")
try:
    resp = requests.get('http://localhost:5000/list_strategies')
    if resp.status_code == 200:
        data = resp.json()
        if data.get('success') and 'strategies' in data:
            strategies = data['strategies']
            print(f"✅ Tìm thấy {len(strategies)} strategies")
            
            # Tìm SAGA strategies
            saga_strategies = []
            for strategy in strategies:
                if 'SAGA' in str(strategy.get('symbol', '')).upper():
                    saga_strategies.append(strategy)
                    print(f"📋 SAGA Strategy: {strategy}")
            
            if not saga_strategies:
                print("❌ Không tìm thấy SAGA strategy nào!")
            else:
                print(f"✅ Tìm thấy {len(saga_strategies)} SAGA strategies")
        else:
            print(f"❌ Response format không đúng: {data}")
    else:
        print(f"❌ Strategy API failed: {resp.status_code}")
        print(f"Response: {resp.text}")
        
except Exception as e:
    print(f"❌ Lỗi khi gọi API: {e}")

# 2. Kiểm tra candles
print("\n2️⃣ Lấy danh sách candles:")
try:
    resp = requests.get('http://localhost:5000/list_candle_files')
    if resp.status_code == 200:
        data = resp.json()
        print(f"📋 Raw candle response: {data}")
        
        # Tìm SAGA candles
        all_candles = data.get('files', [])
        saga_candles = [c for c in all_candles if 'SAGA' in c.upper()]
        
        print(f"✅ Tìm thấy {len(saga_candles)} SAGA candles:")
        for candle in saga_candles:
            print(f"   🕯️ {candle}")
            
except Exception as e:
    print(f"❌ Lỗi khi lấy candles: {e}")

# 3. Test optimization với exact parameters
print("\n3️⃣ Test optimization với exact parameters:")

# Sử dụng parameters chính xác từ API response
test_data = {
    'use_selected_data': 'true',
    'strategy_symbol': 'SAGAUSDT',  # Fix: đúng như API response
    'strategy_timeframe': '30m',
    'strategy_name': 'BS4',  # Fix: đúng như API response
    'strategy_version': 'v1',
    'selected_candle': 'candles/BINANCE_SAGAUSDT.P, 30.csv',  # Use CSV file instead of DB
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

print(f"📤 Test parameters:")
for key, value in test_data.items():
    print(f"   {key}: {value}")

try:
    resp = requests.post('http://localhost:5000/optimize', data=test_data, timeout=30)
    print(f"\n📥 Response status: {resp.status_code}")
    
    if resp.status_code == 200:
        result = resp.json()
        if result.get('success'):
            print("✅ Optimization thành công!")
        else:
            print(f"❌ Optimization failed: {result.get('error', 'Unknown error')}")
    else:
        error_text = resp.text[:500]
        print(f"❌ HTTP {resp.status_code}: {error_text}")
        
except Exception as e:
    print(f"❌ Lỗi request: {e}")

print("\n🏁 Debug hoàn tất!")