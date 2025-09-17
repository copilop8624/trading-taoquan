#!/usr/bin/env python3
"""
Simple server starter script
"""
import subprocess
import sys
import os

# Change to the script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("🚀 Starting Trading Optimization Web Server...")
print("📁 Working directory:", os.getcwd())
print("🐍 Python version:", sys.version)
print("📊 Starting web_app.py...")

try:
    # Run web_app.py
    subprocess.run([sys.executable, "web_app.py"], check=True)
except KeyboardInterrupt:
    print("\n⏹️ Server stopped by user")
except Exception as e:
    print(f"❌ Error starting server: {e}")
