#!/usr/bin/env python3
"""
🚀 CLEAN STARTUP SCRIPT
Khởi động chỉ main web_app.py sau khi fix
"""

import subprocess
import sys
import os

def main():
    print("🚀 Starting FIXED Trading Optimization Web App...")
    print("🔧 All conflicts resolved, using single main app")
    print("=" * 50)
    
    # Ensure we're in the right directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Start only main web app
    try:
        subprocess.run([sys.executable, "web_app.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
