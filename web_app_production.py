# Production Enhancement for web_app.py
# Add this to the end of web_app.py, replacing the existing if __name__ == '__main__': section

if __name__ == '__main__':
    import os
    
    # Production Configuration
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('HOST', '0.0.0.0')
    
    print("Starting Enhanced Trading Optimization Web App...")
    print(f"Access at: http://{HOST}:{PORT}")
    print("Features: Multi-Symbol Batch Processing, Analytics & Deployment Ready")
    print(f"Mode: {'Development' if DEBUG else 'Production'}")
    print(f"Advanced Engine: {'Available' if ADVANCED_MODE else 'SL-Only Fallback'}")
    
    # Production Security Headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response
    
    try:
        app.run(debug=DEBUG, host=HOST, port=PORT, threaded=True)
    except Exception as e:
        print(f"Failed to start server: {e}")
        print("Fallback: Starting on localhost:5000")
        app.run(debug=False, host='127.0.0.1', port=5000)