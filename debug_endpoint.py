import requests
import json

# First test basic endpoint
url = "http://localhost:5000"

print("🔍 Testing base endpoint...")
try:
    response = requests.get(url)
    print(f"Base Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Server is running")
    else:
        print(f"❌ Server issue: {response.status_code}")
except Exception as e:
    print(f"❌ Connection error: {e}")

# Test optimize endpoint with simple GET first
print("\n🔍 Testing /optimize GET...")
try:
    response = requests.get(url + "/optimize")
    print(f"GET Status: {response.status_code}")
    print(f"Response: {response.text[:200]}...")
except Exception as e:
    print(f"❌ Error: {e}")

# Test quick summary to compare
print("\n🔍 Testing /quick_summary_strategy...")
test_data = {
    'strategy_symbol': 'SAGAUSDTUSDT',
    'strategy_timeframe': '30m',
    'strategy_name': 'TRADELIST',
    'strategy_version': 'v1'
}

try:
    response = requests.post(url + "/quick_summary_strategy", data=test_data)
    print(f"Quick Summary Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Quick Summary works: {result}")
    else:
        print(f"❌ Quick Summary failed: {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")