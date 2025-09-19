# Google Colab Setup Script
# Run this in Colab to setup the trading optimization app

import os
import subprocess
import sys

def setup_colab_environment():
    """Setup the trading app in Google Colab"""
    
    print("🚀 Setting up Trading Optimization App in Colab...")
    
    # Install required packages
    print("📦 Installing requirements...")
    subprocess.run([sys.executable, "-m", "pip", "install", 
                   "flask", "optuna", "pandas", "numpy", "plotly", 
                   "pyngrok"], check=True)
    
    # Install ngrok for public tunnel
    print("🌐 Setting up ngrok tunnel...")
    from pyngrok import ngrok
    
    # Upload your files to Colab (manual step)
    print("📁 Please upload these files to Colab:")
    print("   - web_app.py")
    print("   - All CSV data files")
    print("   - requirements.txt")
    
    return True

def run_app_in_colab():
    """Run the Flask app with ngrok tunnel"""
    from pyngrok import ngrok
    import threading
    import time
    
    # Start ngrok tunnel
    public_url = ngrok.connect(5000)
    print(f"🌍 Public URL: {public_url}")
    
    # Run Flask app in background
    def run_flask():
        os.system("python web_app.py")
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("✅ App is running! Access via the public URL above")
    print("⚠️ Remember: Colab sessions timeout after ~12 hours")

if __name__ == "__main__":
    setup_colab_environment()
    # Uncomment to auto-run:
    # run_app_in_colab()