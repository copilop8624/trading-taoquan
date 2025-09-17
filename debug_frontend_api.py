#!/usr/bin/env python3
"""
🔍 Debug Frontend API - Test endpoints
Test các API endpoints để debug tại sao frontend không load được data
"""

import requests
import json
import sys

def test_endpoint(url, description):
    """Test một endpoint và in kết quả"""
    print(f"\n{'='*60}")
    print(f"🧪 Testing: {description}")
    print(f"📡 URL: {url}")
    print('='*60)
    
    try:
        response = requests.get(url, timeout=10)
        print(f"✅ Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"📊 Response Type: {type(data)}")
                print(f"📄 Response Data:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                
                # Analysis
                if isinstance(data, dict):
                    if 'success' in data:
                        print(f"\n🔍 Success: {data.get('success')}")
                    if 'strategies' in data:
                        print(f"🔍 Strategies Count: {len(data.get('strategies', []))}")
                    if 'files' in data:
                        print(f"🔍 Files Count: {len(data.get('files', []))}")
                    if 'total' in data:
                        print(f"🔍 Total: {data.get('total')}")
                        
            except json.JSONDecodeError:
                print(f"❌ Invalid JSON Response:")
                print(response.text[:500])
        else:
            print(f"❌ Error Response:")
            print(response.text[:500])
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

def main():
    """Main function để test các endpoints"""
    print("🔍 Frontend API Debug Tool")
    print("Testing các endpoints để tìm vấn đề data loading")
    
    base_url = "http://localhost:5000"
    
    # Test các endpoints
    endpoints = [
        ('/list_strategies', 'List Strategies API'),
        ('/list_candle_files', 'List Candle Files API'),
        ('/data_management', 'Data Management Dashboard'),
    ]
    
    for endpoint, description in endpoints:
        test_endpoint(f"{base_url}{endpoint}", description)
    
    print(f"\n{'='*60}")
    print("🏁 Test completed!")
    print("='*60")

if __name__ == "__main__":
    main()