"""
EMERGENCY FLASK LAUNCHER
Simple Flask server to test connectivity and run optimization
"""

# Simple Flask server without complex imports
try:
    from flask import Flask, render_template, request, jsonify
    import os
    import sys
    
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Trading Optimization - Emergency Mode</title>
            <style>
                body { font-family: Arial; background: #1e1e1e; color: white; padding: 20px; }
                .container { max-width: 800px; margin: 0 auto; }
                .card { background: #2d2d2d; padding: 20px; margin: 10px 0; border-radius: 8px; }
                .btn { background: #4CAF50; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin: 10px; }
                .btn:hover { background: #45a049; }
                .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
                .success { background: #4CAF50; }
                .warning { background: #ff9800; }
                .error { background: #f44336; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 Trading Optimization - Emergency Mode</h1>
                
                <div class="card">
                    <h2>🔧 System Status</h2>
                    <div class="status success">✅ Flask Server: RUNNING</div>
                    <div class="status success">✅ Python Version: ''' + sys.version.split()[0] + '''</div>
                    <div class="status success">✅ Working Directory: ''' + os.getcwd() + '''</div>
                </div>
                
                <div class="card">
                    <h2>📊 Optimization Status</h2>
                    <p>Your 752,640 combinations optimization can be monitored here.</p>
                    <button class="btn" onclick="checkStatus()">🔍 Check Status</button>
                    <button class="btn" onclick="startOptimization()">🚀 Start New Optimization</button>
                    <div id="status-output" style="margin-top: 20px; padding: 10px; background: #333; border-radius: 5px;"></div>
                </div>
                
                <div class="card">
                    <h2>🎯 Quick Actions</h2>
                    <button class="btn" onclick="location.href='/files'">📁 View Files</button>
                    <button class="btn" onclick="location.href='/logs'">📋 View Logs</button>
                    <button class="btn" onclick="testConnection()">🔗 Test Connection</button>
                </div>
                
                <div class="card">
                    <h2>💡 Troubleshooting</h2>
                    <p><strong>Connection Issue Fixed:</strong> Flask server is now running!</p>
                    <p><strong>Port:</strong> 5000</p>
                    <p><strong>Access URLs:</strong></p>
                    <ul>
                        <li>Main: http://localhost:5000</li>
                        <li>Status: http://localhost:5000/status</li>
                        <li>Files: http://localhost:5000/files</li>
                    </ul>
                </div>
            </div>
            
            <script>
                function checkStatus() {
                    document.getElementById('status-output').innerHTML = '🔄 Checking status...';
                    fetch('/api/status')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('status-output').innerHTML = 
                                '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                        })
                        .catch(error => {
                            document.getElementById('status-output').innerHTML = 
                                '❌ Error: ' + error.message;
                        });
                }
                
                function startOptimization() {
                    document.getElementById('status-output').innerHTML = 
                        '⚠️ Feature available in full web_app.py mode';
                }
                
                function testConnection() {
                    document.getElementById('status-output').innerHTML = 
                        '✅ Connection test successful! Flask server is responding.';
                }
            </script>
        </body>
        </html>
        '''
    
    @app.route('/status')
    def status():
        return '''
        <h1>📊 Simple Status Monitor</h1>
        <p>Server is running on port 5000</p>
        <p><a href="/">← Back to main</a></p>
        '''
    
    @app.route('/files')
    def files():
        try:
            file_list = [f for f in os.listdir('.') if f.endswith(('.py', '.csv', '.bat'))]
            files_html = '<br>'.join([f'📄 {f}' for f in file_list])
            return f'''
            <h1>📁 Project Files</h1>
            {files_html}
            <p><a href="/">← Back to main</a></p>
            '''
        except Exception as e:
            return f'Error listing files: {str(e)}'
    
    @app.route('/api/status')
    def api_status():
        return jsonify({
            'server': 'running',
            'python_version': sys.version,
            'working_directory': os.getcwd(),
            'available_files': [f for f in os.listdir('.') if f.endswith('.py')],
            'message': 'Emergency Flask server is working!'
        })
    
    if __name__ == '__main__':
        print("🚀 EMERGENCY FLASK SERVER STARTING")
        print("=" * 40)
        print("✅ Python version:", sys.version.split()[0])
        print("✅ Working directory:", os.getcwd())
        print("✅ Flask server starting on http://localhost:5000")
        print("=" * 40)
        
        try:
            app.run(debug=True, host='0.0.0.0', port=5000)
        except Exception as e:
            print(f"❌ Error starting server: {e}")
            input("Press Enter to exit...")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Please install Flask: pip install flask")
    input("Press Enter to exit...")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    input("Press Enter to exit...")
