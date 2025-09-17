#!/usr/bin/env python3
"""
Debug Quick Summary Strategy not found errors
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_quick_summary_debug():
    print("🔍 DEBUGGING QUICK SUMMARY 'Strategy not found' ERROR")
    
    # First get available strategies
    try:
        resp = requests.get(f"{BASE_URL}/list_strategies")
        data = resp.json()
        strategies = data.get('strategies', [])
        print(f"📋 Available strategies: {len(strategies)}")
        for i, strategy in enumerate(strategies[:10]):  # Show first 10
            print(f"  {i+1}. {strategy.get('symbol', 'N/A')}_{strategy.get('timeframe', 'N/A')}_{strategy.get('strategy_name', 'N/A')}_{strategy.get('version', 'N/A')}")
            print(f"      File: {strategy.get('filename', 'N/A')}")
    except Exception as e:
        print(f"❌ Error getting strategies: {e}")
        return
    
    # Get available candle files
    try:
        resp = requests.get(f"{BASE_URL}/list_candle_files")
        candles = resp.json()
        if isinstance(candles, list):
            print(f"📋 Available candle files: {len(candles)}")
            for i, candle in enumerate(candles[:10]):  # Show first 10
                print(f"  {i+1}. {candle}")
        else:
            print(f"📋 Candle response: {candles}")
    except Exception as e:
        print(f"❌ Error getting candles: {e}")
        return
    
    # Test strategy data endpoint
    test_cases = [
        ("SAGAUSDT", "30m", "BS4", "v1"),
        ("BTCUSDT", "30m", "BS4", "v1"),
        ("BOMEUSDT", "240m", "BS4", "v1"),
        ("ETHUSDT", "5m", "LONG_SHORT", "v1"),
    ]
    
    print(f"\n🧪 TESTING STRATEGY DATA ENDPOINTS")
    for symbol, timeframe, strategy, version in test_cases:
        try:
            url = f"{BASE_URL}/get_strategy_data?symbol={symbol}&timeframe={timeframe}&strategy_name={strategy}&version={version}"
            print(f"\n🔍 Testing: {symbol} {timeframe} {strategy} {version}")
            print(f"📡 URL: {url}")
            
            resp = requests.get(url)
            print(f"📊 Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Success: {data.get('status', 'unknown')}")
                if 'trades' in data:
                    print(f"📈 Trades found: {len(data['trades'])}")
                if 'candle_file' in data:
                    print(f"🕯️ Candle file: {data['candle_file']}")
            else:
                print(f"❌ Error: {resp.text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    print(f"\n🎯 TEST QUICK SUMMARY POST")
    # Test quick summary with known good data - try exact match from available strategies
    test_data = {
        "symbol": "SAGAUSDT",
        "timeframe": "30m", 
        "strategy_name": "BS4",
        "version": "v1",
        "candle_file": "BINANCE_SAGAUSDT_30m.db"  # Try db file instead
    }
    
    print(f"📋 Testing with data: {test_data}")
    
    try:
        resp = requests.post(f"{BASE_URL}/quick_summary_strategy", json=test_data)
        print(f"📊 Quick Summary Status: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            print(f"✅ Quick Summary Success!")
            print(f"📈 Result keys: {list(result.keys())}")
            if 'error' in result:
                print(f"❌ Error in result: {result['error']}")
            if 'success' in result:
                print(f"📊 Success status: {result['success']}")
        else:
            print(f"❌ Quick Summary Error: {resp.text}")
    except Exception as e:
        print(f"❌ Quick Summary Exception: {e}")
        
    # Also test with exact strategy that exists from our list  
    print(f"\n🎯 TEST WITH EXACT MATCH FROM LIST")
    # From list: BTCUSDT_30m_TRADELIST_v1 with file 30-tradelist-BS4.csv
    test_data3 = {
        "symbol": "BTCUSDT",
        "timeframe": "30m", 
        "strategy_name": "TRADELIST",  # Exact match from list
        "version": "v1",
        "candle_file": "BINANCE_BTCUSDT_30m.db"
    }
    
    print(f"📋 Testing EXACT match: {test_data3}")
    
    try:
        resp = requests.post(f"{BASE_URL}/quick_summary_strategy", json=test_data3)
        print(f"📊 EXACT Quick Summary Status: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            print(f"✅ EXACT Quick Summary response received!")
            if 'error' in result:
                print(f"❌ Error in result: {result['error']}")
            if 'success' in result:
                print(f"📊 Success status: {result['success']}")
            if result.get('success'):
                print(f"🎉 SUCCESS! Strategy found and processed!")
                if 'trade_count' in result:
                    print(f"📈 Trade count: {result['trade_count']}")
        else:
            print(f"❌ EXACT Quick Summary Error: {resp.text}")
    except Exception as e:
        print(f"❌ EXACT Quick Summary Exception: {e}")
        
    # Test with SAGAUSDT case that we know has issue
    print(f"\n🎯 DEBUG SAGA CASE")
    # Check if there's any SAGA strategy in our list
    saga_strategies = [s for s in strategies if 'SAGA' in s.get('symbol', '')]
    print(f"📋 SAGA strategies found: {len(saga_strategies)}")
    for saga in saga_strategies:
        print(f"   - {saga.get('symbol')}_{saga.get('timeframe')}_{saga.get('strategy_name')}_{saga.get('version')}")
        print(f"     File: {saga.get('filename')}")
        
        # Test this exact SAGA strategy
        test_saga = {
            "symbol": saga.get('symbol'),
            "timeframe": saga.get('timeframe'),
            "strategy_name": saga.get('strategy_name'),
            "version": saga.get('version'),
            "candle_file": f"BINANCE_{saga.get('symbol')}_{saga.get('timeframe')}.db"
        }
        
        print(f"   Testing SAGA: {test_saga}")
        try:
            resp = requests.post(f"{BASE_URL}/quick_summary_strategy", json=test_saga)
            result = resp.json()
            if result.get('success'):
                print(f"   ✅ SAGA SUCCESS!")
            else:
                print(f"   ❌ SAGA FAILED: {result.get('error')}")
        except Exception as e:
            print(f"   ❌ SAGA Exception: {e}")

if __name__ == "__main__":
    test_quick_summary_debug()