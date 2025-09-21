#!/usr/bin/env python3
import requests

r = requests.get("http://localhost:5000/api/results", params={"per_page": 1})
result = r.json()["results"][0]["parameters"]
print("SL:", result["sl"])
print("BE:", result["be"]) 
print("TS_ACT:", result["ts_activation"])
print("TS_STEP:", result["ts_step"])