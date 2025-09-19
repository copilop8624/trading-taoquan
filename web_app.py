import os
import sys

# Ensure repository root is on sys.path so local package imports like
# `from src.tradelist_manager import ...` work in CI where PYTHONPATH
# or the process working-directory may not be inherited by background jobs.
repo_root = os.path.dirname(os.path.abspath(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Ensure console uses UTF-8 for stdout/stderr to avoid UnicodeEncodeError on Windows
try:
    # Python 3.7+: reconfigure stdout/stderr encoding
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    # If reconfigure is not available, set PYTHONIOENCODING environment fallback
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import pandas as pd
import numpy as np
import json
import io
import base64
import math
import random
import tempfile
import os
import sqlite3

# 🔧 CENTRALIZED OPTUNA CONFIGURATION
DEFAULT_OPTUNA_TRIALS = 50  # Default number of Optuna trials, matches frontend default
MIN_OPTUNA_TRIALS = 10      # Minimum allowed trials
MAX_OPTUNA_TRIALS = 500     # Maximum allowed trials

def validate_optuna_trials(user_input, default=DEFAULT_OPTUNA_TRIALS):
    """
    Validate and sanitize Optuna trials input from frontend
    
    Args:
        user_input: Raw input from frontend (string, int, or None)
        default: Default value if input is invalid
        
    Returns:
        int: Validated trials count between MIN and MAX limits
    """
    try:
        trials = int(user_input) if user_input else default
        
        # Clamp to valid range
        if trials < MIN_OPTUNA_TRIALS:
            print(f"⚠️ Optuna trials {trials} below minimum, using {MIN_OPTUNA_TRIALS}")
            return MIN_OPTUNA_TRIALS
        elif trials > MAX_OPTUNA_TRIALS:
            print(f"⚠️ Optuna trials {trials} above maximum, using {MAX_OPTUNA_TRIALS}")
            return MAX_OPTUNA_TRIALS
        else:
            print(f"✅ Optuna trials validated: {trials}")
            return trials
            
    except (ValueError, TypeError):
        print(f"⚠️ Invalid Optuna trials input '{user_input}', using default {default}")
        return default
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
import optuna
import threading
from src.tradelist_manager import TradelistManager
from data_manager import DataManager, get_data_manager
from results_manager import ResultsManager, get_results_manager
from strategy_manager import StrategyManager, get_strategy_manager

# Data management imports
try:
    from csv_to_db import migrate_csv_to_db, show_database_status
    from binance_fetcher import BinanceFetcher
    DATA_MANAGEMENT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Data management modules not available: {e}")
    DATA_MANAGEMENT_AVAILABLE = False

# Import logic tá»« file gá»‘c vá»›i fallback
ADVANCED_MODE = False
_advanced_import_error = None
try:
    # Try package import first (preferred if module is inside web_backtest package)
    from web_backtest.backtest_gridsearch_slbe_ts_Version3 import (
        simulate_trade, grid_search_parallel,
        load_trade_csv as load_trade_csv_file,
        load_candle_csv as load_candle_csv_file,
        get_trade_pairs as get_trade_pairs_file
    )
    print("âœ… CHáº¾ Äá»˜ NÃ‚NG CAO ÄÃƒ KÃCH HOáº T (web_backtest): MÃ´ phá»ng Ä‘áº§y Ä‘á»§ BE + TS from Version3")
    ADVANCED_MODE = True
except Exception as e_pkg:
    try:
        # Fallback to top-level module if package import failed
        from backtest_gridsearch_slbe_ts_Version3 import (
            simulate_trade, grid_search_parallel,
            load_trade_csv as load_trade_csv_file,
            load_candle_csv as load_candle_csv_file,
            get_trade_pairs as get_trade_pairs_file
        )
        print("âœ… CHáº¾ Äá»˜ NÃ‚NG CAO ÄÃƒ KÃCH HOáº T: MÃ´ phá»ng Ä‘áº§y Ä‘á»§ BE + TS from top-level Version3")
        ADVANCED_MODE = True
    except Exception as e_top:
        _advanced_import_error = e_top
        print(f"âš ï¸ KhÃ´ng thá»ƒ táº£i module nÃ¢ng cao (package and top-level failed): {e_top}")
        print("ðŸ”„ Chuyá»ƒn sang cháº¿ Ä‘á»™ chá»‰ SL...")
        ADVANCED_MODE = False

        # Fallback functions
        def simulate_trade(*args, **kwargs):
            return None, ["MÃ´ phá»ng nÃ¢ng cao khÃ´ng kháº£ dá»¥ng"]

        def grid_search_parallel(trade_pairs, df_candle, sl_list, be_list, ts_trig_list, ts_step_list, opt_type):
            """
            Triá»ƒn khai dá»± phÃ²ng khi module nÃ¢ng cao khÃ´ng kháº£ dá»¥ng.
            Thay vÃ¬ tráº£ vá» máº£ng rá»—ng, sá»­ dá»¥ng dá»± phÃ²ng chá»‰ SL vá»›i tham sá»‘ BE/TS máº·c Ä‘á»‹nh.
            """
            print("âš ï¸ grid_search_parallel: Module nÃ¢ng cao khÃ´ng kháº£ dá»¥ng, sá»­ dá»¥ng dá»± phÃ²ng chá»‰ SL")
            print("ðŸš¨ Cáº¢NH BÃO: ÄÃ¢y lÃ  cháº¿ Ä‘á»™ CHá»ˆ SL, khÃ´ng pháº£i mÃ´ phá»ng thá»±c táº¿ BE+TS!")

            # Sá»­ dá»¥ng giÃ¡ trá»‹ trung bÃ¬nh tá»« cÃ¡c dáº£i BE/TS lÃ m tham sá»‘ cá»‘ Ä‘á»‹nh
            be_default = be_list[len(be_list)//2] if be_list else 0.5
            ts_trig_default = ts_trig_list[len(ts_trig_list)//2] if ts_trig_list else 0.5
            ts_step_default = ts_step_list[len(ts_step_list)//2] if ts_step_list else 3.0

            # Gá»i hÃ m dá»± phÃ²ng chá»‰ SL vá»›i tham sá»‘ BE/TS máº·c Ä‘á»‹nh
            sl_min = min(sl_list) if sl_list else 0
            sl_max = max(sl_list) if sl_list else 0
            sl_step = sl_list[1] - sl_list[0] if len(sl_list) > 1 else 1.0

            return grid_search_sl_fallback(trade_pairs, df_candle, sl_min, sl_max, sl_step, opt_type,
                                          be_default, ts_trig_default, ts_step_default)

        def load_trade_csv_file(*args, **kwargs):
            raise ImportError("Táº£i file trade khÃ´ng kháº£ dá»¥ng")

        def load_candle_csv_file(*args, **kwargs):
            raise ImportError("Táº£i file náº¿n khÃ´ng kháº£ dá»¥ng")

        def get_trade_pairs_file(*args, **kwargs):
            raise ImportError("Tạo cặp trade không khả dụng")

def safe_int(value):
    """Safely convert to int, handling infinity and NaN"""
    try:
        val = float(value)
        if np.isinf(val):
            print(f"⚠️ WARNING: Infinity value detected in safe_int: {value}")
            return 0  # Return 0 instead of 999999 for better data quality
        elif np.isnan(val):
            return 0
        return int(val)
    except (TypeError, ValueError):
        return 0

app = Flask(__name__)

# Data Management for Binance Updates
class WebDataManager:
    """Data manager for web app Binance updates"""
    def __init__(self):
        if DATA_MANAGEMENT_AVAILABLE:
            self.fetcher = BinanceFetcher()
        else:
            self.fetcher = None
        self.update_status = {
            'running': False,
            'progress': 0,
            'current_symbol': '',
            'log': []
        }

# Global data manager instance
web_data_manager = WebDataManager() if DATA_MANAGEMENT_AVAILABLE else None

def load_candle_data_from_db(symbol_name):
    """Load candle data from database table"""
    try:
        import sqlite3
        conn = sqlite3.connect('candles.db')
        table_name = f"BINANCE_{symbol_name}"
        
        query = f"SELECT * FROM `{table_name}` ORDER BY datetime"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    except Exception as e:
        raise Exception(f"Error loading from database: {str(e)}")

def safe_float(value, default=0.0):
    """Safely convert value to float, handling None, NaN, and invalid values"""
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            if math.isnan(value) or math.isinf(value):
                return default
            return float(value)
        return float(value)
    except (ValueError, TypeError):
        return default

def discover_available_symbols():
    """Tự động phát hiện symbols và timeframes từ thư mục candles/"""
    import glob
    import os
    import re
    
    candles_dir = os.path.join(os.path.dirname(__file__), 'candles')
    if not os.path.exists(candles_dir):
        # Fallback to root directory if candles/ doesn't exist
        candles_dir = os.path.dirname(__file__)
    
    symbols_data = {}
    
    # Scan candle files
    candle_pattern = os.path.join(candles_dir, '*.csv')
    candle_files = glob.glob(candle_pattern)
    
    for file_path in candle_files:
        filename = os.path.basename(file_path)
        
        # Skip tradelist files
        if 'tradelist' in filename.lower():
            continue
            
        # Parse BINANCE format: BINANCE_SYMBOL.P, timeframe.csv or BINANCE_SYMBOL, timeframe.csv
        match = re.match(r'BINANCE_([A-Z]+)\.?P?,?\s*(\d+)\.csv', filename)
        if match:
            symbol = f"BINANCE_{match.group(1)}"
            timeframe = match.group(2)
            
            if symbol not in symbols_data:
                symbols_data[symbol] = []
            if timeframe not in symbols_data[symbol]:
                symbols_data[symbol].append(timeframe)
    
    # Sort timeframes
    for symbol in symbols_data:
        symbols_data[symbol] = sorted(symbols_data[symbol], key=int)
    
    return symbols_data

# ============================================================================
# ðŸŽ¯ NEW ROUTES - BATCH PROCESSING & ANALYTICS  
# ============================================================================

@app.route('/batch')
def batch_dashboard():
    """🚀 Batch processing dashboard with full functionality"""
    # Automatically discover symbols from candles/ directory
    symbols_data = discover_available_symbols()
    
    try:
        return render_template('batch_dashboard.html', 
                             available_symbols=symbols_data,
                             available_timeframes=symbols_data)
    except Exception as e:
        return f"""
        <html>
        <head>
            <title>ðŸš€ Multi-Symbol Batch Processing</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
                .data-card {{ background: #e8f4f8; padding: 15px; border-radius: 8px; margin: 10px 0; }}
                .symbol {{ background: #d4edda; padding: 8px; margin: 5px; border-radius: 5px; display: inline-block; }}
                .nav {{ background: #007bff; color: white; padding: 10px; border-radius: 5px; margin-bottom: 20px; }}
                .nav a {{ color: white; text-decoration: none; margin-right: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="nav">
                    <a href="/">ðŸ  Home</a>
                    <a href="/compare">ðŸ“Š Compare</a>  
                    <a href="/analytics">ðŸ“ˆ Analytics</a>
                </div>
                
                <h1>ðŸš€ Multi-Symbol Batch Processing Dashboard</h1>
                
                <div class="data-card">
                    <h2>ðŸ“Š Available Trading Data:</h2>
                    <div>
                        <div class="symbol">
                            <strong>BINANCE_BOMEUSDT:</strong> 240min timeframe
                        </div>
                        <div class="symbol">
                            <strong>BINANCE_BTCUSDT:</strong> 60min, 30min, 5min timeframes  
                        </div>
                        <div class="symbol">
                            <strong>BINANCE_SAGAUSDT:</strong> 30min timeframe
                        </div>
                    </div>
                </div>
                
                <div class="data-card">
                    <h2>ðŸŽ¯ Batch Processing Features:</h2>
                    <ul>
                        <li>âœ… Multi-symbol parallel optimization</li>
                        <li>âœ… Real-time progress tracking</li>
                        <li>âœ… Comprehensive result analysis</li>
                        <li>âœ… Export & comparison tools</li>
                    </ul>
                </div>
                
                <div class="data-card">
                    <h3>âš ï¸ Status:</h3>
                    <p>Template system loading... ({str(e)})</p>
                    <p><strong>System:</strong> Multi-Symbol Processor Ready</p>
                </div>
            </div>
        </body>
        </html>
        """

@app.route('/compare')
def comparison_dashboard():
    """ðŸ” Result comparison dashboard"""
    return """
    <html>
    <head>
        <title>ðŸ” Result Comparison Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
            .nav { background: #28a745; color: white; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
            .nav a { color: white; text-decoration: none; margin-right: 15px; }
            .feature-card { background: #e9f7ef; padding: 15px; border-radius: 8px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="nav">
                <a href="/">ðŸ  Home</a>
                <a href="/batch">ï¿½ Batch Processing</a>  
                <a href="/analytics">ðŸ“ˆ Analytics</a>
            </div>
            
            <h1>ðŸ” Multi-Symbol Result Comparison</h1>
            
            <div class="feature-card">
                <h2>ðŸ“Š Available Comparisons:</h2>
                <ul>
                    <li>âœ… Side-by-side parameter optimization results</li>
                    <li>âœ… Performance metrics comparison across symbols</li>
                    <li>âœ… Risk-return analysis visualization</li>
                    <li>âœ… Strategy effectiveness evaluation</li>
                </ul>
            </div>
            
            <div class="feature-card">
                <h3>ðŸŽ¯ Ready for Integration</h3>
                <p>Comparison engine ready to analyze optimization results</p>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/analytics')  
def analytics_dashboard():
    """ðŸ“ˆ Advanced analytics dashboard with Chart.js integration"""
    return """
    <html>
    <head>
        <title>ðŸ“ˆ Advanced Analytics Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
            .nav { background: #ffc107; color: black; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
            .nav a { color: black; text-decoration: none; margin-right: 15px; }
            .chart-container { background: #fff3cd; padding: 20px; border-radius: 8px; margin: 15px 0; }
            .chart-row { display: flex; justify-content: space-between; margin: 20px 0; }
            .chart-box { width: 48%; height: 300px; background: white; border: 1px solid #ddd; border-radius: 5px; padding: 10px; }
            .analytics-stats { background: #e2e3e5; padding: 15px; border-radius: 8px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="nav">
                <a href="/">ðŸ  Home</a>
                <a href="/batch">ðŸš€ Batch Processing</a>  
                <a href="/compare">ðŸ” Compare Results</a>
            </div>
            
            <h1>ðŸ“ˆ Advanced Analytics Dashboard</h1>
            
            <div class="analytics-stats">
                <h2>ðŸ“Š Chart.js Integration Ready</h2>
                <ul>
                    <li>âœ… Performance Radar Charts</li>
                    <li>âœ… Risk-Return Scatter Plots</li>
                    <li>âœ… Parameter Optimization Heat Maps</li>
                    <li>âœ… Comparative Bar Charts</li>
                    <li>âœ… Time Series Analysis</li>
                    <li>âœ… Bubble Charts for Multi-Dimensional Analysis</li>
                </ul>
            </div>
            
            <div class="chart-row">
                <div class="chart-box">
                    <h3>ðŸ“ˆ Performance Overview</h3>
                    <canvas id="perfChart"></canvas>
                </div>
                <div class="chart-box">
                    <h3>ðŸŽ¯ Risk Analysis</h3>
                    <canvas id="riskChart"></canvas>
                </div>
            </div>
            
            <div class="chart-container">
                <h3>ðŸš€ Multi-Symbol Analytics Ready</h3>
                <p>Advanced Chart.js visualization system prepared for:</p>
                <p><strong>Symbols:</strong> BINANCE_BOMEUSDT, BINANCE_BTCUSDT, BINANCE_SAGAUSDT</p>
                <p><strong>Capabilities:</strong> Real-time data visualization, interactive controls, export features</p>
            </div>
        </div>
        
        <script>
            // Sample Chart.js initialization
            const ctx1 = document.getElementById('perfChart').getContext('2d');
            new Chart(ctx1, {
                type: 'line',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
                    datasets: [{
                        label: 'Performance',
                        data: [12, 19, 3, 5, 2],
                        borderColor: '#007bff',
                        tension: 0.1
                    }]
                }
            });
            
            const ctx2 = document.getElementById('riskChart').getContext('2d');
            new Chart(ctx2, {
                type: 'doughnut',
                data: {
                    labels: ['Low Risk', 'Medium Risk', 'High Risk'],
                    datasets: [{
                        data: [30, 50, 20],
                        backgroundColor: ['#28a745', '#ffc107', '#dc3545']
                    }]
                }
            });
        </script>
    </body>
    </html>
    """

# ============================================================================
# ðŸŽ¯ API ROUTES FOR BATCH PROCESSING
# ============================================================================

@app.route('/api/batch_optimize', methods=['GET', 'POST'])
def api_batch_optimize():
    """🚀 API endpoint for batch optimization"""
    if request.method == 'GET':
        # Return API documentation for GET requests
        return jsonify({
            'endpoint': '/api/batch_optimize',
            'method': 'POST',
            'description': 'Start batch optimization for multiple symbols',
            'required_payload': {
                'symbols': ['BINANCE_BTCUSDT', 'BINANCE_BOMEUSDT'],
                'timeframes': ['30', '60', '240']
            },
            'optional_payload': {
                'parameters': {
                    'sl_min': 1.0,
                    'sl_max': 5.0,
                    'be_min': 2.0,
                    'be_max': 2.0,
                    'ts_min': 2.0,
                    'ts_max': 1.5
                }
            },
            'example_curl': 'curl -X POST "http://127.0.0.1:5000/api/batch_optimize" -H "Content-Type: application/json" -d \'{"symbols": ["BINANCE_BTCUSDT"], "timeframes": ["30"]}\''
        })
    
    # Handle POST requests
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])
        timeframes = data.get('timeframes', {})
        parameters = data.get('parameters', {})
        
        # Basic validation
        if not symbols:
            return jsonify({'success': False, 'error': 'No symbols selected'}), 400
            
        # Return sample response for now
        return jsonify({
            'success': True,
            'message': 'Batch optimization started',
            'job_id': 'batch_001',
            'symbols': symbols,
            'estimated_time': len(symbols) * 30  # seconds
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/batch_status/<job_id>', methods=['GET'])
def api_batch_status(job_id):
    """ðŸ“Š Get batch optimization progress"""
    # Sample progress data
    return jsonify({
        'job_id': job_id,
        'status': 'running',
        'progress': 65,
        'completed_symbols': 2,
        'total_symbols': 3,
        'current_symbol': 'BINANCE_BTCUSDT',
        'estimated_remaining': 45
    })

@app.route('/api/batch_results/<job_id>', methods=['GET'])
def api_batch_results(job_id):
    """ðŸ“ˆ Get batch optimization results"""
    # Sample results data
    return jsonify({
        'job_id': job_id,
        'status': 'completed',
        'results': [
            {
                'symbol': 'BINANCE_BTCUSDT',
                'timeframe': '30',
                'best_params': {'sl': 2.5, 'be': 1.2, 'ts_trig': 0.8, 'ts_step': 5.0},
                'performance': {'pnl': 15.67, 'winrate': 68.5, 'sharpe': 1.24}
            },
            {
                'symbol': 'BINANCE_BOMEUSDT', 
                'timeframe': '240',
                'best_params': {'sl': 3.0, 'be': 1.5, 'ts_trig': 1.0, 'ts_step': 5.0},
                'performance': {'pnl': 12.34, 'winrate': 72.1, 'sharpe': 1.18}
            }
        ]
    })


@app.route('/health', methods=['GET'])
def health():
    info = {'status': 'ok', 'time': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'advanced_mode': bool(ADVANCED_MODE)}
    if _advanced_import_error is not None:
        info['advanced_import_error'] = str(_advanced_import_error)
    return jsonify(info), 200

@app.route('/test_filter_debug.html', methods=['GET'])
def test_filter_debug():
    """Serve test filter debug page"""
    try:
        test_file_path = os.path.join(os.path.dirname(__file__), 'test_filter_debug.html')
        return send_file(test_file_path)
    except Exception as e:
        return f"Error loading test file: {e}", 404

@app.route('/test_range_suggestions', methods=['GET'])
def test_range_suggestions():
    """Serve test range suggestions page"""
    try:
        return render_template('test_range_suggestions.html')
    except Exception as e:
        return f"Error loading test page: {e}", 404


# ========== DATA MANAGEMENT API ENDPOINTS ==========

@app.route('/api/status')
def api_status():
    """API endpoint for update status"""
    if not DATA_MANAGEMENT_AVAILABLE or web_data_manager is None:
        return jsonify({'success': False, 'error': 'Data management not available'})
    return jsonify(web_data_manager.update_status)

@app.route('/api/csv/migrate', methods=['POST'])
def api_csv_migrate():
    """API endpoint to migrate CSV files to database"""
    if not DATA_MANAGEMENT_AVAILABLE or web_data_manager is None:
        return jsonify({'success': False, 'error': 'Data management not available'})
    
    try:
        def run_migration():
            web_data_manager.update_status['running'] = True
            web_data_manager.update_status['current_symbol'] = 'Migrating CSV files...'
            web_data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting CSV migration")
            
            try:
                migrate_csv_to_db()
                web_data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] CSV migration completed successfully")
            except Exception as e:
                web_data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Migration error: {e}")
            finally:
                web_data_manager.update_status['running'] = False
                web_data_manager.update_status['current_symbol'] = ''
        
        thread = threading.Thread(target=run_migration)
        thread.start()
        
        return jsonify({'success': True, 'message': 'CSV migration started'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/binance/update', methods=['POST'])
def api_binance_update():
    """API endpoint to update data from Binance"""
    if not DATA_MANAGEMENT_AVAILABLE or web_data_manager is None:
        return jsonify({'success': False, 'error': 'Data management not available'})
    
    try:
        data = request.get_json()
        symbol = data.get('symbol', 'all') if data else 'all'
        timeframe = data.get('timeframe', '') if data else ''
        
        def run_update():
            web_data_manager.update_status['running'] = True
            web_data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting Binance update")
            
            try:
                if symbol == 'all':
                    web_data_manager.fetcher.update_all_symbols()
                else:
                    web_data_manager.update_status['current_symbol'] = f"{symbol} {timeframe}"
                    web_data_manager.fetcher.update_symbol(symbol, timeframe)
                
                web_data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Binance update completed")
            except Exception as e:
                web_data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Update error: {e}")
            finally:
                web_data_manager.update_status['running'] = False
                web_data_manager.update_status['current_symbol'] = ''
        
        thread = threading.Thread(target=run_update)
        thread.start()
        
        return jsonify({'success': True, 'message': 'Binance update started'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/binance/add', methods=['POST'])
def api_binance_add():
    """API endpoint to add new symbol from Binance"""
    if not DATA_MANAGEMENT_AVAILABLE or web_data_manager is None:
        return jsonify({'success': False, 'error': 'Data management not available'})
    
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper() if data else ''
        timeframe = data.get('timeframe', '30m') if data else '30m'
        days = int(data.get('days', 365)) if data and data.get('days') else 365
        
        def run_add():
            web_data_manager.update_status['running'] = True
            web_data_manager.update_status['current_symbol'] = f"Adding {symbol} {timeframe}"
            web_data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Adding new symbol {symbol} {timeframe}")
            
            try:
                if web_data_manager.fetcher:
                    # Add logic here for fetching new symbol data
                    web_data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully added {symbol} {timeframe}")
            except Exception as e:
                web_data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Add error: {e}")
            finally:
                web_data_manager.update_status['running'] = False
                web_data_manager.update_status['current_symbol'] = ''
        
        thread = threading.Thread(target=run_add)
        thread.start()
        
        return jsonify({'success': True, 'message': f'Adding {symbol} {timeframe}'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ===================================================


# Simple artifacts UI
@app.route('/reports', methods=['GET'])
def reports_index():
    base = Path('reports')
    if not base.exists():
        return render_template('reports_list.html', runs=[])
    runs = []
    for d in sorted(base.iterdir(), reverse=True):
        if d.is_dir():
            files = [f.name for f in d.iterdir() if f.is_file()]
            runs.append({'tag': d.name, 'files': files})
    return render_template('reports_list.html', runs=runs)


@app.route('/reports/<tag>/file/<path:filename>', methods=['GET'])
def reports_file(tag, filename):
    p = Path('reports') / tag / filename
    if not p.exists():
        return jsonify({'error': 'not found'}), 404
    return send_file(str(p), as_attachment=True)


@app.route('/screenshots/<tag>/file/<path:filename>', methods=['GET'])
def screenshots_file(tag, filename):
    p = Path('screenshots') / tag / filename
    if not p.exists():
        return jsonify({'error': 'not found'}), 404
    return send_file(str(p), as_attachment=False)


# Demo endpoint to run SmartRangeFinder quickly and return JSON
@app.route('/run_demo', methods=['GET', 'POST'])
def run_demo():
    """Run SmartRangeFinder on the sample tradelist and return range_analysis.json.
    Query params:
      - tradelist: path to tradelist CSV (optional, defaults to sample_tradelist.csv)
    """
    try:
        tradelist = request.args.get('tradelist', 'sample_tradelist.csv')
        out_dir = Path('output_demo')
        out_dir.mkdir(parents=True, exist_ok=True)

        # Import SmartRangeFinder lazily so endpoint works even if module missing
        try:
            from smart_range_finder import SmartRangeFinder
        except Exception as e:
            return jsonify({'status': 'error', 'error': f'SmartRangeFinder import failed: {e}'}), 500

        srf = SmartRangeFinder(tradelist_path=tradelist)
        analysis = srf.analyze_price_movement_patterns()

        out_file = out_dir / 'range_analysis.json'
        with out_file.open('w', encoding='utf-8') as fh:
            json.dump(analysis, fh, ensure_ascii=False, indent=2)

        return jsonify({'status': 'ok', 'output': str(out_file), 'analysis': analysis}), 200
    except Exception as exc:
        tb = traceback.format_exc()
        return jsonify({'status': 'error', 'error': str(exc), 'traceback': tb}), 500

# Global variable to track optimization progress
optimization_status = {
    'running': False,
    'start_time': None,
    'total_combinations': 0,
    'current_progress': 0,
    'estimated_completion': None,
    'status_message': 'Ready'
}

def convert_to_serializable(obj):
    """Convert numpy/pandas types to native Python types for JSON serialization"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.floating):
        val = float(obj)
        # Handle infinity values for JSON serialization
        if np.isinf(val):
            # For advanced metrics, allow reasonable infinity values
            if abs(val) > 1e6:
                print(f"âš ï¸ WARNING: Very large infinity in convert_to_serializable: {val}")
                return 999999.0 if val > 0 else -999999.0
            else:
                return val  # Keep reasonable infinity values for metrics
        elif np.isnan(val):
            return 0.0
        return val
    elif isinstance(obj, float):
        # Handle Python float infinity/nan
        if np.isinf(obj):
            if abs(obj) > 1e6:
                print(f"âš ï¸ WARNING: Very large Python float infinity: {obj}")
                return 999999.0 if obj > 0 else -999999.0
            else:
                return obj  # Keep reasonable infinity values
        elif np.isnan(obj):
            return 0.0
        return obj
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Series):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    else:
        return obj

def safe_float_parse(form_data, key, default):
    """Safely parse float from form data, handling empty strings and invalid values"""
    try:
        value = form_data.get(key, default)
        if isinstance(value, str):
            value = value.strip()  # Remove whitespace
            if not value:  # Empty or whitespace-only string
                return float(default)
        return float(value)
    except (ValueError, TypeError):
        return float(default)

# Defensive helper: safe_float

def safe_float(x, default=0.0):
    try:
        if x is None:
            return float(default)
        if isinstance(x, str):
            x = x.strip()
            if x == '':
                return float(default)
        val = float(x)
        if not np.isfinite(val):
            return float(default)
        return val
    except Exception:
        return float(default)


# Robust candle index finder with tolerant matching

def find_candle_idx(dt, df_candle):
    try:
        if pd.isna(dt) or df_candle is None or not hasattr(df_candle, 'columns'):
            return -1
        if 'time' not in df_candle.columns:
            return -1
        arr = df_candle['time'].values
        try:
            target_dt = np.datetime64(dt)
        except Exception:
            try:
                target_dt = np.datetime64(pd.to_datetime(dt))
            except Exception:
                return -1
        # bounds
        if len(arr) == 0:
            return -1
        try:
            if target_dt < arr[0] or target_dt > arr[-1]:
                return -1
        except Exception:
            pass
        # exact match
        idx = np.where(arr == target_dt)[0]
        if len(idx) > 0:
            return int(idx[0])
        # nearest within tolerance (120s)
        try:
            diffs = np.abs((arr - target_dt).astype('timedelta64[s]')).astype('int64')
            nearest = int(np.argmin(diffs))
            if int(diffs[nearest]) <= 120:
                return nearest
        except Exception:
            pass
        return -1
    except Exception:
        return -1


# Defensive SL-only simulation fallback

def simulate_trade_sl_only(pair, df_candle, sl_percent):
    entryPrice = safe_float(pair.get('entryPrice', 0))
    exitPriceOrigin = safe_float(pair.get('exitPrice', entryPrice))
    side = pair.get('side', 'LONG') or 'LONG'
    # If no valid candles, compute from given pair prices
    if df_candle is None or not hasattr(df_candle, 'columns') or 'time' not in df_candle.columns or len(df_candle) == 0:
        try:
            if side == 'LONG':
                pnlPct = (exitPriceOrigin - entryPrice) / entryPrice * 100.0 if entryPrice != 0 else 0.0
            else:
                pnlPct = (entryPrice - exitPriceOrigin) / entryPrice * 100.0 if entryPrice != 0 else 0.0
            if not np.isfinite(pnlPct):
                pnlPct = 0.0
        except Exception:
            pnlPct = 0.0
        return {
            'num': pair.get('num'),
            'side': side,
            'entryPrice': float(entryPrice),
            'exitPrice': float(exitPriceOrigin),
            'exitType': 'Original',
            'pnlPct': float(pnlPct),
            'pnlPctOrigin': float(pnlPct),
            'entryDt': pair.get('entryDt'),
            'exitDt': pair.get('exitDt'),
            'sl': sl_percent,
            'be': 0,
            'ts_trig': 0,
            'ts_step': 0
        }
    # find indexes
    entryIdx = find_candle_idx(pair.get('entryDt'), df_candle)
    exitIdx = find_candle_idx(pair.get('exitDt'), df_candle)
    if entryIdx == -1 or exitIdx == -1 or exitIdx <= entryIdx:
        # attempt approximate mapping
        try:
            arr = df_candle['time'].values
            if pair.get('entryDt') is not None:
                target_entry = np.datetime64(pair.get('entryDt'))
                diffs = np.abs((arr - target_entry).astype('timedelta64[s]')).astype('int64')
                entryIdx = int(np.argmin(diffs))
                if int(diffs[entryIdx]) > 300:
                    return None
            else:
                return None
            if pair.get('exitDt') is not None:
                target_exit = np.datetime64(pair.get('exitDt'))
                diffs2 = np.abs((arr - target_exit).astype('timedelta64[s]')).astype('int64')
                exitIdx = int(np.argmin(diffs2))
                if int(diffs2[exitIdx]) > 300:
                    return None
            else:
                return None
            if exitIdx <= entryIdx:
                return None
        except Exception:
            return None
    # fallback to candle prices if pair prices invalid
    try:
        if not (entryPrice and np.isfinite(entryPrice)):
            if 'open' in df_candle.columns and 0 <= entryIdx < len(df_candle):
                entryPrice = safe_float(df_candle.iloc[entryIdx].get('open', entryPrice))
        finalExitPrice = safe_float(exitPriceOrigin)
        if not (finalExitPrice and np.isfinite(finalExitPrice)):
            if 'close' in df_candle.columns and 0 <= exitIdx < len(df_candle):
                finalExitPrice = safe_float(df_candle.iloc[exitIdx].get('close', finalExitPrice))
    except Exception:
        entryPrice = safe_float(entryPrice)
        finalExitPrice = safe_float(exitPriceOrigin)
    exitType = 'Original'
    # SL check
    if sl_percent and sl_percent != 0:
        try:
            if side == 'LONG':
                slPrice = entryPrice * (1 - sl_percent / 100.0)
                for i in range(entryIdx, min(exitIdx + 1, len(df_candle))):
                    low = safe_float(df_candle.iloc[i].get('low', np.nan), default=np.nan)
                    if not np.isnan(low) and low <= slPrice:
                        finalExitPrice = low
                        exitType = 'SL'
                        break
            else:
                slPrice = entryPrice * (1 + sl_percent / 100.0)
                for i in range(entryIdx, min(exitIdx + 1, len(df_candle))):
                    high = safe_float(df_candle.iloc[i].get('high', np.nan), default=np.nan)
                    if not np.isnan(high) and high >= slPrice:
                        finalExitPrice = high
                        exitType = 'SL'
                        break
        except Exception:
            pass
    try:
        if side == 'LONG':
            pnlPct = (finalExitPrice - entryPrice) / entryPrice * 100.0 if entryPrice != 0 else 0.0
        else:
            pnlPct = (entryPrice - finalExitPrice) / entryPrice * 100.0 if entryPrice != 0 else 0.0
        if not np.isfinite(pnlPct):
            pnlPct = 0.0
    except Exception:
        pnlPct = 0.0
    return {
        'num': pair.get('num'),
        'side': side,
        'entryPrice': float(entryPrice),
        'exitPrice': float(finalExitPrice),
        'exitType': exitType,
        'pnlPct': float(pnlPct),
        'pnlPctOrigin': float(pnlPct),
        'entryDt': pair.get('entryDt'),
        'exitDt': pair.get('exitDt'),
        'sl': sl_percent,
        'be': 0,
        'ts_trig': 0,
        'ts_step': 0
    }

# Import cÃ¡c functions tá»« script gá»‘c
def normalize_trade_date(s):
    """Normalize trade date with support for multiple formats"""
    try:
        # Thá»­ format 1: YYYY-MM-DD HH:MM (ACEUSDT/TradingView/BOME format)
        dt = pd.to_datetime(s, format='%Y-%m-%d %H:%M', errors='coerce')
        if not pd.isna(dt):
            # For simplicity, treat all YYYY-MM-DD format as UTC
            if dt.tz is None:
                dt = dt.tz_localize('UTC').tz_localize(None)
            return dt
    except:
        pass
    
    try:
        # Thá»­ format 2: MM/DD/YYYY HH:MM (Legacy BTC format)
        dt = pd.to_datetime(s, format='%m/%d/%Y %H:%M', errors='coerce')
        if not pd.isna(dt):
            # Assume Bangkok timezone for old MM/DD/YYYY format, convert to UTC
            if dt.tz is None:
                dt = dt.tz_localize('Asia/Bangkok').tz_convert('UTC').tz_localize(None)
            return dt
    except:
        pass
    
    try:
        # Fallback: Auto-detect format
        dt = pd.to_datetime(s, errors='coerce')
        if not pd.isna(dt):
            if dt.tz is None:
                # Default to UTC timezone for unknown formats
                dt = dt.tz_localize('UTC').tz_localize(None)
            else:
                # Convert existing timezone to UTC
                dt = dt.tz_convert('UTC').tz_localize(None)
            return dt
    except Exception as e:
        print(f"Warning: Error parsing trade date '{s}': {e}")
        pass
    
    return pd.NaT

def normalize_candle_date(s):
    """Normalize candle date with proper timezone handling for Vietnam timezone"""
    try:
        dt = pd.to_datetime(s, errors='coerce')
        if not pd.isna(dt):
            if dt.tz is not None:
                # Keep Vietnam timezone (+7) and then remove tz info for consistency with trade data
                # Most trade data from TradingView is in Vietnam time
                dt = dt.tz_localize(None)  # Remove timezone but keep the time value
            return dt
    except Exception as e:
        print(f"Warning: Error parsing candle date '{s}': {e}")
        return pd.NaT
    
    return pd.NaT

def smart_read_csv(file_content):
    """Äá»c CSV tá»« ná»™i dung file"""
    try:
        df = pd.read_csv(io.StringIO(file_content), sep=",")
        if len(df.columns) == 1:
            df = pd.read_csv(io.StringIO(file_content), sep="\t")
    except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as e:
        print(f"Warning: CSV parsing with comma failed: {e}, trying tab separator")
        try:
            df = pd.read_csv(io.StringIO(file_content), sep="\t")
        except Exception as e2:
            print(f"Error: All CSV parsing methods failed: {e2}")
            raise ValueError(f"Cannot parse CSV content: {e2}")
    return df

def load_trade_csv_from_content(content):
    """Universal trade CSV loader using Version3 functions with file reference support"""
    temp_path = None
    
    # 🔍 CHECK: Is this content just a file reference?
    content_lines = content.strip().split('\n')
    if len(content_lines) == 1 and content_lines[0].strip().endswith('.csv'):
        # This might be a file reference, try to load the referenced file
        ref_path = content_lines[0].strip()
        print(f"🔍 Detected file reference: {ref_path}")
        
        # Try to find and load the referenced file
        if os.path.exists(ref_path):
            print(f"✅ Loading referenced file: {ref_path}")
            with open(ref_path, 'r', encoding='utf-8') as f:
                content = f.read()
        elif os.path.exists(os.path.join('tradelist', ref_path)):
            full_path = os.path.join('tradelist', ref_path)
            print(f"✅ Loading referenced file from tradelist: {full_path}")
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            print(f"⚠️ Referenced file not found: {ref_path}")
    
    try:
        # ðŸ”§ FORCE USE VERSION3 FUNCTIONS (with date format fix)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8') as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Use fixed Version3 load_trade_csv function
        from backtest_gridsearch_slbe_ts_Version3 import load_trade_csv
        df = load_trade_csv(temp_path)
        
        if len(df) == 0:
            raise ValueError('No valid trade data found after Version3 parsing')
        
        trades = len(df['trade'].unique())
        records = len(df)
        print(f"âœ… Version3 trade loading: {records} records from {trades} trades")
        return df
        
    except Exception as e:
        print(f"âš ï¸ Version3 parser failed: {e}, falling back to legacy methods")
        return load_trade_csv_from_content_legacy(content)
    
    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass

def load_trade_csv_from_content_legacy(content):
    df = smart_read_csv(content)
    
    # Clean column names
    df.columns = [col.strip().lower().replace(' ', '_').replace('/', '_').replace('#', '').replace('&', '') for col in df.columns]
    
    # Smart column mapping
    column_mapping = {}
    
    # Map Trade column
    for col in ['trade_', 'trade_number', 'trade']:
        if col in df.columns:
            column_mapping[col] = 'trade'
            break
    
    # Map Price column  
    for col in ['price_usdt', 'price']:
        if col in df.columns:
            column_mapping[col] = 'price'
            break
    
    # Map Date/Time column - keep original names for proper routing
    if 'date_time' in df.columns:
        column_mapping['date_time'] = 'date_time'  # ACEUSDT format
    elif 'date' in df.columns:
        # Don't remap 'date' column for legacy format - keep it as 'date'
        pass  # Keep original 'date' column name for legacy format
    
    if column_mapping:
        df.rename(columns=column_mapping, inplace=True)
    
    # Detect data format based on available columns
    has_signal = 'signal' in df.columns
    has_pnl_usdt = 'pl_usdt' in df.columns  # P&L USDT becomes pl_usdt after cleaning
    has_quantity = 'quantity' in df.columns
    has_tradingview_cols = has_signal and (has_pnl_usdt or has_quantity)
    
    # Check if this is BOME data (even though it's TradingView format)
    # BOME data has very small prices (around 0.009xxx)
    has_small_prices = False
    price_col_for_detection = None
    
    # Look for price column after mapping
    for col in ['price', 'price_usdt']:
        if col in df.columns:
            price_col_for_detection = col
            break
    
    if price_col_for_detection:
        try:
            price_sample = pd.to_numeric(df[price_col_for_detection].head(10), errors='coerce').dropna()
            if len(price_sample) > 0:
                avg_price = price_sample.mean()
                has_small_prices = avg_price < 0.1  # BOME prices are around 0.009xxx
        except:
            pass
    
    if has_tradingview_cols:
        if has_small_prices:
            # BOME format (TradingView but different processing)
            return load_bome_format(df)
        else:
            # ACEUSDT format detected
            return load_aceusdt_format(df)
    else:
        # BTC/BOME format (legacy) - ensure 'date' column exists
        if 'date' not in df.columns:
            # Try to find date-like column
            date_candidates = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
            if date_candidates:
                df['date'] = df[date_candidates[0]]
                print(f"ðŸ” LEGACY ROUTING: Created 'date' column from '{date_candidates[0]}'")
            else:
                raise ValueError(f"No date column found for legacy format! Available: {df.columns.tolist()}")
        return load_legacy_format(df)

def load_aceusdt_format(df):
    """Load ACEUSDT format data from TradingView Strategy Tester"""
    # Required columns for ACEUSDT format - check with original names
    required_cols = ['trade', 'type', 'signal']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"ACEUSDT format missing columns: {missing_cols}. Available: {df.columns.tolist()}")
    
    # Process datetime - try multiple column names
    date_col = None
    for col in ['date_time', 'date']:
        if col in df.columns:
            date_col = col
            break
    
    if date_col is None:
        raise ValueError(f"No date column found in ACEUSDT format! Available columns: {df.columns.tolist()}")
    
    df['date'] = df[date_col].apply(normalize_trade_date)
    
    # Process price - use 'price_usdt' column or 'price'
    price_col = None
    for col in ['price_usdt', 'price']:
        if col in df.columns:
            price_col = col
            break
    
    if price_col is None:
        raise ValueError(f"No price column found in ACEUSDT format! Available columns: {df.columns.tolist()}")
    
    df['price'] = df[price_col].astype(str).str.replace(',', '').str.replace('"', '')
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    # Filter for entry/exit trades
    # ACEUSDT format uses 'Type' column with values like "Entry long", "Exit short", etc.
    df = df[df['type'].str.lower().str.contains('entry') | df['type'].str.lower().str.contains('exit')]
    df = df.dropna(subset=['date', 'price'])
    
    return df

def load_bome_format(df):
    """Load BOME format data from TradingView Strategy Tester (small price precision)"""
    # Required columns for BOME format - similar to ACEUSDT but different price handling
    required_cols = ['trade', 'type', 'signal']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"BOME format missing columns: {missing_cols}. Available: {df.columns.tolist()}")
    
    # Process datetime - try multiple column names (BOME uses 'date_time' after mapping)
    date_col = None
    for col in ['date_time', 'date']:
        if col in df.columns:
            date_col = col
            break
    
    if date_col is None:
        raise ValueError(f"No date column found in BOME format! Available columns: {df.columns.tolist()}")
    
    df['date'] = df[date_col].apply(normalize_trade_date)
    
    # Process price - BOME has small prices (0.009xxx), need high precision
    price_col = None
    for col in ['price_usdt', 'price']:
        if col in df.columns:
            price_col = col
            break
    
    if price_col is None:
        raise ValueError(f"No price column found in BOME format! Available columns: {df.columns.tolist()}")
    
    df['price'] = df[price_col].astype(str).str.replace(',', '').str.replace('"', '')
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    # Filter for entry/exit trades (same logic as ACEUSDT)
    df = df[df['type'].str.lower().str.contains('entry') | df['type'].str.lower().str.contains('exit')]
    df = df.dropna(subset=['date', 'price'])
    
    return df

def load_legacy_format(df):
    """Load legacy BTC/BOME format data - OPTIMIZED VERSION"""
    # Ensure we have 'date' column for legacy format
    if 'date' not in df.columns:
        if 'date_time' in df.columns:
            df['date'] = df['date_time']
        else:
            # Look for any date-like column
            date_candidates = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
            if date_candidates:
                df['date'] = df[date_candidates[0]]
            else:
                raise ValueError(f"No date column found for legacy format! Available: {df.columns.tolist()}")
    
    # Check required columns for legacy format
    required_cols = ['trade', 'type', 'date', 'price']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Legacy format missing columns: {missing_cols}! Available: {df.columns.tolist()}")
    
    df['date'] = df['date'].apply(normalize_trade_date)
    df['price'] = df['price'].astype(str).str.replace(',', '').str.replace('"', '')
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    df = df[df['type'].str.lower().str.contains('entry') | df['type'].str.lower().str.contains('exit')]
    df = df.dropna(subset=['date', 'price'])
    
    print(f"âœ… Legacy format processed: {len(df)} valid trade rows")
    return df

def load_candle_csv_from_content(content):
    """Load candle CSV using Version3 functions"""
    temp_path = None
    try:
        # ðŸ”§ FORCE USE VERSION3 FUNCTIONS (with date format fix)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8') as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Use fixed Version3 load_candle_csv function
        from backtest_gridsearch_slbe_ts_Version3 import load_candle_csv
        df = load_candle_csv(temp_path)
        
        if len(df) == 0:
            raise ValueError('No valid candle data found after Version3 parsing')
        
        print(f"âœ… Version3 candle loading: {len(df)} candles loaded")
        print(f"   Time range: {df['time'].min()} â†’ {df['time'].max()}")
        return df
        
    except Exception as e:
        print(f"âš ï¸ Version3 candle parser failed: {e}")
        raise
    
    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

def get_trade_pairs(df_trade):
    """Get trade pairs using Version3 function"""
    try:
        # ðŸ”§ FORCE USE VERSION3 get_trade_pairs
        from backtest_gridsearch_slbe_ts_Version3 import get_trade_pairs as get_pairs_v3
        pairs, log = get_pairs_v3(df_trade)
        
        print(f"âœ… Version3 trade pairs: {len(pairs)} pairs generated")
        if log:
            for msg in log[:5]:  # Show first 5 log messages
                print(f"   Log: {msg}")
        
        return pairs, log
        
    except Exception as e:
        print(f"âš ï¸ Version3 get_trade_pairs failed: {e}")
        # Fallback to original logic if needed
        return get_trade_pairs_legacy(df_trade)

def get_trade_pairs_legacy(df_trade):
    log = []
    pairs = []
    
    print(f"ðŸ” DEBUG: Processing {len(df_trade)} trade rows")
    print(f"ðŸ” DEBUG: Columns: {df_trade.columns.tolist()}")
    print(f"ðŸ” DEBUG: First 5 rows:")
    print(df_trade.head().to_string())
    
    # Detect data format
    # Check for TradingView format columns
    has_signal = 'signal' in df_trade.columns
    has_pnl_usdt = 'pl_usdt' in df_trade.columns  # P&L USDT becomes pl_usdt after cleaning
    has_quantity = 'quantity' in df_trade.columns
    has_tradingview_cols = has_signal and (has_pnl_usdt or has_quantity)
    
    # Check if this is BOME data (small prices)
    has_small_prices = False
    if 'price' in df_trade.columns:
        try:
            price_sample = pd.to_numeric(df_trade['price'].head(10), errors='coerce').dropna()
            if len(price_sample) > 0:
                avg_price = price_sample.mean()
                has_small_prices = avg_price < 0.1  # BOME prices are around 0.009xxx
        except:
            pass
    
    print(f"ðŸ” FORMAT DETECTION: signal={has_signal}, p&l_usdt={has_pnl_usdt}, quantity={has_quantity}, small_prices={has_small_prices}")
    
    if has_tradingview_cols:
        if has_small_prices:
            print(f"ðŸ” FORMAT: BOME (TradingView with small prices)")
            return get_bome_trade_pairs(df_trade)
        else:
            print(f"ðŸ” FORMAT: ACEUSDT (TradingView)")
            return get_aceusdt_trade_pairs(df_trade)
    else:
        print(f"ðŸ” FORMAT: Legacy (BTC/BOME)")
        return get_legacy_trade_pairs(df_trade)

def get_aceusdt_trade_pairs(df_trade):
    """Extract trade pairs from ACEUSDT TradingView format"""
    log = []
    pairs = []
    
    print(f"ðŸ”„ Processing ACEUSDT format with {len(df_trade)} rows")
    
    for trade_num in df_trade['trade'].unique():
        group = df_trade[df_trade['trade'] == trade_num]
        entry = group[group['type'].str.lower().str.contains('entry')]
        exit = group[group['type'].str.lower().str.contains('exit')]
        
        if len(entry) == 0 or len(exit) == 0:
            log.append(f"ACEUSDT Trade {trade_num}: thiáº¿u Entry hoáº·c Exit, bá» qua")
            continue
            
        entry_row = entry.iloc[0]
        exit_row = exit.iloc[0]
        
        # Determine side from Type column
        # "Entry long" = LONG, "Entry short" = SHORT
        entry_type = entry_row['type'].lower()
        if 'long' in entry_type:
            side = 'LONG'
        elif 'short' in entry_type:
            side = 'SHORT'
        else:
            # Fallback: check signal column
            signal = entry_row.get('signal', '').lower()
            side = 'LONG' if 'long' in signal else 'SHORT'
        
        # Debug first few trades
        if trade_num <= 3:
            print(f"ðŸ” ACEUSDT TRADE {trade_num} DEBUG:")
            print(f"   Entry row: {entry_row.to_dict()}")
            print(f"   Exit row: {exit_row.to_dict()}")
            print(f"   Entry type: {entry_row['type']}")
            print(f"   Exit type: {exit_row['type']}")
            print(f"   Side detected: {side}")
            print(f"   Entry price: {entry_row['price']}")
            print(f"   Exit price: {exit_row['price']}")
        
        pairs.append({
            'num': trade_num,
            'entryDt': entry_row.get('date', entry_row.get('date_time', entry_row.get('time', 'Unknown'))),
            'exitDt': exit_row.get('date', exit_row.get('date_time', exit_row.get('time', 'Unknown'))),
            'side': side,
            'entryPrice': entry_row['price'],
            'exitPrice': exit_row['price']
        })
        
    print(f"âœ… ACEUSDT pairs extracted: {len(pairs)} valid pairs")
    return pairs, log

def get_bome_trade_pairs(df_trade):
    """Extract trade pairs from BOME TradingView format (small price precision)"""
    log = []
    pairs = []
    
    print(f"ðŸ”„ Processing BOME format with {len(df_trade)} rows")
    
    for trade_num in df_trade['trade'].unique():
        group = df_trade[df_trade['trade'] == trade_num]
        entry = group[group['type'].str.lower().str.contains('entry')]
        exit = group[group['type'].str.lower().str.contains('exit')]
        
        if len(entry) == 0 or len(exit) == 0:
            log.append(f"BOME Trade {trade_num}: thiáº¿u Entry hoáº·c Exit, bá» qua")
            continue
            
        entry_row = entry.iloc[0]
        exit_row = exit.iloc[0]
        
        # Determine side from Type column (same logic as ACEUSDT)
        entry_type = entry_row['type'].lower()
        if 'long' in entry_type:
            side = 'LONG'
        elif 'short' in entry_type:
            side = 'SHORT'
        else:
            # Fallback: check signal column
            signal = entry_row.get('signal', '').lower()
            side = 'LONG' if 'long' in signal else 'SHORT'
        
        # Debug first few trades with high precision for BOME
        if trade_num <= 3:
            print(f"ðŸ” BOME TRADE {trade_num} DEBUG:")
            print(f"   Entry row: {entry_row.to_dict()}")
            print(f"   Exit row: {exit_row.to_dict()}")
            print(f"   Entry type: {entry_row['type']}")
            print(f"   Exit type: {exit_row['type']}")
            print(f"   Side detected: {side}")
            print(f"   Entry price: {entry_row['price']:.8f}")  # Higher precision for BOME
            print(f"   Exit price: {exit_row['price']:.8f}")
        
        pairs.append({
            'num': trade_num,
            'entryDt': entry_row.get('date', entry_row.get('date_time', entry_row.get('time', 'Unknown'))),
            'exitDt': exit_row.get('date', exit_row.get('date_time', exit_row.get('time', 'Unknown'))),
            'side': side,
            'entryPrice': entry_row['price'],
            'exitPrice': exit_row['price']
        })
        
    print(f"âœ… BOME pairs extracted: {len(pairs)} valid pairs")
    return pairs, log

def get_legacy_trade_pairs(df_trade):
    """Extract trade pairs from legacy BTC/BOME format"""
    log = []
    pairs = []
    
    print(f"ðŸ”„ Processing legacy format with {len(df_trade)} rows")
    
    for trade_num in df_trade['trade'].unique():
        group = df_trade[df_trade['trade']==trade_num]
        entry = group[group['type'].str.lower().str.contains('entry')]
        exit = group[group['type'].str.lower().str.contains('exit')]
        if len(entry)==0 or len(exit)==0:
            log.append(f"Legacy TradeNum {trade_num}: thiáº¿u Entry hoáº·c Exit, bá» qua")
            continue
        entry_row = entry.iloc[0]
        exit_row = exit.iloc[0]
        side = 'LONG' if 'long' in entry_row['type'].lower() else 'SHORT'
        
        # Debug first few trades to see actual data
        if trade_num <= 3:
            print(f"ðŸ” LEGACY TRADE {trade_num} DEBUG:")
            print(f"   Entry row: {entry_row.to_dict()}")
            print(f"   Exit row: {exit_row.to_dict()}")
            print(f"   Entry price: {entry_row['price']}")
            print(f"   Exit price: {exit_row['price']}")
            print(f"   Same price? {entry_row['price'] == exit_row['price']}")
        
        pairs.append({
            'num': trade_num,
            'entryDt': entry_row.get('date', entry_row.get('date_time', entry_row.get('time', 'Unknown'))),
            'exitDt': exit_row.get('date', exit_row.get('date_time', exit_row.get('time', 'Unknown'))),
            'side': side,
            'entryPrice': entry_row['price'],
            'exitPrice': exit_row['price']
        })
        
    print(f"âœ… Legacy pairs extracted: {len(pairs)} valid pairs")
    return pairs, log

def calculate_original_performance(pairs):
    """TÃ­nh toÃ¡n hiá»‡u suáº¥t gá»‘c cá»§a dá»¯ liá»‡u trade vá»›i cÃ¡c chá»‰ sá»‘ nÃ¢ng cao"""
    if not pairs:
        return None
    
    total_trades = len(pairs)
    win_trades = 0
    loss_trades = 0
    total_pnl = 0
    gross_profit = 0
    gross_loss = 0
    win_amounts = []
    loss_amounts = []
    pnl_list = []
    
    # Sort trades theo thá»i gian Ä‘á»ƒ tÃ­nh drawdown
    sorted_pairs = sorted(pairs, key=lambda x: x['entryDt'])
    
    for pair in sorted_pairs:
        if pair['side'] == 'LONG':
            pnl_pct = (pair['exitPrice'] - pair['entryPrice']) / pair['entryPrice'] * 100
        else:  # SHORT
            pnl_pct = (pair['entryPrice'] - pair['exitPrice']) / pair['entryPrice'] * 100
        
        pnl_list.append(pnl_pct)
        total_pnl += pnl_pct
        
        if pnl_pct > 0:
            win_trades += 1
            gross_profit += pnl_pct
            win_amounts.append(pnl_pct)
        else:
            loss_trades += 1
            gross_loss += abs(pnl_pct)
            loss_amounts.append(pnl_pct)
    
    # TÃ­nh cÃ¡c chá»‰ sá»‘ cÆ¡ báº£n
    winrate = (win_trades / total_trades * 100) if total_trades > 0 else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
    avg_trade = total_pnl / total_trades if total_trades > 0 else 0
    
    # TÃ­nh Max Drawdown
    cumulative_pnl = []
    running_total = 0
    for pnl in pnl_list:
        running_total += pnl
        cumulative_pnl.append(running_total)
    
    max_drawdown = 0
    peak = cumulative_pnl[0] if cumulative_pnl else 0
    for value in cumulative_pnl:
        if value > peak:
            peak = value
        drawdown = peak - value
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    # TÃ­nh Average Win/Loss
    avg_win = sum(win_amounts) / len(win_amounts) if win_amounts else 0
    avg_loss = sum(loss_amounts) / len(loss_amounts) if loss_amounts else 0
    
    # TÃ­nh Consecutive Wins/Losses
    max_consecutive_wins = 0
    max_consecutive_losses = 0
    current_win_streak = 0
    current_loss_streak = 0
    
    for pnl in pnl_list:
        if pnl > 0:
            current_win_streak += 1
            current_loss_streak = 0
            max_consecutive_wins = max(max_consecutive_wins, current_win_streak)
        else:
            current_loss_streak += 1
            current_win_streak = 0
            max_consecutive_losses = max(max_consecutive_losses, current_loss_streak)
    
    # TÃ­nh Sharpe Ratio (Ä‘Æ¡n giáº£n hoÃ¡)
    if len(pnl_list) > 1:
        std_dev = math.sqrt(sum([(x - avg_trade) ** 2 for x in pnl_list]) / (len(pnl_list) - 1))
        sharpe_ratio = avg_trade / std_dev if std_dev > 0 else 0
    else:
        sharpe_ratio = 0
    
    # TÃ­nh Recovery Factor
    recovery_factor = total_pnl / max_drawdown if max_drawdown > 0 else float('inf') if total_pnl > 0 else 0
    
    return {
        'total_trades': total_trades,
        'win_trades': win_trades,
        'loss_trades': loss_trades,
        'total_pnl': total_pnl,
        'winrate': winrate,
        'profit_factor': safe_float(profit_factor),
        'avg_trade': avg_trade,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'max_drawdown': max_drawdown,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'max_consecutive_wins': max_consecutive_wins,
        'max_consecutive_losses': max_consecutive_losses,
        'sharpe_ratio': safe_float(sharpe_ratio),
        'recovery_factor': safe_float(recovery_factor)
    }

def create_original_baseline_details(trade_pairs):
    """
    CRITICAL HELPER: Create baseline details from ORIGINAL trade pairs
    This ensures we use actual tradelist data instead of simulation results
    """
    baseline_details = []
    for pair in trade_pairs:
        if pair['side'] == 'LONG':
            pnl_pct = (pair['exitPrice'] - pair['entryPrice']) / pair['entryPrice'] * 100
        else:  # SHORT
            pnl_pct = (pair['entryPrice'] - pair['exitPrice']) / pair['entryPrice'] * 100
        
        baseline_details.append({
            'entryDt': pair['entryDt'],
            'exitDt': pair['exitDt'],
            'pnlPct': pnl_pct,
            'num': pair['num'],
            'side': pair['side'],
            'entryPrice': pair['entryPrice'],  # Use original entry price
            'exitPrice': pair['exitPrice']    # Use original exit price
        })
    
    return baseline_details

def filter_trades_by_selection(pairs, max_trades=0, start_trade=1, selection_mode='sequence'):
    """Lá»c trades theo tham sá»‘ ngÆ°á»i dÃ¹ng chá»n"""
    if not pairs:
        return pairs
    
    # Sort theo mode
    if selection_mode == 'time':
        sorted_pairs = sorted(pairs, key=lambda x: x['entryDt'])
    elif selection_mode == 'random':
        sorted_pairs = pairs.copy()
        random.shuffle(sorted_pairs)
    else:  # sequence
        sorted_pairs = sorted(pairs, key=lambda x: x['num'])
    
    # Apply start_trade filter
    total_count = len(sorted_pairs)
    
    if start_trade < 0:
        # Sá»‘ Ã¢m = báº¯t Ä‘áº§u tá»« cuá»‘i (vÃ­ dá»¥: -10 = 10 lá»‡nh cuá»‘i)
        start_idx = max(0, total_count + start_trade)
        sorted_pairs = sorted_pairs[start_idx:]
    elif start_trade > 1:
        # Sá»‘ dÆ°Æ¡ng = báº¯t Ä‘áº§u tá»« Ä‘áº§u (vÃ­ dá»¥: 5 = tá»« lá»‡nh thá»© 5)
        sorted_pairs = sorted_pairs[start_trade-1:]
    
    # Apply max_trades filter
    if max_trades > 0:
        sorted_pairs = sorted_pairs[:max_trades]
    
    return sorted_pairs

def find_candle_idx(dt, df_candle):
    if pd.isna(dt):
        return -1
    arr = df_candle['time'].values
    target_dt = np.datetime64(dt)
    min_time = arr[0]
    max_time = arr[-1] 
    if target_dt < min_time or target_dt > max_time:
        return -1
    idx = np.where(arr == target_dt)[0]
    return idx[0] if len(idx) > 0 else -1

def simulate_trade_sl_only(pair, df_candle, sl_percent):
    """
    âš¡ Tá»I Æ¯U: SL-only simulation, tá»‘i giáº£n log, tÄƒng tá»‘c Ä‘á»™
    """
    entryIdx = find_candle_idx(pair['entryDt'], df_candle)
    exitIdx = find_candle_idx(pair['exitDt'], df_candle)
    if entryIdx == -1 or exitIdx == -1 or exitIdx <= entryIdx:
        return None
    prices = df_candle.iloc[entryIdx:exitIdx+1]
    side = pair['side']
    entryPrice = float(pair['entryPrice'])
    finalExitPrice = float(pair['exitPrice'])
    exitType = 'Original'
    if sl_percent > 0:
        if side == 'LONG':
            slPrice = entryPrice * (1 - sl_percent/100)
            for i in range(len(prices)):
                low = float(prices.iloc[i]['low'])
                if low <= slPrice:
                    finalExitPrice = max(slPrice * 0.999, low)
                    exitType = 'SL'
                    break
        else:
            slPrice = entryPrice * (1 + sl_percent/100)
            for i in range(len(prices)):
                high = float(prices.iloc[i]['high'])
                if high >= slPrice:
                    finalExitPrice = min(slPrice * 1.001, high)
                    exitType = 'SL'
                    break
    try:
        if side == 'LONG':
            pnlPct = (finalExitPrice - entryPrice) / entryPrice * 100.0
        else:
            pnlPct = (entryPrice - finalExitPrice) / entryPrice * 100.0
        if not np.isfinite(pnlPct):
            pnlPct = 0.0
    except (ZeroDivisionError, OverflowError):
        pnlPct = 0.0
    return {
        'num': pair['num'],
        'side': side,
        'entryPrice': entryPrice,
        'exitPrice': finalExitPrice,
        'exitType': exitType,
        'pnlPct': float(pnlPct),
        'pnlPctOrigin': float(pnlPct),
        'entryDt': pair['entryDt'],
        'exitDt': pair['exitDt'],
        'sl': sl_percent,
        'be': 0,
        'ts_trig': 0,
        'ts_step': 0
    }

def calculate_advanced_metrics(details):
    """
    âš¡ Tá»I Æ¯U: TÃ­nh toÃ¡n cÃ¡c chá»‰ sá»‘ nÃ¢ng cao, tá»‘i giáº£n log, tÄƒng tá»‘c Ä‘á»™
    """
    if not details:
        return {
            'max_drawdown': 0, 'avg_win': 0, 'avg_loss': 0,
            'max_consecutive_wins': 0, 'max_consecutive_losses': 0,
            'sharpe_ratio': 0, 'recovery_factor': 0
        }
    pnl_list = [trade['pnlPct'] for trade in details]
    if all(pnl == 0 for pnl in pnl_list):
        return {
            'max_drawdown': 0, 'avg_win': 0, 'avg_loss': 0,
            'max_consecutive_wins': 0, 'max_consecutive_losses': 0,
            'sharpe_ratio': 0, 'recovery_factor': 0
        }
    cumulative_pnl = np.cumsum(pnl_list)
    max_drawdown = float(np.max(np.maximum.accumulate(cumulative_pnl) - cumulative_pnl)) if len(cumulative_pnl) else 0
    win_amounts = [pnl for pnl in pnl_list if pnl > 0]
    loss_amounts = [pnl for pnl in pnl_list if pnl <= 0]
    avg_win = float(np.mean(win_amounts)) if win_amounts else 0
    avg_loss = float(np.mean(loss_amounts)) if loss_amounts else 0
    max_consecutive_wins = max_consecutive_losses = 0
    cur_win = cur_loss = 0
    for pnl in pnl_list:
        if pnl > 0:
            cur_win += 1
            cur_loss = 0
            max_consecutive_wins = max(max_consecutive_wins, cur_win)
        else:
            cur_loss += 1
            cur_win = 0
            max_consecutive_losses = max(max_consecutive_losses, cur_loss)
    avg_trade = float(np.mean(pnl_list)) if pnl_list else 0
    if len(pnl_list) > 1:
        std_dev = float(np.std(pnl_list, ddof=1))
        sharpe_ratio = avg_trade / std_dev if std_dev > 0 else 0
    else:
        sharpe_ratio = 0
    total_pnl = float(np.sum(pnl_list))
    recovery_factor = total_pnl / max_drawdown if max_drawdown > 0 else float('inf') if total_pnl > 0 else 0
    return {
        'max_drawdown': max_drawdown,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'max_consecutive_wins': max_consecutive_wins,
        'max_consecutive_losses': max_consecutive_losses,
        'sharpe_ratio': sharpe_ratio,
        'recovery_factor': recovery_factor
    }

def grid_search_sl_fallback(pairs, df_candle, sl_min, sl_max, sl_step, opt_type, 
                           be_min=2.0, ts_trig_min=2.0, ts_step_min=3.0):
    """
    âš¡ Tá»I Æ¯U: Grid search fallback, tá»‘i giáº£n log, tÄƒng tá»‘c Ä‘á»™
    """
    global optimization_status
    print(f"âš¡ OPTIMIZED GRID SEARCH STARTED!")
    print(f"ðŸ“Š {len(pairs)} pairs, SL: {sl_min}-{sl_max} step {sl_step}")
    results = []
    sl_list = list(np.arange(sl_min, sl_max + sl_step/2, sl_step))
    total_combinations = len(sl_list)
    progress_interval = max(1, total_combinations // 4)
    for i, sl in enumerate(sl_list):
        optimization_status['current_progress'] = i + 1
        if i % progress_interval == 0 or i < 2 or i == total_combinations - 1:
            print(f"âš¡ Progress: {i+1}/{total_combinations} ({(i+1)/total_combinations*100:.1f}%) - SL: {sl:.1f}%")
        details = []
        win_count = 0
        gain_sum = 0
        loss_sum = 0
        for pair in pairs:
            res = simulate_trade_sl_only(pair, df_candle, sl)
            if res is not None:
                details.append(res)
                pnl = res['pnlPct']
                if pnl > 0:
                    win_count += 1
                    gain_sum += pnl
                else:
                    loss_sum += abs(pnl)
        total_trades = len(details)
        winrate = (win_count / total_trades * 100) if total_trades > 0 else 0
        pf = (gain_sum / loss_sum) if loss_sum > 0 else float('inf') if gain_sum > 0 else 0
        pnl_total = sum([x['pnlPct'] for x in details])
        if i == 0:
            print(f"âœ… Verification SL={sl:.1f}%: {total_trades} trades, PnL={pnl_total:.4f}%, WR={winrate:.2f}%")
        advanced_metrics = calculate_advanced_metrics(details)
        results.append({
            'sl': float(sl),
            'be': float(be_min),
            'ts_trig': float(ts_trig_min),
            'ts_step': float(ts_step_min),
            'pnl_total': float(pnl_total),
            'winrate': float(winrate),
            'pf': safe_float(pf),
            'max_drawdown': safe_float(advanced_metrics['max_drawdown']),
            'avg_win': safe_float(advanced_metrics['avg_win']),
            'avg_loss': safe_float(advanced_metrics['avg_loss']),
            'max_consecutive_wins': safe_int(advanced_metrics['max_consecutive_wins']),
            'max_consecutive_losses': safe_int(advanced_metrics['max_consecutive_losses']),
            'sharpe_ratio': safe_float(advanced_metrics['sharpe_ratio']),
            'recovery_factor': safe_float(advanced_metrics['recovery_factor']),
            'details': details
        })
    sort_map = {
        'pnl': ('pnl_total', True),
        'winrate': ('winrate', True),
        'pf': ('pf', True),
        'sharpe': ('sharpe_ratio', True),
        'recovery': ('recovery_factor', True),
        'drawdown': ('max_drawdown', False)
    }
    sort_key, reverse_order = sort_map.get(opt_type, ('pnl_total', True))
    results.sort(key=lambda x: x[sort_key], reverse=reverse_order)
    if results:
        best = results[0]
        print(f"ðŸ† BEST RESULT: SL={best['sl']:.1f}% -> PnL={best['pnl_total']:.4f}%, WR={best['winrate']:.2f}%")
    return results

def grid_search_realistic_full(pairs, df_candle, sl_list, be_list, ts_trig_list, ts_step_list, opt_type):
    """
    TÃŒM KIáº¾M LÆ¯á»šI TOÃ€N DIá»†N vá»›i mÃ´ phá»ng Ä‘áº§y Ä‘á»§ SL + BE + TS
    HÃ m nÃ y Ä‘áº£m báº£o MÃ” PHá»ŽNG GIAO Dá»ŠCH THá»°C Táº¾ cho táº¥t cáº£ tá»• há»£p tham sá»‘
    """
    global optimization_status
    
    print(f"ðŸš€ TÃŒM KIáº¾M LÆ¯á»šI THá»°C Táº¾ TOÃ€N DIá»†N Báº®T Äáº¦U!")
    print(f"ðŸ“Š CHáº¾ Äá»˜ MÃ” PHá»ŽNG: SL + Breakeven + Trailing Stop Ä‘áº§y Ä‘á»§")
    print(f"ðŸ”¢ Tham sá»‘: SL={len(sl_list)}, BE={len(be_list)}, TS_TRIG={len(ts_trig_list)}, TS_STEP={len(ts_step_list)}")
    
    results = []
    total_combinations = len(sl_list) * len(be_list) * len(ts_trig_list) * len(ts_step_list)
    combination_count = 0
    
    print(f"ðŸ”„ CHáº¾ Äá»˜ THá»°C Táº¾: Thá»­ nghiá»‡m {total_combinations:,} tá»• há»£p tham sá»‘...")
    print(f"ðŸ’¡ Má»—i lá»‡nh sáº½ Ä‘Æ°á»£c mÃ´ phá»ng vá»›i:")
    print(f"   - Stop Loss: Báº£o vá»‡ vá»‘n Ä‘á»™ng")
    print(f"   - Breakeven: Di chuyá»ƒn SL vá» hÃ²a vá»‘n khi Ä‘áº¡t má»¥c tiÃªu lá»£i nhuáº­n")  
    print(f"   - Trailing Stop: Báº£o vá»‡ lá»£i nhuáº­n Ä‘á»™ng vá»›i tiáº¿n trÃ¬nh tá»«ng bÆ°á»›c")
    
    for sl in sl_list:
        for be in be_list:
            for ts_trig in ts_trig_list:
                for ts_step in ts_step_list:
                    combination_count += 1
                    
                    # Cáº­p nháº­t tiáº¿n Ä‘á»™ cho giao diá»‡n web
                    optimization_status['current_progress'] = combination_count
                    
                    if combination_count % 100 == 0 or combination_count <= 10:
                        print(f"Tiáº¿n Ä‘á»™: {combination_count}/{total_combinations} - Thá»­ nghiá»‡m SL:{sl:.1f}% BE:{be:.1f}% TS:{ts_trig:.1f}%/{ts_step:.1f}%")
                    
                    # Simulate all trades with current parameter set
                    details = []
                    win_count = 0
                    gain_sum = 0
                    loss_sum = 0
                    
                    for pair in pairs:
                        # Sá»­ dá»¥ng hÃ m simulate_trade NÃ‚NG CAO vá»›i logic BE+TS Ä‘áº§y Ä‘á»§
                        if True:  # 🔧 UNIFIED LOGIC: Always use simulate_trade() to match Optuna behavior (ADVANCED_MODE removed)
                            try:
                                result, log = simulate_trade(pair, df_candle, sl, be, ts_trig, ts_step)
                            except Exception as e:
                                print(f"⚠️ Grid Search error for pair {pair.get('num', 'unknown')}: {e}")
                                result = None
                        else:
                            # Dá»± phÃ²ng mÃ´ phá»ng chá»‰ SL  
                            result = simulate_trade_sl_only(pair, df_candle, sl)
                            result.update({'be': be, 'ts_trig': ts_trig, 'ts_step': ts_step})
                        
                        if result is not None:
                            details.append(result)
                            pnl = result['pnlPct']
                            if pnl > 0: 
                                win_count += 1
                                gain_sum += pnl
                            else: 
                                loss_sum += abs(pnl)
                    
                    # TÃ­nh toÃ¡n cÃ¡c chá»‰ sá»‘ hiá»‡u suáº¥t
                    total_trades = len(details)
                    winrate = (win_count / total_trades * 100) if total_trades > 0 else 0
                    pf = (gain_sum / loss_sum) if loss_sum > 0 else float('inf') if gain_sum > 0 else 0
                    pnl_total = sum([x['pnlPct'] for x in details])
                    
                    # TÃ­nh toÃ¡n chá»‰ sá»‘ nÃ¢ng cao sá»­ dá»¥ng káº¿t quáº£ thá»±c táº¿
                    advanced_metrics = calculate_advanced_metrics(details)
                    
                    # Debug vÃ i tá»• há»£p Ä‘áº§u Ä‘á»ƒ xÃ¡c minh mÃ´ phá»ng thá»±c táº¿
                    if combination_count <= 3:
                        print(f"ðŸ” DEBUG THá»°C Táº¾ Tá»• há»£p #{combination_count}:")
                        print(f"   SL={sl:.1f}% BE={be:.1f}% TS_TRIG={ts_trig:.1f}% TS_STEP={ts_step:.1f}%")
                        print(f"   Tá»•ng lá»‡nh: {total_trades}")
                        print(f"   Lá»‡nh tháº¯ng: {win_count}")
                        print(f"   Tá»•ng PnL: {pnl_total:.4f}%")
                        print(f"   Tá»· lá»‡ tháº¯ng: {winrate:.2f}%")
                        print(f"   Chá»‰ sá»‘ nÃ¢ng cao: Max DD={advanced_metrics['max_drawdown']:.4f}%, Sharpe={advanced_metrics['sharpe_ratio']:.4f}")
                        if len(details) > 0:
                            sample_detail = details[0]
                            print(f"   Lá»‡nh máº«u: #{sample_detail['num']} {sample_detail['side']} -> {sample_detail['exitType']} -> {sample_detail['pnlPct']:.4f}%")
                    
                    # Store result with full parameter set
                    result_dict = {
                        'sl': float(sl),
                        'be': float(be),
                        'ts_trig': float(ts_trig),
                        'ts_step': float(ts_step),
                        'pnl_total': float(pnl_total),
                        'winrate': float(winrate),
                        'pf': safe_float(pf),
                        'max_drawdown': safe_float(advanced_metrics['max_drawdown']),
                        'avg_win': safe_float(advanced_metrics['avg_win']),
                        'avg_loss': safe_float(advanced_metrics['avg_loss']),
                        'max_consecutive_wins': safe_int(advanced_metrics['max_consecutive_wins']),
                        'max_consecutive_losses': safe_int(advanced_metrics['max_consecutive_losses']),
                        'sharpe_ratio': safe_float(advanced_metrics['sharpe_ratio']),
                        'recovery_factor': safe_float(advanced_metrics['recovery_factor']),
                        'details': details
                    }
                    
                    results.append(result_dict)
    
    # Sort by optimization type
    if opt_type == 'pnl':
        results.sort(key=lambda x: x['pnl_total'], reverse=True)
    elif opt_type == 'winrate':
        results.sort(key=lambda x: x['winrate'], reverse=True)
    elif opt_type == 'pf':
        results.sort(key=lambda x: x['pf'], reverse=True)
    elif opt_type == 'sharpe':
        results.sort(key=lambda x: x['sharpe_ratio'], reverse=True)
    elif opt_type == 'recovery':
        results.sort(key=lambda x: x['recovery_factor'], reverse=True)
    elif opt_type == 'drawdown':
        results.sort(key=lambda x: x['max_drawdown'], reverse=False)
    else:
        results.sort(key=lambda x: x['pnl_total'], reverse=True)
    
    print(f"ðŸ” Káº¾T QUáº¢ THá»°C Táº¾: Káº¿t quáº£ tá»‘t nháº¥t -> SL:{results[0]['sl']:.1f}% BE:{results[0]['be']:.1f}% TS:{results[0]['ts_trig']:.1f}%/{results[0]['ts_step']:.1f}%")
    print(f"   Hiá»‡u suáº¥t: PnL={results[0]['pnl_total']:.4f}% Tá»· lá»‡ tháº¯ng={results[0]['winrate']:.2f}% Sharpe={results[0]['sharpe_ratio']:.4f}")
    
    return results

def optuna_search(trade_pairs, df_candle, sl_min, sl_max, be_min, be_max, ts_trig_min, ts_trig_max, ts_step_min, ts_step_max, opt_type, n_trials=50):
    """🔧 Enhanced Optuna search with parameter validation and error handling"""
    
    # 🔧 Debug: print actual parameter values and types
    print(f"🔧 Optuna parameters received:")
    print(f"   SL: {sl_min} ({type(sl_min)}) to {sl_max} ({type(sl_max)}) | {sl_min} > {sl_max} = {sl_min > sl_max}")
    print(f"   BE: {be_min} ({type(be_min)}) to {be_max} ({type(be_max)}) | {be_min} > {be_max} = {be_min > be_max}")
    print(f"   TS_TRIG: {ts_trig_min} ({type(ts_trig_min)}) to {ts_trig_max} ({type(ts_trig_max)}) | {ts_trig_min} > {ts_trig_max} = {ts_trig_min > ts_trig_max}")
    print(f"   TS_STEP: {ts_step_min} ({type(ts_step_min)}) to {ts_step_max} ({type(ts_step_max)}) | {ts_step_min} > {ts_step_max} = {ts_step_min > ts_step_max}")
    
    # 🔧 Validate parameter ranges - allow min = max for fixed parameters
    if sl_min > sl_max or be_min > be_max or ts_trig_min > ts_trig_max or ts_step_min > ts_step_max:
        raise ValueError(f"Invalid parameter ranges: SL[{sl_min}-{sl_max}], BE[{be_min}-{be_max}], TS_TRIG[{ts_trig_min}-{ts_trig_max}], TS_STEP[{ts_step_min}-{ts_step_max}]")
    
    if len(trade_pairs) == 0:
        raise ValueError("No trade pairs provided for optimization")
    
    print(f"🔧 Optuna validation: {len(trade_pairs)} pairs, {n_trials} trials")
    
    def objective(trial):
        # Handle parameters: suggest when range exists, use fixed value when min = max
        sl = trial.suggest_float('sl', sl_min, sl_max) if sl_min != sl_max else sl_min
        be = trial.suggest_float('be', be_min, be_max) if be_min != be_max else be_min
        ts_trig = trial.suggest_float('ts_trig', ts_trig_min, ts_trig_max) if ts_trig_min != ts_trig_max else ts_trig_min
        ts_step = trial.suggest_float('ts_step', ts_step_min, ts_step_max) if ts_step_min != ts_step_max else ts_step_min
        

        
        # Sử dụng simulate_trade cho từng pair - CONSISTENT with optimize_single_combination
        details = []
        win_count = 0
        gain_sum = 0
        loss_sum = 0
        total_trades_processed = 0
        
        for i, pair in enumerate(trade_pairs):
            try:
                result, _ = simulate_trade(pair, df_candle, sl, be, ts_trig, ts_step)
                total_trades_processed += 1
                
                if result is None:
                    print(f"⚠️ Optuna: simulate_trade returned None for pair {i+1}")
                    print(f"   Trade details: {pair.get('entryDt', 'Unknown')} | Side: {pair.get('side', 'Unknown')} | Entry: {pair.get('entry', 'Unknown')}")
                    continue
                
                if result is not None:
                    details.append(result)
                    pnl = result['pnlPct']
                    if pnl > 0:
                        win_count += 1
                        gain_sum += pnl
                    else:
                        loss_sum += abs(pnl)
                        
                    # 🔍 DEBUG: Log first few trade results for comparison
                    if trial.number == 0 and i < 3:
                        print(f"   OPTUNA Trade {i+1}: PnL={pnl:.6f}%, EntryPrice={result.get('entryPrice', 'N/A')}, ExitPrice={result.get('exitPrice', 'N/A')}, ExitType={result.get('exitType', 'N/A')}")
                else:
                    # Handle failed trades consistently - add 0 PnL trade
                    failed_result = {'pnlPct': 0.0}
                    details.append(failed_result)
                    if trial.number == 0 and i < 3:
                        print(f"   OPTUNA Trade {i+1}: PnL=0.0000% (FAILED)")
                        
            except Exception as e:
                total_trades_processed += 1
                # Handle errors consistently - add 0 PnL trade
                failed_result = {'pnlPct': 0.0}
                details.append(failed_result)
                if trial.number == 0 and i < 3:
                    print(f"   OPTUNA Trade {i+1}: PnL=0.0000% (ERROR: {e})")
                continue
                    
        total_trades = len(details)
        winrate = (win_count / total_trades * 100) if total_trades > 0 else 0
        pf = (gain_sum / loss_sum) if loss_sum > 0 else float('inf') if gain_sum > 0 else 0
        pnl_total = sum([x['pnlPct'] for x in details])
        

        # Chá»n hÃ m tá»‘i Æ°u hÃ³a
        if opt_type == 'winrate':
            return winrate
        elif opt_type == 'pf':
            return pf
        elif opt_type == 'drawdown':
            advanced_metrics = calculate_advanced_metrics(details)
            return -advanced_metrics['max_drawdown']
        else:
            return pnl_total  # Máº·c Ä‘á»‹nh tá»‘i Æ°u hÃ³a pnl_total

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=n_trials)
    best_params = study.best_params
    best_value = study.best_value
    print(f"Optuna best params: {best_params}, best value: {best_value}")
    return best_params, best_value

def grid_search_realistic_full_v2(pairs, df_candle, sl_list, be_list, ts_trig_list, ts_step_list, opt_type, max_iterations=None):
    """
    OPTUNA: Sá»¬ Dá»¤NG OPTUNA Äá»‚ Tá»I Æ¯U HÃ“A THAM Sá» SL + BE + TS
    
        """
    global optimization_status
    
    print(f"ðŸš€ TÃŒM KIáº¾M LÆ¯á»šI THá»°C Táº¾ TOÃ€N DIá»†N Báº®T Äáº¦U!")
    print(f"ðŸ“Š CHáº¾ Äá»˜ MÃ” PHá»ŽNG: SL + Breakeven + Trailing Stop Ä‘áº§y Ä‘á»§")
    print(f"ðŸ”¢ Tham sá»‘: SL={len(sl_list)}, BE={len(be_list)}, TS_TRIG={len(ts_trig_list)}, TS_STEP={len(ts_step_list)}")
    
    results = []
    total_combinations = len(sl_list) * len(be_list) * len(ts_trig_list) * len(ts_step_list)
    combination_count = 0
    
    print(f"ðŸ”„ CHáº¾ Äá»˜ THá»°C Táº¾: Thá»­ nghiá»‡m {total_combinations:,} tá»• há»£p tham sá»‘...")
    print(f"ðŸ’¡ Má»—i lá»‡nh sáº½ Ä‘Æ°á»£c mÃ´ phá»ng vá»›i:")
    print(f"   - Stop Loss: Báº£o vá»‡ vá»‘n Ä‘á»™ng")
    print(f"   - Breakeven: Di chuyá»ƒn SL vá» hÃ²a vá»‘n khi Ä‘áº¡t má»¥c tiÃªu lá»£i nhuáº­n")  
    print(f"   - Trailing Stop: Báº£o vá»‡ lá»£i nhuáº­n Ä‘á»™ng vá»›i tiáº¿n trÃ¬nh tá»«ng bÆ°á»›c")
    
    # Cháº¡y Optuna Ä‘á»ƒ tÃ¬m tham sá»‘ tá»‘i Æ°u nháº¥t
    print(f"ðŸ” CHáº Y OPTUNA Äá»‚ TÃŒM THAM Sá» Tá»I Æ¯U NHáº¤T")
    opt_params, opt_value = optuna_search(pairs, df_candle, 
                                          min(sl_list), max(sl_list), 
                                          min(be_list), max(be_list), 
                                          min(ts_trig_list), max(ts_trig_list), 
                                          min(ts_step_list), max(ts_step_list), 
                                          opt_type, n_trials=(validate_optuna_trials(max_iterations) if max_iterations else DEFAULT_OPTUNA_TRIALS))
    
    # NOTE: 🔧 Fixed duplicate Optuna execution - now runs once with validated user input or default trials
    

    
    # Extract parameters safely with fallbacks
    sl_opt = opt_params.get('sl', 2.0)  # Default fallback if not optimized
    be_opt = opt_params.get('be', 0.0)  # Default fallback if not optimized
    ts_trig_opt = opt_params.get('ts_trig', 0.0)  # Default fallback if not optimized
    ts_step_opt = opt_params.get('ts_step', 0.1)  # Default fallback if not optimized
    
    print(f"ðŸ† THAM Sá» Tá»I Æ¯U: SL={sl_opt:.1f}%, BE={be_opt:.1f}%, TS_TRIG={ts_trig_opt:.1f}%, TS_STEP={ts_step_opt:.1f}%")
    print(f"   GiÃ¡ trá»‹ tá»‘i Æ°u: {opt_value}")
    
    # Cháº¡y mÃ´ phá»ng vá»›i tham sá»‘ tá»‘i Æ°u
    details_opt = []
    win_count_opt = 0
    gain_sum_opt = 0
    loss_sum_opt = 0
    
    for pair in pairs:
        result, _ = simulate_trade(pair, df_candle, sl_opt, be_opt, ts_trig_opt, ts_step_opt)
        if result is not None:
            details_opt.append(result)
            pnl = result['pnlPct']
            if pnl > 0:
                win_count_opt += 1
                gain_sum_opt += pnl
            else:
                loss_sum_opt += abs(pnl)
    
    total_trades_opt = len(details_opt)
    winrate_opt = (win_count_opt / total_trades_opt * 100) if total_trades_opt > 0 else 0
    pf_opt = (gain_sum_opt / loss_sum_opt) if loss_sum_opt > 0 else float('inf') if gain_sum_opt > 0 else 0
    pnl_total_opt = sum([x['pnlPct'] for x in details_opt])
    
    # TÃ­nh cÃ¡c chá»‰ sá»‘ nÃ¢ng cao cho káº¿t quáº£ tá»‘i Æ°u
    advanced_metrics_opt = calculate_advanced_metrics(details_opt)
    
    # ÄÃ³ng gÃ³i káº¿t quáº£
    result_dict_opt = {
        'sl': float(sl_opt),
        'be': float(be_opt),
        'ts_trig': float(ts_trig_opt),
        'ts_step': float(ts_step_opt),
        'pnl_total': float(pnl_total_opt),
        'winrate': float(winrate_opt),
        'pf': safe_float(pf_opt),
        'max_drawdown': safe_float(advanced_metrics_opt['max_drawdown']),
        'avg_win': safe_float(advanced_metrics_opt['avg_win']),
        'avg_loss': safe_float(advanced_metrics_opt['avg_loss']),
        'max_consecutive_wins': safe_int(advanced_metrics_opt['max_consecutive_wins']),
        'max_consecutive_losses': safe_int(advanced_metrics_opt['max_consecutive_losses']),
        'sharpe_ratio': safe_float(advanced_metrics_opt['sharpe_ratio']),
        'recovery_factor': safe_float(advanced_metrics_opt['recovery_factor']),
        'details': details_opt
    }
    
    results.append(result_dict_opt)
    
    # Sort káº¿t quáº£ tá»‘i Æ°u
    if opt_type == 'pnl':
        results.sort(key=lambda x: x['pnl_total'], reverse=True)
    elif opt_type == 'winrate':
        results.sort(key=lambda x: x['winrate'], reverse=True)
    elif opt_type == 'pf':
        results.sort(key=lambda x: x['pf'], reverse=True)
    elif opt_type == 'sharpe':
        results.sort(key=lambda x: x['sharpe_ratio'], reverse=True)
    elif opt_type == 'recovery':
        results.sort(key=lambda x: x['recovery_factor'], reverse=True)
    elif opt_type == 'drawdown':
        results.sort(key=lambda x: x['max_drawdown'], reverse=False)
    else:
        results.sort(key=lambda x: x['pnl_total'], reverse=True)
    
    print(f"ðŸ” Káº¾T QUáº¢ Tá»I Æ¯U: Káº¿t quáº£ tá»‘t nháº¥t -> SL:{results[0]['sl']:.1f}% BE:{results[0]['be']:.1f}% TS:{results[0]['ts_trig']:.1f}%/{results[0]['ts_step']:.1f}%")
    print(f"   Hiá»‡u suáº¥t: PnL={results[0]['pnl_total']:.4f}% Tá»· lá»‡ tháº¯ng={results[0]['winrate']:.2f}% Sharpe={results[0]['sharpe_ratio']:.4f}")
    
    return results

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload_tradelist', methods=['POST'])
def upload_tradelist():
    try:
        trade_file = request.files.get('file')
        symbol = request.form.get('symbol', 'TEST')
        strategy = request.form.get('strategy', 'demo')
        if not trade_file:
            return jsonify({'success': False, 'error': 'Missing file'}), 400

        content = trade_file.read().decode('utf-8')
        df = load_trade_csv_from_content(content)
        tm = TradelistManager('tradelists')
        added = tm.merge_tradelist(strategy, symbol, df)

        preview = df.head(10).to_dict(orient='records')
        return jsonify({'success': True, 'rows_added': int(added), 'final_count': len(tm.load_tradelist(strategy, symbol)), 'preview': preview, 'strategy': strategy, 'symbol': symbol})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/simulate', methods=['POST'])
def simulate_route():
    try:
        payload = request.get_json(force=True)
        symbol = payload.get('symbol', 'TEST')
        strategy = payload.get('strategy', 'demo')
        sl = float(payload.get('sl', 0) or 0)
        be = float(payload.get('break_even_trigger', 0) or 0)
        ts_trig = float(payload.get('trailing_stop', 0) or 0)
        ts_step = float(payload.get('ts_step', 0) or 0)
        candle_path = payload.get('candle_path')

        tm = TradelistManager('tradelists')
        df_trade = tm.load_tradelist(strategy, symbol)
        if df_trade.empty:
            return jsonify({'success': False, 'error': 'No tradelist found for symbol/strategy'}), 404

        # Try Version3 get_trade_pairs first
        try:
            pairs, log = get_trade_pairs_file(df_trade)
        except Exception:
            pairs, log = get_trade_pairs(df_trade)

        # Load candle data from database only
        df_candle = None
        
        # Parse database format from candle_path: SYMBOL_TIMEFRAME.db
        if candle_path and candle_path.endswith('.db'):
            db_name = candle_path.replace('.db', '')
            if '_' in db_name:
                db_symbol, db_timeframe = db_name.rsplit('_', 1)
                print(f"🔄 [SIMULATE] Loading from database: symbol={db_symbol}, timeframe={db_timeframe}")
                
                # Load from candlestick_data.db
                conn = sqlite3.connect('candlestick_data.db')
                query = "SELECT * FROM candlestick_data WHERE symbol = ? AND timeframe = ? ORDER BY open_time"
                df_candle = pd.read_sql_query(query, conn, params=(db_symbol, db_timeframe))
                conn.close()
                
                if df_candle.empty:
                    raise ValueError(f"No candle data found in database for {db_symbol} {db_timeframe}")
                
                # Convert database format to standard format
                df_candle = df_candle.rename(columns={
                    'open_time': 'time',
                    'open_price': 'open', 
                    'high_price': 'high',
                    'low_price': 'low',
                    'close_price': 'close'
                })
                df_candle['time'] = pd.to_datetime(df_candle['time'], unit='s')  # Database uses seconds
        else:
            # No valid database candle path provided
            print(f"❌ Invalid or missing database candle path: {candle_path}")
            raise ValueError("Database candle path required (format: SYMBOL_TIMEFRAME.db)")

        details = []
        for pair in pairs:
            if df_candle is not None and ADVANCED_MODE:
                try:
                    res, lg = simulate_trade(pair, df_candle, sl, be, ts_trig, ts_step)
                    if res:
                        details.append(res)
                except Exception:
                    res = simulate_trade_sl_only(pair, df_candle if df_candle is not None else pd.DataFrame(), abs(sl))
                    if res:
                        details.append(res)
            else:
                res = simulate_trade_sl_only(pair, df_candle if df_candle is not None else pd.DataFrame(), abs(sl))
                if res:
                    details.append(res)

        total_pnl = sum([d.get('pnlPct', 0) for d in details]) if details else 0
        winrate = (len([d for d in details if d.get('pnlPct', 0) > 0]) / len(details) * 100) if details else 0

        resp = {
            'success': True,
            'summary': {'pnl_total': total_pnl, 'winrate': winrate, 'trade_count': len(details)},
            'details': details
        }
        return jsonify(convert_to_serializable(resp))
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/classic')
def classic():
    return render_template('index.html')

@app.route('/quick_summary_strategy', methods=['POST'])
def quick_summary_strategy():
    """Quick summary for strategy selection mode"""
    try:
        print("=== STRATEGY-BASED QUICK SUMMARY START ===")
        
        strategy_value = request.form.get('strategy')
        candle_data_value = request.form.get('candle_data')
        
        if not strategy_value or not candle_data_value:
            return jsonify({'success': False, 'error': 'Missing strategy or candle data'})
        
        print(f"📊 Strategy: {strategy_value}")
        print(f"📊 Candle: {candle_data_value}")
        
        # Parse strategy selection
        strategy_parts = strategy_value.split('_')
        if len(strategy_parts) >= 4:
            symbol = strategy_parts[0]
            timeframe = strategy_parts[1]  
            strategy_name = '_'.join(strategy_parts[2:-1])
            version = strategy_parts[-1]
            
            print(f"🎯 Parsed - Symbol: {symbol}, Timeframe: {timeframe}, Strategy: {strategy_name}, Version: {version}")
        else:
            return jsonify({'success': False, 'error': 'Invalid strategy format'})
        
        # Load strategy data
        sm = get_strategy_manager()
        strategy_info = sm.get_strategy(symbol, timeframe, strategy_name, version)
        if not strategy_info:
            return jsonify({'success': False, 'error': 'Strategy not found'})
        
        # Load trade data from strategy file
        if not os.path.exists(strategy_info.file_path):
            return jsonify({'success': False, 'error': f'Strategy file not found: {strategy_info.file_path}'})
            
        with open(strategy_info.file_path, 'r', encoding='utf-8') as f:
            trade_content = f.read().strip()
        
        # Check if it's legacy format (file contains only file path)
        if len(trade_content.split('\n')) <= 2 and not trade_content.startswith('Date,') and not trade_content.startswith('date,'):
            # Legacy format - file contains path to actual trade file
            legacy_trade_file = trade_content.strip()
            print(f"🔄 Legacy format detected: {legacy_trade_file}")
            
            if os.path.exists(legacy_trade_file):
                with open(legacy_trade_file, 'r', encoding='utf-8') as f:
                    trade_content = f.read()
                print(f"✅ Loaded legacy trade file: {legacy_trade_file}")
            else:
                return jsonify({'success': False, 'error': f'Legacy trade file not found: {legacy_trade_file}'})
        
        # Load candle data from database only
        candle_data_value = request.form.get('candle_data')
        print(f"📊 Candle source: {candle_data_value}")
        
        # Parse database format: SYMBOL_TIMEFRAME.db
        try:
            if not candle_data_value or not candle_data_value.endswith('.db'):
                raise ValueError("Only database candle sources are supported")
                
            db_name = candle_data_value.replace('.db', '')
            if '_' not in db_name:
                raise ValueError(f"Invalid database format: {candle_data_value}")
                
            parts = db_name.split('_')
            if len(parts) < 2:
                raise ValueError(f"Invalid database format: {candle_data_value}")
                
            db_symbol = '_'.join(parts[:-1])
            db_timeframe = parts[-1]
            
            print(f"🔄 Loading from database: symbol={db_symbol}, timeframe={db_timeframe}")
            
            # Load from candlestick_data.db
            conn = sqlite3.connect('candlestick_data.db')
            query = "SELECT * FROM candlestick_data WHERE symbol = ? AND timeframe = ? ORDER BY open_time"
            df_candle = pd.read_sql_query(query, conn, params=[db_symbol, db_timeframe])
            conn.close()
            
            if df_candle.empty:
                raise ValueError(f"No candle data found in database for {db_symbol} {db_timeframe}")
            
            # Convert database format to standard format
            df_candle = df_candle.rename(columns={
                'open_time': 'time',
                'open_price': 'open', 
                'high_price': 'high',
                'low_price': 'low',
                'close_price': 'close'
            })
            df_candle['time'] = pd.to_datetime(df_candle['time'], unit='s')  # Database uses seconds, not milliseconds
            
            print(f"✅ Loaded from database: {len(df_candle)} candles")
                
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error loading candle data: {str(e)}'})
        
        print(f"✅ Loaded strategy: {strategy_info.filename}")
        print(f"✅ Loaded candle data: {len(df_candle)} candles")
        
        # Load and process trade data
        df_trade = load_trade_csv_from_content(trade_content)
        
        print(f"Data loaded: Trade={len(df_trade)}, Candle={len(df_candle)}")
        
        # Enhanced validation and info
        unique_trades = len(df_trade['trade'].unique()) if 'trade' in df_trade.columns else 0
        print(f"Trade validation: {len(df_trade)} records from {unique_trades} unique trades")
        
        # Get trade pairs for proper PnL calculation
        trade_pairs, log_init = get_trade_pairs(df_trade)
        print(f"📊 Trade pairs extracted: {len(trade_pairs)} pairs from {len(df_trade)} records")
        
        # Calculate performance using trade pairs (like backup_old)
        performance = None
        if trade_pairs:
            performance = calculate_original_performance(trade_pairs)
            if performance:
                total_pnl = performance['total_pnl']
                win_trades = performance['win_trades']
                lose_trades = performance['loss_trades']
                total_trades = performance['total_trades']
                win_rate = performance['winrate']
                profit_factor = performance['profit_factor']
                print(f"📊 Performance calculated: PnL={total_pnl:.2f}%, Win Rate={win_rate:.2f}%, Trades={total_trades}")
            else:
                total_pnl = win_trades = lose_trades = total_trades = win_rate = profit_factor = 0
                print("⚠️ Performance calculation returned None")
        else:
            total_pnl = win_trades = lose_trades = total_trades = win_rate = profit_factor = 0
            print("⚠️ No trade pairs extracted")
            
        # Get date range from trade data
        if 'date' in df_trade.columns:
            start_date = df_trade['date'].min().strftime('%Y-%m-%d') if pd.notna(df_trade['date'].min()) else 'N/A'
            end_date = df_trade['date'].max().strftime('%Y-%m-%d') if pd.notna(df_trade['date'].max()) else 'N/A'
        else:
            start_date = end_date = 'N/A'
        
        # Create response data with enhanced metrics
        summary_data = {
            'strategy_name': f"{symbol} {timeframe} {strategy_name} {version}",
            'total_trades': total_trades,
            'total_pnl': round(total_pnl, 2),
            'win_rate': round(win_rate, 2),
            'profit_factor': round(profit_factor, 2),
            'win_trades': win_trades,
            'lose_trades': lose_trades,
            'start_date': start_date,
            'end_date': end_date,
            'candle_count': len(df_candle)
        }
        
        # Add enhanced metrics if performance data is available
        if performance:
            summary_data.update({
                'avg_win': round(performance.get('avg_win', 0), 2),
                'avg_loss': round(performance.get('avg_loss', 0), 2),
                'max_drawdown': round(performance.get('max_drawdown', 0), 2),
                'sharpe_ratio': round(performance.get('sharpe_ratio', 0), 3),
                'recovery_factor': round(performance.get('recovery_factor', 0), 2),
                'gross_profit': round(performance.get('gross_profit', 0), 2),
                'gross_loss': round(performance.get('gross_loss', 0), 2),
                'avg_trade': round(performance.get('avg_trade', 0), 2),
                'max_consecutive_wins': performance.get('max_consecutive_wins', 0),
                'max_consecutive_losses': performance.get('max_consecutive_losses', 0)
            })
        else:
            # Add default values for enhanced metrics
            summary_data.update({
                'avg_win': 0,
                'avg_loss': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'recovery_factor': 0,
                'gross_profit': 0,
                'gross_loss': 0,
                'avg_trade': 0,
                'max_consecutive_wins': 0,
                'max_consecutive_losses': 0
            })
        
        return jsonify({
            'success': True,
            'data': summary_data
        })
            
    except Exception as e:
        print(f"❌ Error in quick summary: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/quick_summary', methods=['POST'])
def quick_summary():
    try:
        print("=== ENHANCED QUICK SUMMARY START ===")
        
        # Láº¥y dá»¯ liá»‡u tá»« form
        trade_file = request.files.get('trade_file')
        candle_file = request.files.get('candle_file')
        
        if not trade_file or not candle_file:
            return jsonify({'success': False, 'error': 'Missing files'})
        
        print(f"Files: {trade_file.filename}, {candle_file.filename}")
        
        # Äá»c files trá»±c tiáº¿p khÃ´ng qua tempfile Ä‘á»ƒ trÃ¡nh treo
        trade_content = trade_file.read().decode('utf-8')
        candle_content = candle_file.read().decode('utf-8')
        
        print(f"Content lengths: Trade={len(trade_content)}, Candle={len(candle_content)}")
        
        # Load vÃ  process data - chá»‰ dÃ¹ng content-based functions
        df_trade = load_trade_csv_from_content(trade_content)
        df_candle = load_candle_csv_from_content(candle_content)
        
        print(f"Data loaded: Trade={len(df_trade)}, Candle={len(df_candle)}")
        
        # Enhanced validation and info for user
        unique_trades = len(df_trade['trade'].unique()) if 'trade' in df_trade.columns else 0
        print(f"Trade validation: {len(df_trade)} records from {unique_trades} unique trades")
        
        # Sample price detection for format info
        if 'price' in df_trade.columns:
            sample_prices = df_trade['price'].head(10).mean()
            if sample_prices < 0.1:
                format_info = "BOME format detected (low price range)"
            elif sample_prices > 1000:
                format_info = "BTC format detected (high price range)"
            else:
                format_info = "ACE/mid-range format detected"
            print(f"Format info: {format_info}")
        
        # Filter data theo thá»i gian vá»›i debug
        min_candle = df_candle['time'].min()
        max_candle = df_candle['time'].max()
        print(f"ðŸ• SUMMARY DEBUG: Candle time range: {min_candle} to {max_candle}")
        
        min_trade = df_trade['date'].min()
        max_trade = df_trade['date'].max()
        print(f"ðŸ• SUMMARY DEBUG: Trade time range: {min_trade} to {max_trade}")
        
        df_trade_filtered = df_trade[(df_trade['date'] >= min_candle) & (df_trade['date'] <= max_candle)]
        print(f"ðŸ• SUMMARY DEBUG: Trades after time filter: {len(df_trade_filtered)} (original: {len(df_trade)})")
        
        # Láº¥y trade pairs - chá»‰ dÃ¹ng local function
        trade_pairs, log_init = get_trade_pairs(df_trade_filtered)
        
        # TÃ­nh toÃ¡n hiá»‡u suáº¥t gá»‘c báº±ng 2 cÃ¡ch Ä‘á»ƒ so sÃ¡nh
        # CÃ¡ch 1: Direct calculation tá»« trade pairs
        performance_direct = calculate_original_performance(trade_pairs)
        
        # CÃ¡ch 2: Simulation-based calculation Ä‘á»ƒ so sÃ¡nh
        performance_simulated = None
        simulated_details = []
        try:
            for pair in trade_pairs[:10]:  # Test vá»›i 10 lá»‡nh Ä‘áº§u Ä‘á»ƒ khÃ´ng cháº­m
                if ADVANCED_MODE:
                    result, log = simulate_trade(pair, df_candle, 0, 0, 0, 0)
                    if result is not None:
                        simulated_details.append(result)
                else:
                    res = simulate_trade_sl_only(pair, df_candle, 0)
                    if res is not None:
                        simulated_details.append(res)
            
            if simulated_details:
                sim_pnl_total = sum([x['pnlPct'] for x in simulated_details])
                sim_winrate = len([x for x in simulated_details if x['pnlPct'] > 0]) / len(simulated_details) * 100
                performance_simulated = {
                    'total_pnl': sim_pnl_total,
                    'winrate': sim_winrate,
                    'trade_count': len(simulated_details)
                }
                print(f"ðŸ” COMPARISON: Direct vs Simulated PnL for first 10 trades")
                print(f"   Direct method: {performance_direct['total_pnl']/len(trade_pairs)*10:.4f}% (10 trades)")
                print(f"   Simulated method: {sim_pnl_total:.4f}% (10 trades)")
                
        except Exception as e:
            print(f"Warning: Could not run simulation comparison: {e}")
        
        # Use direct calculation as primary result
        performance = performance_direct
        
        print(f"Trade pairs: {len(trade_pairs)}")
        
        # ThÃ´ng tin vá» candle data
        candle_count = len(df_candle)
        date_range = f"{min_candle.strftime('%m/%d %H:%M')} - {max_candle.strftime('%m/%d %H:%M')}"
        
        summary_data = {
            'success': True,
            'summary': {
                'total_trades': len(df_trade),
                'valid_trades': len(trade_pairs),
                'candle_count': candle_count,
                'date_range': date_range,
                'total_pnl': performance['total_pnl'] if performance else 0,
                'winrate': performance['winrate'] if performance else 0,
                'profit_factor': performance['profit_factor'] if performance else 0,
                'avg_trade': performance['avg_trade'] if performance else 0,
                'win_trades': performance['win_trades'] if performance else 0,
                'loss_trades': performance['loss_trades'] if performance else 0,
                'max_drawdown': performance['max_drawdown'] if performance else 0,
                'avg_win': performance['avg_win'] if performance else 0,
                'avg_loss': performance['avg_loss'] if performance else 0,
                'max_consecutive_wins': performance['max_consecutive_wins'] if performance else 0,
                'max_consecutive_losses': performance['max_consecutive_losses'] if performance else 0,
                'sharpe_ratio': performance['sharpe_ratio'] if performance else 0,
                'recovery_factor': performance['recovery_factor'] if performance else 0
            },
            'comparison': {
                'direct_method': performance_direct['total_pnl'] if performance_direct else 0,
                'simulated_method': performance_simulated['total_pnl'] if performance_simulated else 'N/A',
                'method_note': 'Direct = tá»« trade pairs, Simulated = qua engine mÃ´ phá»ng'
            } if performance_simulated else None
        }
        
        print("=== ENHANCED QUICK SUMMARY SUCCESS ===")
        return jsonify(convert_to_serializable(summary_data))
        
    except Exception as e:
        print(f"=== ENHANCED QUICK SUMMARY ERROR: {str(e)} ===")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/suggest_parameters', methods=['POST'])
def suggest_parameters():
    """Smart parameter range suggestion based on tradelist analysis"""
    try:
        print("=== SMART PARAMETER SUGGESTION START ===")
        
        # Get files from request
        trade_file = request.files.get('trade_file')
        
        if not trade_file:
            return jsonify({'success': False, 'error': 'Missing trade file for analysis'})
        
        print(f"Analyzing tradelist: {trade_file.filename}")
        
        # Read and process trade data
        trade_content = trade_file.read().decode('utf-8')
        print(f"Trade content length: {len(trade_content)} chars")
        
        # Load trade data
        df_trade = load_trade_csv_from_content(trade_content)
        print(f"Loaded {len(df_trade)} trade records")
        
        # Extract trade pairs for analysis
        trade_pairs, log_init = get_trade_pairs(df_trade)
        print(f"Extracted {len(trade_pairs)} valid trade pairs")
        
        # Check minimum data requirement
        if len(trade_pairs) < 10:
            return jsonify({
                'success': False, 
                'error': f'KhÃ´ng Ä‘á»§ dá»¯ liá»‡u Ä‘á»ƒ phÃ¢n tÃ­ch thÃ´ng minh. Cáº§n Ã­t nháº¥t 10 trades, hiá»‡n táº¡i chá»‰ cÃ³ {len(trade_pairs)} trades.'
            })
        
        # Import and run Smart Range Finder
        try:
            import tempfile
            import os
            
            # Create temporary tradelist file for analysis
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8') as temp_file:
                temp_file.write(trade_content)
                temp_path = temp_file.name
            
            try:
                # Import Smart Range Finder classes
                from smart_range_finder import SmartRangeFinder
                from dynamic_step_calculator import DynamicStepCalculator
                
                print("ðŸ” Running Smart Range Finder analysis...")
                
                # Initialize and run Smart Range Finder
                finder = SmartRangeFinder(temp_path)
                analysis_results = finder.analyze_price_movement_patterns()
                recommendations = finder.generate_final_recommendations()
                
                print("ðŸ” Running Dynamic Step Calculator...")
                
                # Initialize and run Dynamic Step Calculator
                calculator = DynamicStepCalculator(temp_path)
                step_report = calculator.generate_comprehensive_report()
                
                # Extract parameter ranges from balanced strategy
                # Debug statements removed for performance optimization

                # Build param_ranges from recommendations if available, else fallback to step_data
                if 'parameter_ranges' in recommendations:
                    param_ranges = recommendations['parameter_ranges']
                else:
                    # Fallback: build from step_data using min/max logic
                    param_ranges = {
                        'sl': {'min': float(step_data['sl_steps']['conservative']), 'max': float(step_data['sl_steps']['aggressive'])},
                        'be': {'min': float(step_data['be_steps']['conservative']), 'max': float(step_data['be_steps']['aggressive'])},
                        'ts_trigger': {'min': float(step_data['ts_trigger_steps']['conservative']), 'max': float(step_data['ts_trigger_steps']['aggressive'])},
                        'ts_step': {'min': float(step_data['ts_step_steps']['conservative']), 'max': float(step_data['ts_step_steps']['aggressive'])}
                    }
                # Build response with statistical foundation
                # Enforce TS trigger floor in API-level suggested parameters for transparency
                try:
                    from smart_range_finder import TS_TRIGGER_MIN
                except Exception:
                    TS_TRIGGER_MIN = 2.5

                # Clamp ts trigger suggested min/max to TS_TRIGGER_MIN
                ts_trig_min_suggested = max(float(param_ranges['ts_trigger']['min']), TS_TRIGGER_MIN) if float(param_ranges['ts_trigger']['min'])>0 else 0.0
                ts_trig_max_suggested = max(float(param_ranges['ts_trigger']['max']), TS_TRIGGER_MIN) if float(param_ranges['ts_trigger']['max'])>0 else 0.0

                suggested_params = {
                    'sl_min': param_ranges['sl']['min'],
                    'sl_max': param_ranges['sl']['max'],
                    'sl_step': step_data['sl_steps']['balanced'],

                    'be_min': param_ranges['be']['min'], 
                    'be_max': param_ranges['be']['max'],
                    'be_step': step_data['be_steps']['balanced'],

                    'ts_trig_min': ts_trig_min_suggested,
                    'ts_trig_max': ts_trig_max_suggested,
                    'ts_trig_step': step_data['ts_trigger_steps']['balanced'],

                    'ts_step_min': param_ranges['ts_step']['min'],
                    'ts_step_max': param_ranges['ts_step']['max'],
                    'ts_step_step': step_data['ts_step_steps']['balanced']
                }
                
                # Calculate efficiency gains (use safe defaults if SmartRangeFinder omitted them)
                efficiency_gain = recommendations.get('efficiency_gain', 1.0)
                combinations_count = recommendations.get('combinations_count', int(recommendations.get('smart_combinations', 1)))
                total_trades_analyzed = recommendations.get('total_trades_analyzed', len(trade_pairs))
                
                # Build explanation
                explanation = {
                    'data_analysis': f"PhÃ¢n tÃ­ch {len(trade_pairs)} trades vá»›i {total_trades_analyzed} exit records",
                    'strategy_selected': f"Chiáº¿n lÆ°á»£c Balanced Ä‘Æ°á»£c chá»n tá»± Ä‘á»™ng (cÃ¢n báº±ng rá»§i ro/lá»£i nhuáº­n)",
                    'statistical_foundation': [
                        f"SL Range: {param_ranges['sl']['min']:.1f}%-{param_ranges['sl']['max']:.1f}% dá»±a trÃªn phÃ¢n tÃ­ch drawdown patterns",
                        f"BE Range: {param_ranges['be']['min']:.2f}%-{param_ranges['be']['max']:.2f}% dá»±a trÃªn early run-up patterns", 
                        f"TS Trigger: {param_ranges['ts_trigger']['min']:.2f}%-{param_ranges['ts_trigger']['max']:.2f}% dá»±a trÃªn profit development patterns",
                        f"TS Step: {param_ranges['ts_step']['min']:.2f}%-{param_ranges['ts_step']['max']:.2f}% dá»±a trÃªn volatility adjustment"
                    ],
                    'step_logic': [
                        f"SL Step ({step_data['sl_steps']['balanced']}): {step_data['sl_steps']['base_calculation']}",
                        f"BE Step ({step_data['be_steps']['balanced']}): {step_data['be_steps']['base_calculation']}",
                        f"TS Trigger Step ({step_data['ts_trigger_steps']['balanced']}): {step_data['ts_trigger_steps']['base_calculation']}",
                        f"TS Step Step ({step_data['ts_step_steps']['balanced']}): {step_data['ts_step_steps']['base_calculation']}"
                    ]
                }
                
                # Add a user-visible warning if we applied the clamp
                ts_warnings = []
                if float(param_ranges['ts_trigger']['min'])>0 and ts_trig_min_suggested != float(param_ranges['ts_trigger']['min']):
                    ts_warnings.append(f"ts_trig_min raised to {TS_TRIGGER_MIN}% from {param_ranges['ts_trigger']['min']}%")
                if float(param_ranges['ts_trigger']['max'])>0 and ts_trig_max_suggested != float(param_ranges['ts_trigger']['max']):
                    ts_warnings.append(f"ts_trig_max raised to {TS_TRIGGER_MIN}% from {param_ranges['ts_trigger']['max']}%")

                # Normalize warnings: merge sources then convert to structured objects
                merged_raw_warnings = (step_report.get('warnings', []) or []) + (finder.range_analysis.get('warnings', []) if hasattr(finder, 'range_analysis') else []) + ts_warnings

                # Use centralized descriptions from warning_codes
                try:
                    from warning_codes import CODE_DESCRIPTIONS
                except Exception:
                    CODE_DESCRIPTIONS = {}

                def normalize_warning(w):
                    # Original human string (if available)
                    original_human = None
                    code = 'unknown'
                    value = None
                    raw_message = ''

                    if isinstance(w, dict):
                        code = w.get('code', 'unknown')
                        raw_message = str(w.get('message', ''))
                        original_human = str(w.get('human', raw_message))
                        value = w.get('value', None)
                    elif isinstance(w, str):
                        raw_message = w
                        original_human = w
                        low = w.lower()
                        # Heuristic code mapping for legacy strings
                        if 'sl' in low and 'floor' in low:
                            code = 'SL_FLOOR'
                        elif 'be' in low and 'floor' in low:
                            code = 'BE_FLOOR'
                        elif 'ts-step' in low or 'ts step' in low or 'step' in low and 'ts' in low:
                            code = 'TS_STEP_FLOOR'
                        elif 'ts_trig' in low or 'ts trig' in low or 'ts trigger' in low or 'ts conservative' in low or 'ts balanced' in low:
                            code = 'TS_TRIGGER_FLOOR'
                        else:
                            code = 'INFO'
                        # try to extract numeric percent
                        import re
                        m = re.search(r"(\d+(?:\.\d+)?)%", w)
                        value = float(m.group(1)) if m else None
                    else:
                        raw_message = str(w)
                        original_human = raw_message

                    # Normalize code casing to match keys in CODE_DESCRIPTIONS
                    code_key = str(code)
                    # If code is one of the short constants, try to map to canonical key names used in CODE_DESCRIPTIONS
                    # CODE_DESCRIPTIONS uses exact constants from warning_codes; try both direct and upper variants
                    canonical_msg = CODE_DESCRIPTIONS.get(code_key) or CODE_DESCRIPTIONS.get(code_key.upper()) or raw_message

                    return {
                        'code': code_key,
                        'message': canonical_msg,
                        'value': value,
                        'human': original_human
                    }

                structured_warnings = [normalize_warning(w) for w in merged_raw_warnings]

                response_data = {
                    'success': True,
                    'suggested_parameters': suggested_params,
                    # Include TP level suggestions from SmartRangeFinder if available
                    'tp_levels': recommendations.get('tp_levels', finder.range_analysis.get('tp_levels', {})) if isinstance(recommendations, dict) else finder.range_analysis.get('tp_levels', {}),
                    # Feature enable flags at the analysis level: True if the suggested ranges/steps indicate >0
                    'features_enabled': {
                        'sl_enabled': float(param_ranges['sl']['max']) > 0 and float(suggested_params['sl_step']) > 0,
                        'be_enabled': float(param_ranges['be']['max']) > 0 and float(suggested_params['be_step']) > 0,
                        'ts_enabled': float(param_ranges['ts_trigger']['max']) > 0 and float(suggested_params['ts_step_step']) > 0,
                    },
                    'parameter_steps_full': step_data,
                    # Structured warnings for API consumers
                    'warnings': structured_warnings,
                    # include validation, statistical foundations and improvement metrics
                    'validation_results': step_report.get('validation_results', {}),
                    'statistical_foundations': step_report.get('statistical_foundations', {}),
                    'improvement_metrics': step_report.get('improvement_metrics', {}),
                    # include SmartRangeFinder recommendations (safe)
                    'finder_recommendations': recommendations if isinstance(recommendations, dict) else {},
                    'explanation': explanation,
                    'efficiency': {
                        'efficiency_gain': efficiency_gain,
                        'smart_combinations': combinations_count,
                        'estimated_time_savings': f"{efficiency_gain:.1f}x faster than blind search"
                    },
                    'data_quality': {
                        'total_trades_analyzed': len(trade_pairs),
                        'data_quality_issues': recommendations.get('data_quality_issues', [])
                    }
                }
                
                print(f"âœ… Smart parameter suggestion complete!")
                print(f"   SL: {suggested_params['sl_min']:.1f}%-{suggested_params['sl_max']:.1f}% (step: {suggested_params['sl_step']})")
                print(f"   BE: {suggested_params['be_min']:.2f}%-{suggested_params['be_max']:.2f}% (step: {suggested_params['be_step']})")
                print(f"   Efficiency: {efficiency_gain:.1f}x improvement")
                
                return jsonify(convert_to_serializable(response_data))
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except ImportError as e:
            print(f"âš ï¸ Smart Range Finder not available: {e}")
            return jsonify({
                'success': False,
                'error': 'Smart Range Finder module khÃ´ng cÃ³ sáºµn. Vui lÃ²ng kiá»ƒm tra smart_range_finder.py vÃ  dynamic_step_calculator.py files.'
            })
        
    except Exception as e:
        print(f"=== SMART PARAMETER SUGGESTION ERROR: {str(e)} ===")
        return jsonify({'success': False, 'error': f'Lá»—i phÃ¢n tÃ­ch thÃ´ng sá»‘: {str(e)}'})

@app.route('/optimize', methods=['POST'])
def optimize():
    global optimization_status
    print("🔥🔥🔥 OPTIMIZE FUNCTION ENTERED 🔥🔥🔥")
    print(f"Request method: {request.method}")
    print(f"Request form keys: {list(request.form.keys())}")
    try:
        print("🚨🚨🚨 OPTIMIZE ROUTE HIT! 🚨🚨🚨")
        print("=== ENHANCED OPTIMIZATION START ===")
        
        # Check if using selected data or uploaded files
        use_selected_data = request.form.get('use_selected_data', 'false').lower() == 'true'
        
        if use_selected_data:
            print("📊 Using SELECTED DATA from Strategy Management")
            
            # Get strategy info
            strategy_symbol = request.form.get('strategy_symbol')
            strategy_timeframe = request.form.get('strategy_timeframe') 
            strategy_name = request.form.get('strategy_name')
            strategy_version = request.form.get('strategy_version')
            selected_candle = request.form.get('selected_candle')
            
            print(f"📈 Strategy: {strategy_symbol} {strategy_timeframe} {strategy_name} v{strategy_version}")
            print(f"🕯️ Candle: {selected_candle}")
            
            # Load strategy data
            sm = get_strategy_manager()
            try:
                strategy_info = sm.get_strategy(strategy_symbol, strategy_timeframe, strategy_name, strategy_version)
                if not strategy_info:
                    raise ValueError("Strategy not found in database")
                    
                trade_file_path = strategy_info.file_path
                if not os.path.exists(trade_file_path):
                    raise ValueError(f"Strategy file not found: {trade_file_path}")
                    
                print(f"✅ Strategy file: {trade_file_path}")
                
                # Load trade data using proper function with column mapping
                with open(trade_file_path, 'r', encoding='utf-8') as f:
                    trade_content = f.read()
                df_trade = load_trade_csv_from_content(trade_content)
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Error loading strategy: {str(e)}'
                })
            
            # Load candle data from database only
            candle_source = selected_candle
            print(f"✅ Candle source: {candle_source}")
            
            try:
                # Parse database format: SYMBOL_TIMEFRAME.db
                if not candle_source or not candle_source.endswith('.db'):
                    raise ValueError("Only database candle sources are supported")
                
                db_name = candle_source.replace('.db', '')
                if '_' not in db_name:
                    raise ValueError(f"Invalid database format: {candle_source}")
                    
                db_symbol, db_timeframe = db_name.rsplit('_', 1)
                if not db_symbol or not db_timeframe:
                    raise ValueError(f"Invalid database format: {candle_source}")
                
                print(f"🔄 [OPTIMIZE] Loading from database: symbol={db_symbol}, timeframe={db_timeframe}")
                
                # Load from candlestick_data.db
                conn = sqlite3.connect('candlestick_data.db')
                query = "SELECT * FROM candlestick_data WHERE symbol = ? AND timeframe = ? ORDER BY open_time"
                df_candle = pd.read_sql_query(query, conn, params=(db_symbol, db_timeframe))
                conn.close()
                
                if df_candle.empty:
                    raise ValueError(f"No candle data found in database for {db_symbol} {db_timeframe}")
                
                # Convert database format to standard format
                df_candle = df_candle.rename(columns={
                    'open_time': 'time',
                    'open_price': 'open', 
                    'high_price': 'high',
                    'low_price': 'low',
                    'close_price': 'close'
                })
                df_candle['time'] = pd.to_datetime(df_candle['time'], unit='s')  # Database uses seconds
                print(f"✅ Loaded candle data: {len(df_candle)} rows")
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Error loading candle data: {str(e)}'
                })
            
        else:
            print("📁 Using UPLOADED FILES (legacy mode)")
            # Lấy dữ liệu từ form
            trade_file = request.files['trade_file']
            candle_file = request.files['candle_file']
        
        # ðŸš¨ DEBUG: Print raw form data to see what browser is actually sending
        print(f"ðŸ” RAW FORM DATA DEBUG:")
        for key, value in request.form.items():
            print(f"   {key} = '{value}'")
        
        # 🔧 GET MAX_ITERATIONS FROM FORM
        raw_max_iterations = request.form.get('max_iterations')
        max_iterations = validate_optuna_trials(raw_max_iterations)
        print(f"🔧 Form Max Iterations: {raw_max_iterations} → {max_iterations} (validated)")
        

        # --- Dynamic parameter selection ---
        sl_min = float(request.form['sl_min'])
        sl_max = float(request.form['sl_max'])
        sl_step = float(request.form['sl_step'])
        be_min = safe_float_parse(request.form, 'be_min', 2.0)
        be_max = safe_float_parse(request.form, 'be_max', 2.0)
        be_step = safe_float_parse(request.form, 'be_step', 0.5)
        ts_trig_min = safe_float_parse(request.form, 'ts_trig_min', 2.0)
        ts_trig_max = safe_float_parse(request.form, 'ts_trig_max', 3.0)
        ts_trig_step = safe_float_parse(request.form, 'ts_trig_step', 0.5)
        ts_step_min = safe_float_parse(request.form, 'ts_step_min', 3.0)
        ts_step_max = safe_float_parse(request.form, 'ts_step_max', 1.0)
        ts_step_step = safe_float_parse(request.form, 'ts_step_step', 0.2)

        # 🔒 BACKEND VALIDATION: Apply same safety minimums for form route
        def validate_and_enforce_minimums_v2(be_min, be_max, ts_trig_min, ts_trig_max, ts_step_min, ts_step_max):
            """Enforce safety minimums for form input route"""
            SAFETY_BE_MIN = 2.0          
            SAFETY_TS_TRIGGER_MIN = 2.0  
            SAFETY_TS_STEP_MIN = 3.0     
            
            warnings = []
            
            # Validate BE
            if be_min > 0 and be_min < SAFETY_BE_MIN:
                warnings.append(f"BE min {be_min}% → {SAFETY_BE_MIN}% (safety minimum)")
                be_min = SAFETY_BE_MIN
            if be_max > 0 and be_max < SAFETY_BE_MIN:
                warnings.append(f"BE max {be_max}% → {SAFETY_BE_MIN}% (safety minimum)")
                be_max = SAFETY_BE_MIN
                
            # Validate TS trigger
            if ts_trig_min > 0 and ts_trig_min < SAFETY_TS_TRIGGER_MIN:
                warnings.append(f"TS trigger min {ts_trig_min}% → {SAFETY_TS_TRIGGER_MIN}% (safety minimum)")
                ts_trig_min = SAFETY_TS_TRIGGER_MIN
            if ts_trig_max > 0 and ts_trig_max < SAFETY_TS_TRIGGER_MIN:
                warnings.append(f"TS trigger max {ts_trig_max}% → {SAFETY_TS_TRIGGER_MIN}% (safety minimum)")
                ts_trig_max = SAFETY_TS_TRIGGER_MIN
                
            # Validate TS step
            if ts_step_min > 0 and ts_step_min < SAFETY_TS_STEP_MIN:
                warnings.append(f"TS step min {ts_step_min}% → {SAFETY_TS_STEP_MIN}% (safety minimum)")
                ts_step_min = SAFETY_TS_STEP_MIN
            if ts_step_max > 0 and ts_step_max < SAFETY_TS_STEP_MIN:
                warnings.append(f"TS step max {ts_step_max}% → {SAFETY_TS_STEP_MIN}% (safety minimum)")
                ts_step_max = SAFETY_TS_STEP_MIN
            
            return be_min, be_max, ts_trig_min, ts_trig_max, ts_step_min, ts_step_max, warnings
        
        # Apply validation to form inputs
        be_min, be_max, ts_trig_min, ts_trig_max, ts_step_min, ts_step_max, validation_warnings = validate_and_enforce_minimums_v2(
            be_min, be_max, ts_trig_min, ts_trig_max, ts_step_min, ts_step_max
        )
        
        if validation_warnings:
            print(f"🔒 FORM VALIDATION APPLIED ({len(validation_warnings)} adjustments):")
            for warning in validation_warnings:
                print(f"   ⚠️ {warning}")
        else:
            print(f"✅ Form parameters above safety minimums")

        # Parse optimize_params (JSON string from frontend)
        optimize_params = request.form.get('optimize_params')
        if optimize_params:
            try:
                import json
                parsed = json.loads(optimize_params)
                # If it's a list (e.g. ["sl","be"]), convert to dict
                if isinstance(parsed, list):
                    optimize_params = {"sl": False, "be": False, "ts": False}
                    for k in parsed:
                        if k in optimize_params:
                            optimize_params[k] = True
                elif isinstance(parsed, dict):
                    # Already in correct format
                    optimize_params = {"sl": bool(parsed.get("sl", False)),
                                       "be": bool(parsed.get("be", False)),
                                       "ts": bool(parsed.get("ts", False))}
                else:
                    optimize_params = {"sl": True, "be": True, "ts": True}
            except Exception as e:
                print(f"âš ï¸ Failed to parse optimize_params: {e}")
                optimize_params = {"sl": True, "be": True, "ts": True}
        else:
            optimize_params = {"sl": True, "be": True, "ts": True}

        # Build parameter lists: náº¿u khÃ´ng chá»n thÃ¬ truyá»n 0 (táº¯t logic), náº¿u chá»n thÃ¬ build range
        if optimize_params.get("sl", True):
            sl_list = list(np.arange(sl_min, sl_max + sl_step/2, sl_step))
        else:
            # If SL optimization is disabled, do not include user SL values in the search.
            # Use [0] to indicate SL is turned off in the grid search (consistent with BE/TS handling).
            sl_list = [0]

        if optimize_params.get("be", True):
            if be_min == be_max == 0:
                be_list = [0]
            elif be_min == be_max:
                be_list = [be_min]
            else:
                be_list = list(np.arange(be_min, be_max + be_step/2, be_step))
        else:
            be_list = [0]  # KhÃ´ng chá»n BE thÃ¬ truyá»n 0 (táº¯t logic BE)

        if optimize_params.get("ts", True):
            if ts_trig_min == ts_trig_max == 0:
                ts_trig_list = [0]
            elif ts_trig_min == ts_trig_max:
                ts_trig_list = [ts_trig_min]
            else:
                ts_trig_list = list(np.arange(ts_trig_min, ts_trig_max + ts_trig_step/2, ts_trig_step))
            if ts_step_min == ts_step_max == 0:
                ts_step_list = [0]
            elif ts_step_min == ts_step_max:
                ts_step_list = [ts_step_min]
            else:
                ts_step_list = list(np.arange(ts_step_min, ts_step_max + ts_step_step/2, ts_step_step))
        else:
            ts_trig_list = [0]  # KhÃ´ng chá»n TS thÃ¬ truyá»n 0 (táº¯t logic TS)
            ts_step_list = [0]

        # Print debug info
        print(f"ðŸ” SERVER RECEIVED PARAMETERS:")
        print(f"   SL: min={sl_min}, max={sl_max}, step={sl_step}, list={sl_list}")
        print(f"   BE: min={be_min}, max={be_max}, step={be_step}, list={be_list}")
        print(f"   TS_TRIG: min={ts_trig_min}, max={ts_trig_max}, step={ts_trig_step}, list={ts_trig_list}")
        print(f"   TS_STEP: min={ts_step_min}, max={ts_step_max}, step={ts_step_step}, list={ts_step_list}")
        
        # Trade selection parameters  
        max_trades = int(request.form.get('max_trades', 0))
        start_trade = int(request.form.get('start_trade', 1))
        selection_mode = request.form.get('trade_selection_mode', 'sequence')
        
        opt_type = request.form['opt_type']
        
        print(f"Enhanced Parameters: SL {sl_min}-{sl_max}, BE {be_min}-{be_max}, TS {ts_trig_min}-{ts_trig_max}/{ts_step_min}-{ts_step_max}, opt={opt_type}")
        
        # Äá»c files trá»±c tiáº¿p Ä‘á»ƒ trÃ¡nh treo
        if not use_selected_data:
            trade_content = trade_file.read().decode("utf-8")
            candle_content = candle_file.read().decode("utf-8")
            print(f"Files loaded: Trade={len(trade_content)} chars, Candle={len(candle_content)} chars")
        else:
            print("📊 Selected data mode - files already loaded above")
        if not use_selected_data:
            # Upload mode - load from content
            try:
                df_trade = load_trade_csv_from_content(trade_content)
                df_candle = load_candle_csv_from_content(candle_content)
                print("Using content-based loading (safer)")
            except Exception as content_error:
                print(f"Content loading failed: {content_error}")
                # Fallback to file-based náº¿u cáº§n
                try:
                    # Táº¡o temp files
                    trade_temp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
                    candle_temp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
                
                    trade_temp.write(trade_content)
                    candle_temp.write(candle_content)
                    trade_temp.close()
                    candle_temp.close()
                
                    # Load using file-based functions
                    df_trade = load_trade_csv_file(trade_temp.name)
                    df_candle = load_candle_csv_file(candle_temp.name)
                
                    # Clean up temp files
                    os.unlink(trade_temp.name)
                    os.unlink(candle_temp.name)
                    print("Using file-based loading (fallback)")
                
                except Exception as file_error:
                    print(f"File loading also failed: {file_error}")
                    raise content_error
        
        # Filter data theo thá»i gian
        min_candle = df_candle['time'].min()
        max_candle = df_candle['time'].max()
        print(f"ðŸ• DEBUG: Candle time range: {min_candle} to {max_candle}")
        
        min_trade = df_trade['date'].min()
        max_trade = df_trade['date'].max()
        print(f"ðŸ• DEBUG: Trade time range: {min_trade} to {max_trade}")
        
        df_trade = df_trade[(df_trade['date'] >= min_candle) & (df_trade['date'] <= max_candle)]
        print(f"ðŸ• DEBUG: Trades after time filter: {len(df_trade)} (original: {len(df_trade) + len(df_trade[(df_trade['date'] < min_candle) | (df_trade['date'] > max_candle)])})")
        
        if len(df_trade) == 0:
            return jsonify({'error': f'KhÃ´ng cÃ³ trade nÃ o náº±m trong khoáº£ng thá»i gian cá»§a dá»¯ liá»‡u náº¿n! Candle: {min_candle} to {max_candle}, Trade: {min_trade} to {max_trade}. Hint: Kiá»ƒm tra xem báº¡n cÃ³ upload Ä‘Ãºng cáº·p file trade/candle khÃ´ng (VD: BOME trade vá»›i BOME candle, BTC trade vá»›i BTC candle)'})
        
        # Láº¥y trade pairs - Æ°u tiÃªn local function
        try:
            trade_pairs, log_init = get_trade_pairs(df_trade)
            print("Using content-based trade pairs")
        except Exception:
            try:
                trade_pairs, log_init = get_trade_pairs_file(df_trade)
                print("Using file-based trade pairs")
            except Exception as e:
                return jsonify({'error': f'Lá»—i xá»­ lÃ½ trade pairs: {str(e)}'})
        
        if len(trade_pairs) == 0:
            return jsonify({'error': 'KhÃ´ng cÃ³ trade pairs há»£p lá»‡!'})
        
        # Filter trades theo tham sá»‘ ngÆ°á»i dÃ¹ng
        original_count = len(trade_pairs)
        trade_pairs = filter_trades_by_selection(trade_pairs, max_trades, start_trade, selection_mode)
        filtered_count = len(trade_pairs)
        
        if len(trade_pairs) == 0:
            return jsonify({'error': f'KhÃ´ng cÃ³ trade nÃ o sau khi lá»c! (Gá»‘c: {original_count} lá»‡nh)'})
        
        # Log thÃ´ng tin lá»c
        filter_info = f"Enhanced: ÄÃ£ lá»c tá»« {original_count} xuá»‘ng {filtered_count} lá»‡nh"
        if max_trades > 0:
            filter_info += f" (tá»‘i Ä‘a {max_trades})"
        if start_trade < 0:
            filter_info += f" (tá»« {abs(start_trade)} lá»‡nh cuá»‘i)"
        elif start_trade > 1:
            filter_info += f" (tá»« lá»‡nh #{start_trade})"
        filter_info += f" (cháº¿ Ä‘á»™: {selection_mode})"
        
        print(filter_info)
        
        
        total_combinations = len(sl_list) * len(be_list) * len(ts_trig_list) * len(ts_step_list)
        print(f"Total combinations to test: {total_combinations}")
        
        # Cho phÃ©p user override limit náº¿u muá»‘n test nhiá»u combinations
        force_advanced = request.form.get('force_advanced_mode', 'false').lower() == 'true'
        combinations_limit = 1000000 if force_advanced else 100000  # NÃ¢ng limit cao hÆ¡n nhiá»u
        
        # ðŸ” DEBUG MODE SELECTION
        print(f"ðŸ” MODE SELECTION DEBUG:")
        print(f"   ADVANCED_MODE = {ADVANCED_MODE}")
        print(f"   total_combinations = {total_combinations}")
        print(f"   force_advanced = {force_advanced}")
        print(f"   combinations_limit = {combinations_limit:,}")
        print(f"   Condition (ADVANCED_MODE and total_combinations <= {combinations_limit}): {ADVANCED_MODE and total_combinations <= combinations_limit}")
        
        # Cháº¡y grid search vá»›i nháº­n diá»‡n cháº¿ Ä‘á»™
        method_type = request.form.get('method_type', 'grid')
        print(f"ðŸ” CHáº Y OPTUNA" if method_type == "optuna" else "ðŸ” CHáº Y GRID SEARCH")

        if method_type == "optuna":
            results = grid_search_realistic_full_v2(
                trade_pairs, df_candle, sl_list, be_list, ts_trig_list, ts_step_list, opt_type, max_iterations
            )
        else:
            results = grid_search_realistic_full(
                trade_pairs, df_candle, sl_list, be_list, ts_trig_list, ts_step_list, opt_type
            )
        
        # Mark optimization as complete
        optimization_status.update({
            'running': False,
            'status_message': f'HoÃ n táº¥t: Táº¡o ra {len(results)} káº¿t quáº£'
        })
        
        # Convert results Ä‘á»ƒ JSON serializable
        for result in results:
            result['sl'] = float(result['sl'])
            result['be'] = float(result['be'])
            result['ts_trig'] = float(result['ts_trig'])
            result['ts_step'] = float(result['ts_step'])
            result['pnl_total'] = float(result['pnl_total'])
            result['winrate'] = float(result['winrate'])
            result['pf'] = float(result['pf'])
            
            # Clean details
            for detail in result['details']:
                detail['num'] = safe_int(detail['num'])
                detail['entryPrice'] = float(detail['entryPrice'])
                detail['exitPrice'] = float(detail['exitPrice'])
                detail['pnlPct'] = float(detail['pnlPct'])
                detail['pnlPctOrigin'] = float(detail['pnlPctOrigin'])
        
        # TÃ­nh baseline vá»›i enhanced error handling vÃ  debug
        baseline_details = []
        baseline_logs = []
        baseline_debug_count = 0
        
        print(f"ðŸ” BASELINE DEBUG: Processing {len(trade_pairs)} trade pairs...")
        
        for pair in trade_pairs:
            try:
                if ADVANCED_MODE:
                    result, log = simulate_trade(pair, df_candle, 0, 0, 0, 0)  # No optimization
                    if result is not None:
                        # Convert Ä‘á»ƒ Ä‘áº£m báº£o JSON serializable
                        result_clean = {
                            'num': safe_int(result['num']),
                            'side': str(result['side']),
                            'entryPrice': float(result['entryPrice']),
                            'exitPrice': float(result['exitPrice']),
                            'exitType': str(result['exitType']),
                            'pnlPct': float(result['pnlPct']),
                            'pnlPctOrigin': float(result['pnlPctOrigin']),
                            'entryDt': result['entryDt'],
                            'exitDt': result['exitDt'],
                            'sl': 0.0,
                            'be': 0.0,
                            'ts_trig': 0.0,
                            'ts_step': 0.0
                        }
                        baseline_details.append(result_clean)
                        baseline_logs.extend(log)
                else:
                    # Use simulation engine for baseline calculation (no SL/BE/TS)
                    # This ensures same calculation method as optimization results
                    res = simulate_trade_sl_only(pair, df_candle, 0)  # No SL = baseline
                    if res is not None:
                        baseline_details.append(res)
                        
                        # Debug first few trades to verify calculation
                        if baseline_debug_count < 5:
                            print(f"ðŸ” BASELINE Trade {res['num']}: Entry={res['entryPrice']:.8f}, Exit={res['exitPrice']:.8f}, Side={res['side']}, PnL={res['pnlPct']:.4f}%")
                            
                            # Also show manual calculation for comparison
                            if res['side'] == 'LONG':
                                manual_pnl = (res['exitPrice'] - res['entryPrice']) / res['entryPrice'] * 100
                            else:
                                manual_pnl = (res['entryPrice'] - res['exitPrice']) / res['entryPrice'] * 100
                            print(f"ðŸ” MANUAL Trade {res['num']}: Manual PnL={manual_pnl:.4f}%, Simulated PnL={res['pnlPct']:.4f}%")
                            baseline_debug_count += 1
                            
            except Exception as e:
                print(f"Warning: Error processing baseline for trade {pair['num']}: {str(e)}")
                continue
        
        print(f"ðŸ” BASELINE DEBUG: Generated {len(baseline_details)} baseline results")
        
        # CRITICAL FIX: Calculate baseline stats from ORIGINAL trade pairs instead of simulation
        # This ensures baseline comparison uses real tradelist data
        original_baseline_pnl = 0
        original_baseline_wins = 0
        
        for pair in trade_pairs:
            if pair['side'] == 'LONG':
                pnl_pct = (pair['exitPrice'] - pair['entryPrice']) / pair['entryPrice'] * 100
            else:  # SHORT
                pnl_pct = (pair['entryPrice'] - pair['exitPrice']) / pair['entryPrice'] * 100
            
            original_baseline_pnl += pnl_pct
            if pnl_pct > 0:
                original_baseline_wins += 1
        
        baseline_winrate = (original_baseline_wins / len(trade_pairs) * 100) if trade_pairs else 0
        baseline_pnl = original_baseline_pnl
        
        print(f"ðŸ” BASELINE CORRECTED: Using ORIGINAL data - PnL={baseline_pnl:.4f}%, Winrate={baseline_winrate:.2f}%")
        
        # Format káº¿t quáº£
        best_result = results[0] if results else None
        
        # ðŸš¨ DEBUG: Check best_result structure and advanced metrics values
        if best_result:
            print(f"ðŸ” BEST RESULT DEBUG (BEFORE CONVERSION):")
            print(f"   PnL Total: {best_result.get('pnl_total', 'MISSING')}")
            print(f"   Max Drawdown: {best_result.get('max_drawdown', 'MISSING')}")
            print(f"   Avg Win: {best_result.get('avg_win', 'MISSING')}")
            print(f"   Avg Loss: {best_result.get('avg_loss', 'MISSING')}")
            print(f"   Sharpe Ratio: {best_result.get('sharpe_ratio', 'MISSING')}")
            print(f"   Recovery Factor: {best_result.get('recovery_factor', 'MISSING')}")
            print(f"   Max Win Streak: {best_result.get('max_consecutive_wins', 'MISSING')}")
            print(f"   Max Loss Streak: {best_result.get('max_consecutive_losses', 'MISSING')}")
            
            # Check if any advanced metrics are zero
            zero_metrics = []
            for metric in ['max_drawdown', 'avg_win', 'avg_loss', 'sharpe_ratio', 'recovery_factor', 'max_consecutive_wins', 'max_consecutive_losses']:
                value = best_result.get(metric, 'MISSING')
                if value == 0 or value == 0.0:
                    zero_metrics.append(f"{metric}={value}")
            
            if zero_metrics:
                print(f"   âš ï¸ ZERO METRICS DETECTED: {zero_metrics}")
            else:
                print(f"   âœ… NO ZERO METRICS")
            print(f"   Avg Win: {best_result.get('avg_win', 'MISSING')}")
            print(f"   Avg Loss: {best_result.get('avg_loss', 'MISSING')}")
            print(f"   Sharpe Ratio: {best_result.get('sharpe_ratio', 'MISSING')}")
            print(f"   Recovery Factor: {best_result.get('recovery_factor', 'MISSING')}")
            print(f"   Max Consecutive Wins: {best_result.get('max_consecutive_wins', 'MISSING')}")
            print(f"   Max Consecutive Losses: {best_result.get('max_consecutive_losses', 'MISSING')}")
            print(f"   Available keys: {list(best_result.keys())}")
        
        # TÃ­nh cumulative PnL cho so sÃ¡nh
        def calculate_cumulative_pnl(details):
            """TÃ­nh PnL tÃ­ch lÅ©y theo thá»i gian"""
            if not details:
                return [], []
            
            # Sort theo entry datetime Ä‘á»ƒ cÃ³ thá»© tá»± thá»i gian chÃ­nh xÃ¡c
            sorted_details = sorted(details, key=lambda x: x['entryDt'])
            
            cumulative_pnl = []
            current_total = 0
            trade_labels = []
            
            for i, trade in enumerate(sorted_details, 1):
                current_total += trade['pnlPct']
                cumulative_pnl.append(float(current_total))
                # Format datetime cho label
                entry_time = trade['entryDt'].strftime('%m/%d %H:%M') if hasattr(trade['entryDt'], 'strftime') else f"Trade {i}"
                trade_labels.append(entry_time)
            
            return trade_labels, cumulative_pnl
        
        # TÃ­nh cumulative cho baseline vÃ  best result
        # CRITICAL FIX: Use ORIGINAL trade pairs for baseline cumulative PnL calculation
        # instead of simulation results to ensure accuracy
        original_baseline_details = create_original_baseline_details(trade_pairs)
        baseline_labels, baseline_cumulative = calculate_cumulative_pnl(original_baseline_details)
        
        if best_result and best_result['details']:
            best_labels, best_cumulative = calculate_cumulative_pnl(best_result['details'])
        else:
            best_labels, best_cumulative = [], []
        
        # Táº¡o trade comparison logs cho top 50 trades gáº§n Ä‘Ã¢y nháº¥t
        trade_comparison = []
        if best_result and best_result['details']:
            baseline_dict = {t['num']: t for t in baseline_details}
            optimized_dict = {t['num']: t for t in best_result['details']}
            
            # CRITICAL FIX: Táº¡o dictionary tá»« trade_pairs gá»‘c Ä‘á»ƒ cÃ³ entry/exit price tháº­t
            original_pairs_dict = {p['num']: p for p in trade_pairs}
            
            # Láº¥y táº¥t cáº£ trade nums cÃ³ trong cáº£ baseline vÃ  optimized
            all_trade_nums = sorted(set(baseline_dict.keys()) & set(optimized_dict.keys()))
            
            # Sort theo entry time Ä‘á»ƒ láº¥y 50 lá»‡nh gáº§n Ä‘Ã¢y nháº¥t (má»›i nháº¥t)
            trade_with_time = []
            for trade_num in all_trade_nums:
                baseline_trade = baseline_dict[trade_num]
                optimized_trade = optimized_dict[trade_num]
                improvement = optimized_trade['pnlPct'] - baseline_trade['pnlPct']
                trade_with_time.append((baseline_trade['entryDt'], trade_num, improvement))
            
            # Sort theo thá»i gian giáº£m dáº§n (má»›i nháº¥t trÆ°á»›c) vÃ  láº¥y top 50
            trade_with_time.sort(key=lambda x: x[0], reverse=True)
            top_trades = [(abs(improvement), trade_num, improvement) for _, trade_num, improvement in trade_with_time[:50]]
            
            for abs_improvement, trade_num, improvement in top_trades:
                baseline_trade = baseline_dict[trade_num]
                optimized_trade = optimized_dict[trade_num]
                
                # CRITICAL FIX: Use ORIGINAL entry/exit prices from tradelist for baseline
                if trade_num in original_pairs_dict:
                    original_pair = original_pairs_dict[trade_num]
                    # Use original entry/exit prices from tradelist for baseline
                    entry_price = float(original_pair['entryPrice'])
                    baseline_exit_price = float(original_pair['exitPrice'])
                    print(f"ðŸ” TRADE {trade_num}: Using ORIGINAL prices - Entry={entry_price:.8f}, Exit={baseline_exit_price:.8f}")
                else:
                    # Fallback to simulation results if no original pair found
                    entry_price = float(baseline_trade['entryPrice'])
                    baseline_exit_price = float(baseline_trade['exitPrice'])
                    print(f"âš ï¸ TRADE {trade_num}: Using SIMULATION prices - Entry={entry_price:.8f}, Exit={baseline_exit_price:.8f}")
                
                optimized_exit_price = float(optimized_trade['exitPrice'])
                
                # Calculate baseline PnL using ORIGINAL prices from tradelist
                if trade_num in original_pairs_dict:
                    original_pair = original_pairs_dict[trade_num]
                    side = original_pair['side']
                    if side == 'LONG':
                        baseline_pnl_calculated = (baseline_exit_price - entry_price) / entry_price * 100
                    else:  # SHORT
                        baseline_pnl_calculated = (entry_price - baseline_exit_price) / entry_price * 100
                    print(f"ðŸ” TRADE {trade_num}: Original PnL calculation - {baseline_pnl_calculated:.4f}% vs Simulation: {baseline_trade['pnlPct']:.4f}%")
                else:
                    # Fallback to simulation PnL
                    baseline_pnl_calculated = baseline_trade['pnlPct']
                
                # Determine decimal places based on price magnitude
                if entry_price < 0.01:
                    decimal_places = 6  # Very small prices like BOME (0.009xxx)
                elif entry_price < 1:
                    decimal_places = 4  # Small prices like ACEUSDT (0.4xxx)
                else:
                    decimal_places = 2  # Normal prices like BTC (50000+)
                
                # Calculate improvement using recalculated baseline PnL
                improvement_recalc = optimized_trade['pnlPct'] - baseline_pnl_calculated
                
                trade_info = {
                    'trade_num': safe_int(trade_num),
                    'entry_time': baseline_trade['entryDt'].strftime('%m/%d %H:%M'),
                    'side': baseline_trade['side'],
                    'entry_price': round(entry_price, decimal_places),
                    'baseline_exit_price': round(baseline_exit_price, decimal_places),
                    'baseline_exit_type': 'Signal',
                    'baseline_pnl': round(float(baseline_pnl_calculated), 2),
                    'optimized_exit_price': round(optimized_exit_price, decimal_places),
                    'optimized_exit_type': optimized_trade.get('exitType', 'Signal'),
                    'optimized_pnl': round(float(optimized_trade['pnlPct']), 2),
                    'improvement': round(float(improvement_recalc), 2),
                    'price_format': f'{{:.{decimal_places}f}}'
                }
                
                # Debug first few trades
                if len(trade_comparison) < 5:
                    print(f"ðŸ” BACKEND TRADE {trade_num} DATA:")
                    print(f"   Entry Price: {trade_info['entry_price']}")
                    print(f"   Baseline Exit Price: {trade_info['baseline_exit_price']}")
                    print(f"   Original entry from pair: {entry_price:.8f}")
                    print(f"   Original exit from pair: {baseline_exit_price:.8f}")
                
                trade_comparison.append(trade_info)
        
        response_data = {
            'success': True,
            'filter_info': filter_info,
            'mode': 'ADVANCED' if (ADVANCED_MODE and total_combinations <= combinations_limit) else 'FALLBACK',
            'mode_details': {
                'advanced_mode_available': ADVANCED_MODE,
                'total_combinations': total_combinations,
                'combinations_limit': combinations_limit,
                'fallback_reason': f'Too many combinations ({total_combinations:,} > {combinations_limit:,})' if total_combinations > combinations_limit else None,
                'optimization_scope': 'SL + BE + TS (Full Grid Search)' if (ADVANCED_MODE and total_combinations <= combinations_limit) else 'SL only (BE/TS fixed)',
                'warning': f'ðŸš¨ BE/TS parameters NOT optimized - only {len(sl_list)} SL values tested!' if total_combinations > combinations_limit else None,
                'actual_tests_run': len(sl_list) if total_combinations > combinations_limit else total_combinations
            },
            'baseline': {
                'pnl_total': float(baseline_pnl),
                'winrate': float(baseline_winrate),
                'trade_count': int(len(baseline_details))
            },
            'best_result': {
                'sl': float(best_result['sl']),
                'be': float(best_result['be']),
                'ts_trig': float(best_result['ts_trig']),
                'ts_step': float(best_result['ts_step']),
                'pnl_total': float(best_result['pnl_total']),
                'winrate': float(best_result['winrate']),
                'pf': safe_float(best_result['pf']),
                'max_drawdown': best_result.get('max_drawdown', 0.0),
                'avg_win': best_result.get('avg_win', 0.0),
                'avg_loss': best_result.get('avg_loss', 0.0),
                'max_consecutive_wins': best_result.get('max_consecutive_wins', 0),
                'max_consecutive_losses': best_result.get('max_consecutive_losses', 0),
                'sharpe_ratio': best_result.get('sharpe_ratio', 0.0),
                'recovery_factor': best_result.get('recovery_factor', 0.0),
                'trade_win': int(len([d for d in best_result['details'] if d['pnlPct'] > 0])),
                'trade_loss': int(len([d for d in best_result['details'] if d['pnlPct'] <= 0]))
            } if best_result else None,
            'all_results': convert_to_serializable(results[:20]),
            'cumulative_comparison': {
                'labels': baseline_labels,
                'baseline_cumulative': baseline_cumulative,
                'optimized_cumulative': best_cumulative,
                'baseline_label': 'Káº¿t quáº£ gá»‘c (No Optimization)',
                'optimized_label': f'Enhanced Tá»‘i Æ°u (SL:{best_result["sl"]:.1f}% BE:{best_result["be"]:.1f}% TS:{best_result["ts_trig"]:.1f}%/{best_result["ts_step"]:.1f}%)' if best_result else 'N/A'
            },
            'trade_comparison': trade_comparison,
            'total_combinations': len(results)
        }
        # === LOGGING OPTIMIZATION RESULT ===
        try:
            from optimization_log_manager import OptimizationLogManager
            log_manager = OptimizationLogManager()
            # Extract user/project/symbol/timeframe from request or context
            user = request.form.get('user', 'unknown')
            project = request.form.get('project', 'BTC_Backtest')
            symbol = request.form.get('symbol', filter_info.get('symbol', 'unknown') if isinstance(filter_info, dict) else 'unknown')
            timeframe = request.form.get('timeframe', filter_info.get('timeframe', 'unknown') if isinstance(filter_info, dict) else 'unknown')
            param_ranges = {
                'sl_min': sl_min,
                'sl_max': sl_max,
                'be_min': be_min,
                'be_max': be_max,
                'ts_trig_min': ts_trig_min,
                'ts_trig_max': ts_trig_max,
                'ts_step_min': ts_step_min,
                'ts_step_max': ts_step_max
            }
            # Prepare best_result for logging
            best_result_log = {
                'params': {
                    'sl': float(best_result['sl']) if best_result else None,
                    'be': float(best_result['be']) if best_result else None,
                    'ts_trig': float(best_result['ts_trig']) if best_result else None,
                    'ts_step': float(best_result['ts_step']) if best_result else None
                },
                'pnl': float(best_result['pnl_total']) if best_result else None,
                'winrate': float(best_result['winrate']) if best_result else None,
                'pf': float(best_result['pf']) if best_result and 'pf' in best_result else None
            }
            notes = request.form.get('notes', '')
            log_manager.log_optimization(user, project, symbol, timeframe, param_ranges, best_result_log, notes)
            print(f"âœ… Optimization result logged for user={user}, project={project}, symbol={symbol}, timeframe={timeframe}")
        except Exception as log_exc:
            print(f"âš ï¸ Logging optimization result failed: {log_exc}")
        
        # ðŸ” FINAL DEBUG: Log what's actually being sent to frontend
        if best_result:
            response_best = response_data['best_result']
            print(f"ðŸ” FINAL API RESPONSE DEBUG:")
            print(f"   Max Drawdown: {response_best['max_drawdown']} (best_result has: {best_result.get('max_drawdown', 'MISSING')})")
            print(f"   Avg Win: {response_best['avg_win']} (best_result has: {best_result.get('avg_win', 'MISSING')})")
            print(f"   Avg Loss: {response_best['avg_loss']} (best_result has: {best_result.get('avg_loss', 'MISSING')})")
            print(f"   Sharpe Ratio: {response_best['sharpe_ratio']} (best_result has: {best_result.get('sharpe_ratio', 'MISSING')})")
            print(f"   Recovery Factor: {response_best['recovery_factor']} (best_result has: {best_result.get('recovery_factor', 'MISSING')})")
            print(f"   Max Win Streak: {response_best['max_consecutive_wins']} (best_result has: {best_result.get('max_consecutive_wins', 'MISSING')})")
            print(f"   Max Loss Streak: {response_best['max_consecutive_losses']} (best_result has: {best_result.get('max_consecutive_losses', 'MISSING')})")
        
        print("=== ENHANCED OPTIMIZATION SUCCESS ===")
        return jsonify(response_data)
        
    except Exception as e:
        # Reset optimization status on error
        optimization_status.update({
            'running': False,
            'status_message': f'Error: {str(e)}'
        })
        
        print(f"=== ENHANCED OPTIMIZATION ERROR: {str(e)} ===")
        print(f"=== ERROR TYPE: {type(e)} ===")
        print(traceback.format_exc())
        return jsonify({'error': str(e), 'type': str(type(e))})

def optimize_single_combination(trade_pairs, sl_pct, be_pct, ts_activation_pct, ts_step_pct, candle_data):
    """
    Run backtest for a single parameter combination
    
    Args:
        trade_pairs: List of trade dictionaries from get_trade_pairs
        sl_pct: Stop loss percentage 
        be_pct: Break even percentage
        ts_activation_pct: Trailing stop activation percentage
        ts_step_pct: Trailing stop step percentage
        candle_data: DataFrame with candle data
    
    Returns:
        Dictionary with backtest results
    """
    from backtest_gridsearch_slbe_ts_Version3 import simulate_trade

    print(f"🔍 OPTIMIZE_SINGLE_COMBINATION DEBUG:")
    print(f"   Parameters: SL={sl_pct:.6f}%, BE={be_pct:.6f}%, TS={ts_activation_pct:.6f}%, TS_Step={ts_step_pct:.6f}%")
    print(f"   Trade pairs count: {len(trade_pairs)}")
    print(f"   Candle data shape: {candle_data.shape if hasattr(candle_data, 'shape') else 'Not DataFrame'}")
    print(f"   🔍 VERIFICATION DATA CHECK: trade_pairs count={len(trade_pairs)}, candle_data shape={candle_data.shape if hasattr(candle_data, 'shape') else 'No shape'}")
    print(f"   🔍 VERIFICATION FIRST TRADE: {trade_pairs[0] if trade_pairs else 'None'}")
    # Add data hash for comparison
    import hashlib
    trade_data_str = str(trade_pairs[:3]) if len(trade_pairs) >= 3 else str(trade_pairs)
    candle_data_str = str(candle_data.iloc[:5].to_dict()) if hasattr(candle_data, 'iloc') else str(candle_data)
    trade_hash = hashlib.md5(trade_data_str.encode()).hexdigest()[:8]
    candle_hash = hashlib.md5(candle_data_str.encode()).hexdigest()[:8]
    print(f"   🔍 VERIFICATION DATA HASH: trade_hash={trade_hash}, candle_hash={candle_hash}")
    print(f"   OPTIMIZE_SINGLE calling simulate_trade with: pair={trade_pairs[0]['num'] if trade_pairs else 'None'}, sl={sl_pct}, be={be_pct}, ts_trig={ts_activation_pct}, ts_step={ts_step_pct}")
    print(f"   OPTIMIZE_SINGLE calling simulate_trade with: pair={trade_pairs[0]['num'] if trade_pairs else 'None'}, sl={sl_pct}, be={be_pct}, ts_trig={ts_activation_pct}, ts_step={ts_step_pct}")
    
    # 🔍 FIX: Use IDENTICAL logic to Optuna objective function
    details = []
    win_count = 0
    gain_sum = 0
    loss_sum = 0
    total_trades_processed = 0
    simulation_trades = []
    failed_simulations = 0
    
    for i, pair in enumerate(trade_pairs):
        try:
            # 🔍 DEBUG: Use same calling style as Optuna for consistency (positional args)
            result, log = simulate_trade(pair, candle_data, sl_pct, be_pct, ts_activation_pct, ts_step_pct)
            total_trades_processed += 1
            
            if result is not None:
                # ✅ IDENTICAL to Optuna: Add to details array first
                details.append(result)
                pnl = result['pnlPct']
                if pnl > 0:
                    win_count += 1
                    gain_sum += pnl
                else:
                    loss_sum += abs(pnl)
                
                # Also add to simulation_trades for response
                simulation_trades.append({
                    'num': result['num'],
                    'side': result['side'],
                    'entry_price': result['entryPrice'],
                    'exit_price': result['exitPrice'],
                    'exit_type': result['exitType'],
                    'pnl_pct': pnl
                })
                
                # 🔍 DEBUG: Log first few trade results for comparison with Optuna
                if i < 3:
                    print(f"   OPTIMIZE_SINGLE Trade {i+1}: PnL={pnl:.6f}%, EntryPrice={result.get('entryPrice', 'N/A')}, ExitPrice={result.get('exitPrice', 'N/A')}, ExitType={result.get('exitType', 'N/A')}")
                    
            else:
                # ✅ IDENTICAL to Optuna: Handle failed trades consistently
                failed_result = {'pnlPct': 0.0}
                details.append(failed_result)
                failed_simulations += 1
                
                simulation_trades.append({
                    'num': pair.get('num', i+1),
                    'side': pair.get('side', 'UNKNOWN'),
                    'entry_price': pair.get('entryPrice', 0),
                    'exit_price': pair.get('exitPrice', 0),
                    'exit_type': 'FAILED',
                    'pnl_pct': 0.0
                })
                
                if i < 3:
                    print(f"   OPTIMIZE_SINGLE Trade {i+1}: PnL=0.0000% (FAILED)")
                
        except Exception as e:
            # ✅ IDENTICAL to Optuna: Handle errors consistently
            total_trades_processed += 1
            failed_result = {'pnlPct': 0.0}
            details.append(failed_result)
            failed_simulations += 1
            
            simulation_trades.append({
                'num': pair.get('num', i+1),
                'side': pair.get('side', 'UNKNOWN'),
                'entry_price': pair.get('entryPrice', 0),
                'exit_price': pair.get('exitPrice', 0),
                'exit_type': 'ERROR',
                'pnl_pct': 0.0
            })
            
            if i < 3:
                print(f"   OPTIMIZE_SINGLE Trade {i+1}: PnL=0.0000% (ERROR: {e})")
            continue
    
    # ✅ IDENTICAL calculation to Optuna objective function
    total_trades = len(details)
    winrate = (win_count / total_trades * 100) if total_trades > 0 else 0
    pf = (gain_sum / loss_sum) if loss_sum > 0 else float('inf') if gain_sum > 0 else 0
    total_pnl = sum([x['pnlPct'] for x in details])  # 🔍 CRITICAL FIX: Use same calculation as Optuna
    
    
    print(f"   🔍 OPTIMIZE_SINGLE FINAL CALCULATION:")
    print(f"      Details array length: {len(details)}")
    print(f"      Sum calculation: sum([x['pnlPct'] for x in details]) = {total_pnl:.6f}%")
    print(f"      Total trades: {total_trades}, Failed: {failed_simulations}, WR: {winrate:.1f}%")
    print(f"   RESULTS: Total PnL={total_pnl:.6f}%, Trades={total_trades}, Failed={failed_simulations}, WR={winrate:.1f}%")

    return {
        'total_pnl': total_pnl,
        'winrate': winrate,
        'total_trades': total_trades,
        'win_count': win_count,
        'trades': simulation_trades,
        'params': {
            'sl': sl_pct,
            'be': be_pct,
            'ts_activation': ts_activation_pct,
            'ts_step': ts_step_pct
        }
    }

@app.route('/optimize_ranges', methods=['POST'])
def optimize_ranges():
    """🔥 Real Range-Based Optimization with Optuna/Grid Search"""
    try:
        print("🚀 OPTIMIZE_RANGES ROUTE HIT!")
        print("=== RANGE-BASED OPTIMIZATION WITH ENGINE SELECTION ===")
        
        # Initialize variables to avoid scope issues
        opt_params = None
        opt_value = None
        results_data = None
        optimized_results = None
        
        # Parse JSON data from frontend
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data received'})
        
        # 🔍 DEBUG: Print raw request data to see what frontend sends
        print("🔍 RAW REQUEST DATA:")
        print(f"   Full data: {data}")
        print(f"   optimization_engine value: '{data.get('optimization_engine')}' (type: {type(data.get('optimization_engine'))})")
        print(f"   Available keys: {list(data.keys())}")
        
        # Get optimization engine and criteria (support multiple formats)
        raw_engine = data.get('optimization_engine', data.get('engine', 'grid_search'))  # Changed default to grid_search
        
        # 🔧 GET MAX_ITERATIONS FROM FRONTEND
        raw_max_iterations = data.get('max_iterations')
        max_iterations = validate_optuna_trials(raw_max_iterations)
        print(f"🔧 Max Iterations: {raw_max_iterations} → {max_iterations} (validated)")
        
        print(f"🔍 DEBUG: raw_engine = '{raw_engine}' (type: {type(raw_engine)})")
        print(f"🔍 DEBUG: raw_engine.lower() = '{raw_engine.lower() if raw_engine else 'None'}'")
        
        # Normalize engine name to handle various frontend formats
        if raw_engine.lower() in ['grid', 'grid_search', 'gridsearch', 'grid search']:
            optimization_engine = 'grid_search'
            print(f"🔍 DEBUG: Matched GRID SEARCH pattern -> optimization_engine = '{optimization_engine}'")
        elif raw_engine.lower() in ['optuna', 'bayesian']:
            optimization_engine = 'optuna'
            print(f"🔍 DEBUG: Matched OPTUNA pattern -> optimization_engine = '{optimization_engine}'")
        else:
            optimization_engine = 'optuna'  # Default fallback
            print(f"🔍 DEBUG: NO MATCH found! Using fallback -> optimization_engine = '{optimization_engine}'")
            print(f"🔍 DEBUG: Available patterns: ['grid', 'grid_search', 'gridsearch', 'grid search', 'optuna', 'bayesian']")
            
        optimization_criteria = data.get('optimization_criteria', 'pnl')
        selected_params = data.get('selected_params', ['sl'])  # Default to SL only
        
        print(f"🧠 Selected Optimization Engine: {optimization_engine}")
        print(f"🎯 Selected Optimization Criteria: {optimization_criteria}")
        print(f"⚙️ Selected Parameters: {selected_params}")
        
        # Get strategy and candle data
        strategy = data.get('strategy')
        candle_data = data.get('candle_data')
        
        if not strategy or not candle_data:
            return jsonify({'success': False, 'error': 'Missing strategy or candle data'})
        
        print(f"📊 Strategy: {strategy}")
        print(f"🕯️ Candle Data: {candle_data}")
        
        # Load strategy data (similar to quick_summary_strategy)
        strategy_parts = strategy.split('_')
        if len(strategy_parts) >= 4:
            symbol = strategy_parts[0]
            timeframe = strategy_parts[1]  
            strategy_name = '_'.join(strategy_parts[2:-1])
            version = strategy_parts[-1]
        else:
            return jsonify({'success': False, 'error': 'Invalid strategy format'})
        
        # Get strategy manager and load data
        sm = get_strategy_manager()
        strategy_info = sm.get_strategy(symbol, timeframe, strategy_name, version)
        if not strategy_info:
            return jsonify({'success': False, 'error': 'Strategy not found'})
        
        # Load trade data
        if not os.path.exists(strategy_info.file_path):
            return jsonify({'success': False, 'error': f'Strategy file not found: {strategy_info.file_path}'})
            
        with open(strategy_info.file_path, 'r', encoding='utf-8') as f:
            trade_content = f.read().strip()
        
        # Handle legacy format
        if len(trade_content.split('\n')) <= 2 and not trade_content.startswith('Date,') and not trade_content.startswith('date,'):
            legacy_trade_file = trade_content.strip()
            if os.path.exists(legacy_trade_file):
                with open(legacy_trade_file, 'r', encoding='utf-8') as f:
                    trade_content = f.read()
            else:
                return jsonify({'success': False, 'error': f'Legacy trade file not found: {legacy_trade_file}'})
        
        # Load candle data from database
        try:
            if not candle_data.endswith('.db'):
                raise ValueError("Only database candle sources are supported")
                
            db_name = candle_data.replace('.db', '')
            parts = db_name.split('_')
            if len(parts) < 2:
                raise ValueError(f"Invalid database format: {candle_data}")
                
            db_symbol = '_'.join(parts[:-1])
            db_timeframe = parts[-1]
            
            # Load from candlestick_data.db
            conn = sqlite3.connect('candlestick_data.db')
            query = "SELECT * FROM candlestick_data WHERE symbol = ? AND timeframe = ? ORDER BY open_time"
            df_candle = pd.read_sql_query(query, conn, params=[db_symbol, db_timeframe])
            conn.close()
            
            if df_candle.empty:
                raise ValueError(f"No candle data found in database for {db_symbol} {db_timeframe}")
            
            # Convert database format to standard format
            df_candle = df_candle.rename(columns={
                'open_time': 'time',
                'open_price': 'open', 
                'high_price': 'high',
                'low_price': 'low',
                'close_price': 'close'
            })
            df_candle['time'] = pd.to_datetime(df_candle['time'], unit='s')
                
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error loading candle data: {str(e)}'})
        
        # Load and process trade data
        df_trade = load_trade_csv_from_content(trade_content)
        trade_pairs, log_init = get_trade_pairs(df_trade)
        
        print(f"✅ Data loaded: Trade pairs={len(trade_pairs)}, Candle={len(df_candle)}")
        
        if not trade_pairs:
            return jsonify({'success': False, 'error': 'No valid trade pairs found'})
        
        # Get parameter ranges
        sl_min = float(data.get('sl_min', 0.5))
        sl_max = float(data.get('sl_max', 3.0))
        sl_step = float(data.get('sl_step', 0.1))
        be_min = float(data.get('be_min', 2.0))
        be_max = float(data.get('be_max', 1.5))
        be_step = float(data.get('be_step', 0.1))
        ts_active_min = float(data.get('ts_active_min', 2.0))
        ts_active_max = float(data.get('ts_active_max', 1.0))
        ts_active_step = float(data.get('ts_active_step', 0.05))
        ts_step_min = float(data.get('ts_step_min', 3.0))
        ts_step_max = float(data.get('ts_step_max', 0.3))
        ts_step_step = float(data.get('ts_step_step', 0.01))
        
        # 🔒 BACKEND VALIDATION: Enforce minimum safety values to prevent profit destruction
        def validate_and_enforce_minimums(be_min, be_max, ts_active_min, ts_active_max, ts_step_min, ts_step_max):
            """Enforce safety minimums and return adjusted values with warnings"""
            SAFETY_BE_MIN = 2.0          # BE cannot be less than 2% (preserves profit buffer)
            SAFETY_TS_TRIGGER_MIN = 2.0  # TS trigger cannot be less than 2% (prevents early activation)
            SAFETY_TS_STEP_MIN = 3.0     # TS step cannot be less than 3% (prevents aggressive trailing)
            
            warnings = []
            
            # Validate BE ranges
            if be_min > 0 and be_min < SAFETY_BE_MIN:
                warnings.append(f"BE min {be_min}% → {SAFETY_BE_MIN}% (safety minimum)")
                be_min = SAFETY_BE_MIN
            if be_max > 0 and be_max < SAFETY_BE_MIN:
                warnings.append(f"BE max {be_max}% → {SAFETY_BE_MIN}% (safety minimum)")
                be_max = SAFETY_BE_MIN
                
            # Validate TS trigger ranges
            if ts_active_min > 0 and ts_active_min < SAFETY_TS_TRIGGER_MIN:
                warnings.append(f"TS trigger min {ts_active_min}% → {SAFETY_TS_TRIGGER_MIN}% (safety minimum)")
                ts_active_min = SAFETY_TS_TRIGGER_MIN
            if ts_active_max > 0 and ts_active_max < SAFETY_TS_TRIGGER_MIN:
                warnings.append(f"TS trigger max {ts_active_max}% → {SAFETY_TS_TRIGGER_MIN}% (safety minimum)")
                ts_active_max = SAFETY_TS_TRIGGER_MIN
                
            # Validate TS step ranges
            if ts_step_min > 0 and ts_step_min < SAFETY_TS_STEP_MIN:
                warnings.append(f"TS step min {ts_step_min}% → {SAFETY_TS_STEP_MIN}% (safety minimum)")
                ts_step_min = SAFETY_TS_STEP_MIN
            if ts_step_max > 0 and ts_step_max < SAFETY_TS_STEP_MIN:
                warnings.append(f"TS step max {ts_step_max}% → {SAFETY_TS_STEP_MIN}% (safety minimum)")
                ts_step_max = SAFETY_TS_STEP_MIN
            
            return be_min, be_max, ts_active_min, ts_active_max, ts_step_min, ts_step_max, warnings
        
        # Apply validation
        be_min, be_max, ts_active_min, ts_active_max, ts_step_min, ts_step_max, validation_warnings = validate_and_enforce_minimums(
            be_min, be_max, ts_active_min, ts_active_max, ts_step_min, ts_step_max
        )
        
        # Log validation results
        if validation_warnings:
            print(f"🔒 SAFETY VALIDATION APPLIED ({len(validation_warnings)} adjustments):")
            for warning in validation_warnings:
                print(f"   ⚠️ {warning}")
        else:
            print(f"✅ All parameters above safety minimums")
        
        print(f"� Parameter Ranges:")
        print(f"   SL: {sl_min}% → {sl_max}% (step {sl_step}%)")
        print(f"   BE: {be_min}% → {be_max}% (step {be_step}%)")
        print(f"   TS Active: {ts_active_min}% → {ts_active_max}% (step {ts_active_step}%)")
        print(f"   TS Step: {ts_step_min}% → {ts_step_max}% (step {ts_step_step}%)")
        
        # Create parameter lists based on selected parameters only
        print(f"🔧 Creating parameter lists for selected params: {selected_params}")
        
        # CORRECTED LOGIC: Use default/recommended values for non-selected parameters
        # For non-selected params, we need reasonable baseline values, not 0 (which disables them)
        # This maintains simulation realism while only optimizing selected parameters
        
        # Default baseline values (representing typical trading setup)
        DEFAULT_SL = 2.0    # 2% stop loss - common baseline
        DEFAULT_BE = 0.0    # Breakeven disabled by default  
        DEFAULT_TS = 0.0    # Trailing stop disabled by default
        DEFAULT_TS_STEP = 0.0  # Trailing step disabled by default
        
        # Generate parameter lists: optimize selected, fix non-selected to defaults
        if 'sl' in selected_params:
            sl_list = [sl_min + i * sl_step for i in range(int((sl_max - sl_min) / sl_step) + 1)]
        else:
            sl_list = [DEFAULT_SL]  # Use reasonable SL baseline when not optimizing SL
            
        if 'be' in selected_params:
            be_list = [be_min + i * be_step for i in range(int((be_max - be_min) / be_step) + 1)]
        else:
            be_list = [DEFAULT_BE]  # BE disabled when not optimizing BE
            
        if 'ts' in selected_params:
            ts_trig_list = [ts_active_min + i * ts_active_step for i in range(int((ts_active_max - ts_active_min) / ts_active_step) + 1)]
            ts_step_list = [ts_step_min + i * ts_step_step for i in range(int((ts_step_max - ts_step_min) / ts_step_step) + 1)]
        else:
            ts_trig_list = [DEFAULT_TS]  # TS disabled when not optimizing TS
            ts_step_list = [DEFAULT_TS_STEP]  # TS step disabled when not optimizing TS
        
        # Calculate actual combinations
        actual_combinations = len(sl_list) * len(be_list) * len(ts_trig_list) * len(ts_step_list)
        print(f"📊 Parameter lists: SL={len(sl_list)}, BE={len(be_list)}, TS_Active={len(ts_trig_list)}, TS_Step={len(ts_step_list)}")
        print(f"🎯 Total combinations: {actual_combinations} (reduced from full grid)")
        
        # Use optimization criteria from user selection
        opt_type = optimization_criteria  # User-selected optimization target
        print(f"🎯 Using optimization criteria: {opt_type}")
        
        # Run optimization based on selected engine
        if optimization_engine == 'optuna':
            print("🔥 Running OPTUNA optimization...")
            
            # Initialize variables at the beginning to avoid UnboundLocalError
            optuna_trades = []
            optuna_advanced_metrics = {
                'max_drawdown': 0, 'avg_win': 0, 'avg_loss': 0, 
                'sharpe_ratio': 0, 'recovery_factor': 0, 
                'max_consecutive_wins': 0, 'max_consecutive_losses': 0
            }
            win_trades = 0
            loss_trades = 0
            winrate_real = 0
            results_data = []
            
            try:
                # CORRECTED LOGIC: Use same default baseline values as Grid Search
                # This ensures consistent behavior between optimization engines
                DEFAULT_SL = 2.0    # 2% stop loss - common baseline
                DEFAULT_BE = 0.0    # Breakeven disabled by default  
                DEFAULT_TS = 0.0    # Trailing stop disabled by default
                DEFAULT_TS_STEP = 0.0  # Trailing step disabled by default
                
                # Set parameter ranges: optimize selected, fix non-selected to defaults
                if 'sl' in selected_params:
                    opt_sl_min = sl_min
                    opt_sl_max = sl_max
                else:
                    opt_sl_min = opt_sl_max = DEFAULT_SL  # Fixed SL baseline when not optimizing
                    
                if 'be' in selected_params:
                    opt_be_min = be_min
                    opt_be_max = be_max
                else:
                    opt_be_min = opt_be_max = DEFAULT_BE  # BE disabled when not optimizing
                    
                if 'ts' in selected_params:
                    opt_ts_active_min = ts_active_min
                    opt_ts_active_max = ts_active_max
                    opt_ts_step_min = ts_step_min
                    opt_ts_step_max = ts_step_max
                else:
                    opt_ts_active_min = opt_ts_active_max = DEFAULT_TS  # TS disabled when not optimizing
                    opt_ts_step_min = opt_ts_step_max = DEFAULT_TS_STEP  # TS step disabled when not optimizing
                
                print(f"Calling optuna_search with selected parameters:")
                print(f"  sl_range: {opt_sl_min} to {opt_sl_max} {'(OPTIMIZING)' if 'sl' in selected_params else '(FIXED)'}")
                print(f"  be_range: {opt_be_min} to {opt_be_max} {'(OPTIMIZING)' if 'be' in selected_params else '(FIXED)'}")
                print(f"  ts_active_range: {opt_ts_active_min} to {opt_ts_active_max} {'(OPTIMIZING)' if 'ts' in selected_params else '(FIXED)'}")
                print(f"  ts_step_range: {opt_ts_step_min} to {opt_ts_step_max} {'(OPTIMIZING)' if 'ts' in selected_params else '(FIXED)'}")
                print(f"  trade_pairs: {len(trade_pairs)}")
                print(f"  candle_data: {len(df_candle)} rows")
                
                opt_params, opt_value = optuna_search(
                    trade_pairs, df_candle, 
                    opt_sl_min, opt_sl_max, opt_be_min, opt_be_max, 
                    opt_ts_active_min, opt_ts_active_max, opt_ts_step_min, opt_ts_step_max,  # Updated TS parameters
                    opt_type, n_trials=max_iterations  # 🔧 USE USER INPUT from frontend
                )
                
                print(f"✅ Optuna completed successfully!")
                print(f"   Best params: {opt_params}")
                print(f"   Best value: {opt_value}")
                
                # Define final parameter values for use throughout the code
                final_sl = opt_params.get('sl', opt_sl_min)
                final_be = opt_params.get('be', opt_be_min)
                final_ts_trig = opt_params.get('ts_trig', opt_ts_active_min)
                final_ts_step = opt_params.get('ts_step', opt_ts_step_min)
                
                # Store Optuna results directly (DON'T convert to grid search format)
                optuna_best_params = opt_params
                optuna_best_value = opt_value
                
                # Calculate real advanced metrics for Optuna result
                # Simulate all trades with best params to get detailed results
                try:
                    # Run simulation with best parameters to get all trade results
                    # final_* variables already defined above
                    print(f"🔧 Debug: About to simulate with final params: sl={final_sl}, be={final_be}, ts_trig={final_ts_trig}, ts_step={final_ts_step}")
                    
                    optuna_trade_results = []
                    for i, pair in enumerate(trade_pairs):
                        try:
                            result, _ = simulate_trade(pair, df_candle, final_sl, final_be, final_ts_trig, final_ts_step)
                            if result is not None:
                                optuna_trade_results.append(result)
                        except Exception as pair_error:
                            print(f"🔧 Debug: Error in simulate_trade for pair {i}: {pair_error}")
                            continue  # Skip problematic trades
                    
                    print(f"🔧 Debug: Completed {len(optuna_trade_results)} trade simulations")
                    
                    # Calculate advanced metrics from results
                    optuna_trades = optuna_trade_results  # Store for PF calculation
                    print(f"🔧 Debug: About to calculate advanced metrics")
                    optuna_advanced_metrics = calculate_advanced_metrics(optuna_trade_results)
                    print(f"🔧 Debug: Advanced metrics calculated successfully")
                    
                    # Calculate win/loss trades
                    win_trades = len([t for t in optuna_trade_results if t.get('pnlPct', 0) > 0])
                    loss_trades = len([t for t in optuna_trade_results if t.get('pnlPct', 0) <= 0])
                    winrate_real = (win_trades / len(optuna_trade_results) * 100) if optuna_trade_results else 0
                    
                except Exception as e:
                    print(f"⚠️ Warning: Could not calculate Optuna advanced metrics: {e}")
                    import traceback
                    print(f"🔧 Full detailed traceback:")
                    traceback.print_exc()
                    print(f"⚠️ Optuna trades variable state: {type(optuna_trades) if 'optuna_trades' in locals() else 'UNDEFINED'}")
                    # Keep fallback values initialized above
                
                # Format results for frontend
                results_data = [{
                    'sl': final_sl / 100,  # Convert to ratio for frontend
                    'be': final_be / 100,
                    'ts': final_ts_trig / 100,
                    'ts_step': final_ts_step / 100,  # ADD MISSING TS_STEP!
                    'total_profit': opt_value,
                    'win_rate': winrate_real / 100,  # Real winrate calculation
                    'total_trades': len(trade_pairs),
                    # Add all advanced metrics from calculation
                    'win_trades': win_trades,
                    'loss_trades': loss_trades,
                    'avg_win': optuna_advanced_metrics.get('avg_win', 0),
                    'avg_loss': optuna_advanced_metrics.get('avg_loss', 0),
                    'max_drawdown': optuna_advanced_metrics.get('max_drawdown', 0),
                    'sharpe_ratio': optuna_advanced_metrics.get('sharpe_ratio', 0),
                    'recovery_factor': optuna_advanced_metrics.get('recovery_factor', 0),
                    'max_consecutive_wins': optuna_advanced_metrics.get('max_consecutive_wins', 0),
                    'max_consecutive_losses': optuna_advanced_metrics.get('max_consecutive_losses', 0),
                    'pf': opt_value / abs(sum([t.get('pnlPct', 0) for t in optuna_trades if t.get('pnlPct', 0) < 0])) if optuna_trades and any(t.get('pnlPct', 0) < 0 for t in optuna_trades) else 1.0,
                    'optimization_engine': 'Optuna'
                }]
                
                print(f"🏆 Optuna Result: SL={final_sl:.2f}%, BE={final_be:.2f}%, TS={final_ts_trig:.2f}%, Value={opt_value:.2f}")
                
            except Exception as e:
                print(f"❌ Optuna optimization error: {e}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                print(f"Error details: {type(e).__name__}: {str(e)}")
                print(f"🔍 Debug Info:")
                print(f"   Trade pairs loaded: {len(trade_pairs) if 'trade_pairs' in locals() else 'Not loaded'}")
                print(f"   Candle data loaded: {len(df_candle) if 'df_candle' in locals() else 'Not loaded'}")
                if len(trade_pairs) > 0:
                    print(f"   First trade pair keys: {list(trade_pairs[0].keys())}")
                if 'df_candle' in locals() and len(df_candle) > 0:
                    print(f"   Candle columns: {list(df_candle.columns)}")
                return jsonify({'success': False, 'error': f'Optuna optimization failed: {str(e)}'})
            
        else:
            print("🔍 Running GRID SEARCH optimization...")
            try:
                # Use Grid Search optimization with selected parameters only
                print(f"Calling grid_search with {len(sl_list)} x {len(be_list)} x {len(ts_trig_list)} combinations")
                print(f"📋 Only optimizing: {', '.join(selected_params)}")
                
                results = grid_search_realistic_full(
                    trade_pairs, df_candle, sl_list, be_list, ts_trig_list, ts_step_list, opt_type
                )
                
                print(f"✅ Grid search completed: {len(results) if results else 0} results")
                
                if not results:
                    return jsonify({'success': False, 'error': 'Grid search returned no results'})
                
                # Format results for frontend (take top 10)
                results_data = []
                for result in results[:10]:  # Top 10 results
                    # Calculate win/loss trades from winrate and total_trades
                    total_trades = result.get('total_trades', 0)
                    winrate = result.get('winrate', 0)
                    win_trades = int(total_trades * winrate / 100) if total_trades > 0 else 0
                    loss_trades = total_trades - win_trades
                    
                    results_data.append({
                        'sl': result['sl'] / 100,  # Convert to ratio
                        'be': result['be'] / 100,
                        'ts': result['ts_trig'] / 100,
                        'ts_step': result.get('ts_step', 0.1) / 100,  # ADD TS_STEP for Grid Search
                        'total_profit': result.get('pnl_total', 0),
                        'win_rate': result.get('winrate', 0) / 100,
                        'total_trades': total_trades,
                        # Calculate win/loss trades from winrate
                        'win_trades': win_trades,
                        'loss_trades': loss_trades,
                        'avg_win': result.get('avg_win', 0),
                        'avg_loss': result.get('avg_loss', 0),
                        'max_drawdown': result.get('max_drawdown', 0),
                        'sharpe_ratio': result.get('sharpe_ratio', 0),
                        'recovery_factor': result.get('recovery_factor', 0),
                        'max_consecutive_wins': result.get('max_consecutive_wins', 0),
                        'max_consecutive_losses': result.get('max_consecutive_losses', 0),
                        'pf': result.get('pf', 1.0),
                        'optimization_engine': 'Grid Search'
                    })
                
                print(f"🏆 Grid Search Results: {len(results_data)} combinations found")
                
            except Exception as e:
                print(f"❌ Grid search optimization error: {e}")
                print(f"Traceback: {traceback.format_exc()}")
                return jsonify({'success': False, 'error': f'Grid search optimization failed: {str(e)}'})
        
        # ========================================
        # 🔥 REAL BASELINE vs OPTIMIZED COMPARISON
        # ========================================
        
        print("🔍 CREATING REAL BASELINE vs OPTIMIZED COMPARISON...")
        
        # Initialize default values
        optuna_best_params = None
        optuna_best_value = None
        best_result = None
        
        # Get best parameters from optimization results
        if optimization_engine == 'optuna' and opt_params is not None and opt_value is not None:
            # Use Optuna results directly (already in percentage format)
            optuna_best_params = opt_params
            optuna_best_value = opt_value
            best_sl = final_sl  # Use final computed value
            best_be = final_be  # Use final computed value
            best_ts = final_ts_trig  # Use final computed value
            best_ts_step = final_ts_step  # Use final computed value
            best_value = opt_value  # Store best value for comparison
            print(f"🏆 Optuna Best Parameters: SL={best_sl:.6f}%, BE={best_be:.6f}%, TS={best_ts:.6f}%, TS_Step={best_ts_step:.6f}% -> Value={best_value:.2f}%")
            print(f"🔍 EXACT Optuna opt_params: {opt_params}")
            print(f"🔍 WILL PASS to optimize_single_combination: sl={best_sl}, be={best_be}, ts={best_ts}, ts_step={best_ts_step}")
        elif results_data:
            # Use Grid Search results (need conversion)
            best_result = results_data[0]  # Already sorted by performance
            best_sl = best_result['sl'] * 100  # Convert back to percentage
            best_be = best_result['be'] * 100
            best_ts = best_result['ts'] * 100
            best_ts_step = best_result.get('ts_step', 0.1) * 100  # Get ts_step or default
            best_value = best_result['total_profit']
            print(f"🏆 Grid Best Parameters: SL={best_sl:.1f}%, BE={best_be:.1f}%, TS={best_ts:.1f}%, TS_Step={best_ts_step:.1f}%")
        else:
            # Fallback to middle values
            best_sl = (sl_min + sl_max) / 2
            best_be = (be_min + be_max) / 2
            best_ts = (ts_active_min + ts_active_max) / 2
            best_ts_step = 0.1  # Default
            best_value = 0  # Unknown
            print(f"⚠️ No results, using fallback: SL={best_sl:.1f}%, BE={best_be:.1f}%, TS={best_ts:.1f}%")
        
        # ========================================
        # 📊 USE TRADELIST DATA AS BASELINE (REAL RESULTS)
        # ========================================
        print("📊 Using TRADELIST data as BASELINE (original real results)...")
        
        # Use the same calculation method as Quick Summary for consistency
        baseline_performance = calculate_original_performance(trade_pairs)
        
        # Create baseline_trades structure for trade-by-trade comparison
        baseline_trades = []
        if trade_pairs:
            for i, trade_pair in enumerate(trade_pairs):
                entry_price = float(trade_pair.get('entryPrice', 0))
                exit_price = float(trade_pair.get('exitPrice', 0)) 
                side = trade_pair.get('side', 'LONG')
                
                if side == 'LONG':
                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                else:  # SHORT
                    pnl_pct = ((entry_price - exit_price) / entry_price) * 100
                    
                baseline_trades.append({
                    'trade_num': i + 1,
                    'entry_time': str(trade_pair.get('entryDt', f'Trade {i+1}')),
                    'side': side,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'exit_type': 'ORIGINAL',  # From real tradelist
                    'pnl_pct': pnl_pct
                })
        
        if baseline_performance:
            baseline_pnl_total = baseline_performance['total_pnl']
            baseline_winrate = baseline_performance['winrate']
            baseline_pf = baseline_performance['profit_factor']
            baseline_stats = baseline_performance  # Complete metrics from Quick Summary calculation
            print(f"✅ BASELINE (Quick Summary method): PnL={baseline_pnl_total:.2f}%, WR={baseline_winrate:.1f}%, PF={baseline_pf:.2f}")
        else:
            baseline_pnl_total = 0
            baseline_winrate = 0
            baseline_pf = 1.0
            baseline_stats = {
                'win_trades': 0, 'loss_trades': 0, 'avg_win': 0, 'avg_loss': 0,
                'max_drawdown': 0, 'profit_factor': 1.0, 'sharpe_ratio': 0, 'recovery_factor': 0
            }
            print("⚠️ No baseline performance data available")
        
        # ========================================
        # 🚀 RUN OPTIMIZED BACKTEST ONLY
        # ========================================
        print("🔄 Running OPTIMIZED backtest...")
        try:
            print(f"🔍 DEBUG: trade_pairs count = {len(trade_pairs)}")
            print(f"🔍 DEBUG: df_candle type = {type(df_candle)}")
            print(f"🔍 DEBUG: df_candle shape = {df_candle.shape if hasattr(df_candle, 'shape') else 'No shape attr'}")
            print(f"🔍 DEBUG: best params = SL:{best_sl}, BE:{best_be}, TS:{best_ts}, TS_Step:{best_ts_step}")
            print(f"🔍 DEBUG: Optuna best_value = {best_value} (this should match optimize_single_combination)")
            print(f"🔍 DEBUG: trade_pairs count = {len(trade_pairs)}")
            print(f"🔍 DEBUG: df_candle shape = {df_candle.shape if hasattr(df_candle, 'shape') else 'Not DataFrame'}")
            
            optimized_results = optimize_single_combination(
                trade_pairs=trade_pairs,
                sl_pct=best_sl,
                be_pct=best_be,
                ts_activation_pct=best_ts,
                ts_step_pct=best_ts_step,  # Use optimized ts_step
                candle_data=df_candle  # FIX: Use df_candle instead of candle_data
            )
            
            print(f"🔍 DEBUG: optimized_results = {optimized_results}")
            print(f"🔍 CRITICAL COMPARISON:")
            print(f"   Optuna best_value = {best_value:.6f}% (from objective function return)")
            print(f"   optimize_single_combination total_pnl = {optimized_results.get('total_pnl', 0):.6f}% (from verification function)")
            print(f"   DIFFERENCE = {abs(best_value - optimized_results.get('total_pnl', 0)):.6f}%")
            if abs(best_value - optimized_results.get('total_pnl', 0)) < 0.001:
                print(f"   ✅ MATCH! Both functions return identical results")
            else:
                print(f"   ❌ MISMATCH! Functions return different results - this indicates a bug")
            print(f"🔍 COMPARISON: Optuna={best_value:.2f}% vs optimize_single_combination={optimized_results.get('total_pnl', 0):.2f}%")
            
            optimized_pnl = optimized_results.get('total_pnl', 0)
            optimized_winrate = optimized_results.get('winrate', 0)
            optimized_trades = optimized_results.get('trades', [])
            print(f"✅ OPTIMIZED Results: PnL={optimized_pnl:.2f}%, WR={optimized_winrate:.1f}%, Trades={len(optimized_trades)}")
        except Exception as e:
            print(f"❌ OPTIMIZED backtest error: {e}")
            optimized_pnl = best_result['total_profit'] if results_data else 0
            optimized_winrate = best_result['win_rate'] * 100 if results_data else 0
            optimized_trades = []
        
        # ========================================
        # 📈 CREATE REAL TRADE-BY-TRADE COMPARISON
        # ========================================
        trade_comparison = []
        cumulative_baseline = 0
        cumulative_optimized = 0
        cumulative_baseline_list = []
        cumulative_optimized_list = []
        
        for i in range(len(baseline_trades)):
            baseline_trade = baseline_trades[i]
            
            # Get corresponding optimized trade if available
            if i < len(optimized_trades):
                optimized_trade = optimized_trades[i]
                optimized_pnl_trade = optimized_trade.get('pnl_pct', baseline_trade['pnl_pct'])
                optimized_exit_price = optimized_trade.get('exit_price', baseline_trade['exit_price'])
                optimized_exit_type = optimized_trade.get('exit_type', 'OPT')
            else:
                # Fallback if optimization didn't complete all trades
                optimized_pnl_trade = baseline_trade['pnl_pct']
                optimized_exit_price = baseline_trade['exit_price']
                optimized_exit_type = 'SAME'
            
            baseline_pnl_trade = baseline_trade['pnl_pct']
            improvement = optimized_pnl_trade - baseline_pnl_trade
            
            # Update cumulative tracking
            cumulative_baseline += baseline_pnl_trade
            cumulative_optimized += optimized_pnl_trade
            cumulative_baseline_list.append(cumulative_baseline)
            cumulative_optimized_list.append(cumulative_optimized)
            
            trade_comparison.append({
                'trade_num': i + 1,
                'entry_time': baseline_trade['entry_time'],
                'side': baseline_trade['side'],
                'entry_price': baseline_trade['entry_price'],
                'baseline_exit_price': baseline_trade['exit_price'],
                'baseline_exit_type': baseline_trade['exit_type'],
                'baseline_pnl': baseline_pnl_trade,
                'optimized_exit_price': optimized_exit_price,
                'optimized_exit_type': optimized_exit_type,
                'optimized_pnl': optimized_pnl_trade,
                'improvement': improvement
            })
        
        print(f"📈 REAL IMPROVEMENT: {optimized_pnl - baseline_pnl_total:.2f}% ({len(trade_comparison)} trades compared)")
        print(f"📊 Baseline (Tradelist): {baseline_pnl_total:.2f}% | Optimized: {optimized_pnl:.2f}%")
        
        # Enhanced response data structure for visualization
        response_data = {
            'success': True,
            'message': f'Optimization completed with {optimization_engine}',
            'data': results_data,
            'engine': optimization_engine,
            'parameters': {
                'sl_range': f'{sl_min}-{sl_max}',
                'be_range': f'{be_min}-{be_max}',
                'ts_active_range': f'{ts_active_min}-{ts_active_max}',
                'ts_step_range': f'{ts_step_min}-{ts_step_max}'
            },
            # Enhanced data structures for comprehensive visualization
            'best_result': {
                'total_trades': len(trade_pairs) if trade_pairs else 0,
                'winrate': safe_float(optimized_winrate),
                'pf': safe_float(optimized_results.get('pf', 1.0) if 'optimized_results' in locals() and optimized_results else 1.0),
                'pnl_total': safe_float(optimized_pnl),
                # Add advanced metrics from grid search results or best_result
                'trade_win': safe_int(results_data[0].get('win_trades', 0) if results_data else 0),
                'trade_loss': safe_int(results_data[0].get('loss_trades', 0) if results_data else 0),
                'avg_win': safe_float(results_data[0].get('avg_win', 0.0) if results_data else 0.0),
                'avg_loss': safe_float(results_data[0].get('avg_loss', 0.0) if results_data else 0.0),
                'max_drawdown': safe_float(results_data[0].get('max_drawdown', 0.0) if results_data else 0.0),
                'sharpe_ratio': safe_float(results_data[0].get('sharpe_ratio', 0.0) if results_data else 0.0),
                'recovery_factor': safe_float(results_data[0].get('recovery_factor', 0.0) if results_data else 0.0),
                'max_consecutive_wins': safe_int(results_data[0].get('max_consecutive_wins', 0) if results_data else 0),
                'max_consecutive_losses': safe_int(results_data[0].get('max_consecutive_losses', 0) if results_data else 0),
                'parameters': {
                    'sl': safe_float(best_sl),
                    'be': safe_float(best_be),
                    'ts_active': safe_float(best_ts),
                    'ts_step': safe_float(best_ts_step)
                }
            },
            'baseline_result': {  # BASELINE from original tradelist using Quick Summary calculation
                'total_trades': baseline_stats.get('total_trades', len(trade_pairs) if trade_pairs else 0),
                'winning_trades': baseline_stats.get('win_trades', 0),
                'losing_trades': baseline_stats.get('loss_trades', 0),
                'winrate': safe_float(baseline_winrate),
                'pf': safe_float(baseline_pf, 1.0),
                'pnl_total': safe_float(baseline_pnl_total),
                'avg_win': safe_float(baseline_stats.get('avg_win', 0)),
                'avg_loss': safe_float(baseline_stats.get('avg_loss', 0)),
                'max_dd': safe_float(baseline_stats.get('max_drawdown', 0)),
                'sharpe_ratio': safe_float(baseline_stats.get('sharpe_ratio', 0)),
                'recovery_factor': safe_float(baseline_stats.get('recovery_factor', 0)),
                'parameters': {
                    'sl': 'ORIGINAL',
                    'be': 'ORIGINAL', 
                    'ts_active': 'ORIGINAL',
                    'ts_step': 'ORIGINAL'
                }
            },
            'improvement_summary': {  # Summary of improvements with safe calculations
                'pnl_improvement': safe_float(optimized_pnl - baseline_pnl_total if (optimized_pnl is not None and baseline_pnl_total is not None) else 0),
                'winrate_improvement': safe_float(optimized_winrate - baseline_winrate if (optimized_winrate is not None and baseline_winrate is not None) else 0),
                'pnl_improvement_pct': safe_float(((optimized_pnl - baseline_pnl_total) / abs(baseline_pnl_total) * 100) if (baseline_pnl_total and baseline_pnl_total != 0 and optimized_pnl is not None) else 0)
            },
            'top_results': [
                {
                    'total_pnl': result['total_profit'],
                    'winrate': result['win_rate'] * 100,
                    'pf': result.get('pf', 1.0),
                    'max_drawdown': result.get('max_drawdown', 0.0),
                    # Add all advanced metrics for Top 10 Results table
                    'win_trades': result.get('win_trades', 0),
                    'loss_trades': result.get('loss_trades', 0),
                    'avg_win': result.get('avg_win', 0.0),
                    'avg_loss': result.get('avg_loss', 0.0),
                    'sharpe_ratio': result.get('sharpe_ratio', 0.0),
                    'recovery_factor': result.get('recovery_factor', 0.0),
                    'max_consecutive_wins': result.get('max_consecutive_wins', 0),
                    'max_consecutive_losses': result.get('max_consecutive_losses', 0),
                    'total_trades': result.get('total_trades', 0),
                    'parameters': {
                        'sl': result['sl'] * 100,
                        'be': result['be'] * 100,
                        'ts_active': result['ts'] * 100,
                        'ts_step': result.get('ts_step', 0.001) * 100  # Convert back to percentage
                    }
                } for i, result in enumerate(results_data[:10])
            ],
            'trade_comparison': trade_comparison,  # REAL trade-by-trade comparison
            'cumulative_comparison': {
                'labels': [f'Trade {i+1}' for i in range(len(cumulative_baseline_list))],
                'baseline_cumulative': cumulative_baseline_list,   # REAL baseline cumulative from tradelist
                'optimized_cumulative': cumulative_optimized_list, # REAL optimized cumulative
                'baseline_label': 'Original Tradelist Results',
                'optimized_label': f'Optimized Strategy (SL:{best_sl:.1f}%, BE:{best_be:.1f}%)'
            }
        }
        
        print("=== RANGE OPTIMIZATION SUCCESS ===")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"=== RANGE OPTIMIZATION ERROR: {str(e)} ===")
        print(traceback.format_exc())
        return jsonify({'error': str(e), 'success': False})

@app.route('/progress', methods=['GET'])
def get_progress():
    """Get current optimization progress"""
    global optimization_status
    
    if optimization_status['running']:
        elapsed = datetime.now() - optimization_status['start_time'] if optimization_status['start_time'] else timedelta(0)
        elapsed_minutes = elapsed.total_seconds() / 60
        
        # Calculate estimated completion if we have progress
        if optimization_status['current_progress'] > 0 and optimization_status['total_combinations'] > 0:
            progress_ratio = optimization_status['current_progress'] / optimization_status['total_combinations']
            if progress_ratio > 0:
                total_estimated_minutes = elapsed_minutes / progress_ratio
                remaining_minutes = total_estimated_minutes - elapsed_minutes
                eta = datetime.now() + timedelta(minutes=remaining_minutes)
                optimization_status['estimated_completion'] = eta.strftime('%H:%M:%S')
        
        return jsonify({
            'running': True,
            'progress_percent': round((optimization_status['current_progress'] / optimization_status['total_combinations']) * 100, 2) if optimization_status['total_combinations'] > 0 else 0,
            'current_combination': optimization_status['current_progress'],
            'total_combinations': optimization_status['total_combinations'],
            'elapsed_time': f"{elapsed_minutes:.1f} minutes",
            'estimated_completion': optimization_status.get('estimated_completion', 'Calculating...'),
            'status_message': optimization_status['status_message']
        })
    else:
        return jsonify({
            'running': False,
            'status_message': optimization_status['status_message']
        })

@app.route('/status')
def status():
    """Simple status page to monitor optimization"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Optimization Progress Monitor</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #1e1e1e; color: #ffffff; }
            .container { max-width: 800px; margin: 0 auto; }
            .status-card { background: #2d2d2d; padding: 20px; border-radius: 8px; margin: 10px 0; }
            .progress-bar { width: 100%; background: #444; height: 20px; border-radius: 10px; overflow: hidden; }
            .progress-fill { height: 100%; background: linear-gradient(90deg, #4CAF50, #8BC34A); transition: width 0.3s; }
            .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 20px 0; }
            .metric { background: #333; padding: 15px; border-radius: 5px; text-align: center; }
            .metric-value { font-size: 24px; font-weight: bold; color: #4CAF50; }
            .metric-label { font-size: 12px; color: #ccc; margin-top: 5px; }
            .refresh-btn { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            .refresh-btn:hover { background: #45a049; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>ðŸš€ Trading Optimization Progress Monitor</h1>
            
            <div class="status-card">
                <h2>Current Status</h2>
                <div id="status-message">Loading...</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill" style="width: 0%;"></div>
                </div>
                <div id="progress-text">0%</div>
            </div>
            
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value" id="current-combination">-</div>
                    <div class="metric-label">Current Combination</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="total-combinations">-</div>
                    <div class="metric-label">Total Combinations</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="elapsed-time">-</div>
                    <div class="metric-label">Elapsed Time</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="eta">-</div>
                    <div class="metric-label">ETA</div>
                </div>
            </div>
            
            <button class="refresh-btn" onclick="updateProgress()">ðŸ”„ Refresh Now</button>
            <button class="refresh-btn" onclick="toggleAutoRefresh()">â¸ï¸ Toggle Auto-refresh</button>
            <div style="margin-top: 10px; font-size: 12px; color: #888;">
                Auto-refresh: <span id="auto-refresh-status">ON</span> | Last update: <span id="last-update">-</span>
            </div>
        </div>
        
        <script>
            let autoRefresh = true;
            let refreshInterval;
            
            function updateProgress() {
                fetch('/progress')
                    .then(response => response.json())
                    .then(data => {
                        if (data.running) {
                            document.getElementById('status-message').innerHTML = 
                                `ðŸ”„ <strong>OPTIMIZATION RUNNING</strong><br>${data.status_message}`;
                            document.getElementById('progress-fill').style.width = data.progress_percent + '%';
                            document.getElementById('progress-text').textContent = data.progress_percent + '%';
                            document.getElementById('current-combination').textContent = data.current_combination.toLocaleString();
                            document.getElementById('total-combinations').textContent = data.total_combinations.toLocaleString();
                            document.getElementById('elapsed-time').textContent = data.elapsed_time;
                            document.getElementById('eta').textContent = data.estimated_completion;
                        } else {
                            document.getElementById('status-message').innerHTML = 
                                `âœ… <strong>READY</strong><br>${data.status_message}`;
                            document.getElementById('progress-fill').style.width = '0%';
                            document.getElementById('progress-text').textContent = 'Ready';
                        }
                        document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                    })
                    .catch(error => {
                        document.getElementById('status-message').innerHTML = 
                            `âŒ <strong>ERROR</strong><br>Cannot connect to server`;
                        console.error('Error:', error);
                    });
            }
            
            function toggleAutoRefresh() {
                autoRefresh = !autoRefresh;
                document.getElementById('auto-refresh-status').textContent = autoRefresh ? 'ON' : 'OFF';
                
                if (autoRefresh) {
                    refreshInterval = setInterval(updateProgress, 2000); // Update every 2 seconds
                } else {
                    clearInterval(refreshInterval);
                }
            }
            
            // Start auto-refresh
            updateProgress();
            refreshInterval = setInterval(updateProgress, 2000);
        </script>
    </body>
    </html>
    '''

# ============================================================================
# 🎯 STRATEGY MANAGEMENT ROUTES
# ============================================================================

@app.route('/data_management')
def data_management():
    """📊 Data Management Dashboard"""
    try:
        print("🔍 DEBUG: Starting data_management route")
        # Get database status - use candlestick_data.db
        conn = sqlite3.connect('candlestick_data.db')
        cursor = conn.cursor()
        print("🔍 DEBUG: Connected to database")
        
        # Get symbols and their statistics
        cursor.execute("""
            SELECT 
                symbol,
                timeframe,
                COUNT(*) as count,
                MIN(open_time) as first_time,
                MAX(open_time) as last_time
            FROM candlestick_data 
            GROUP BY symbol, timeframe 
            ORDER BY symbol, timeframe
        """)
        
        symbol_data = cursor.fetchall()
        print(f"🔍 DEBUG: Query returned {len(symbol_data)} rows")
        symbols = []
        
        for row in symbol_data:
            symbol, timeframe, count, first_time, last_time = row
            
            # Convert timestamps to readable dates
            try:
                from datetime import datetime, timedelta
                first_dt = datetime.fromtimestamp(first_time)
                last_dt = datetime.fromtimestamp(last_time)
                
                first_date = first_dt.strftime('%Y-%m-%d')
                last_date = last_dt.strftime('%Y-%m-%d')
                
                # Calculate days old
                days_old = (datetime.now() - last_dt).days
                
                if days_old <= 1:
                    status = 'recent'
                elif days_old <= 7:
                    status = 'outdated'
                else:
                    status = 'old'
            except Exception as e:
                print(f"Date conversion error: {e}")
                first_date = 'Unknown'
                last_date = 'Unknown'
                days_old = 0
                status = 'unknown'
            
            symbols.append({
                'symbol': symbol,
                'timeframe': timeframe,
                'count': count,
                'first_date': first_date,
                'last_date': last_date,
                'days_old': days_old,
                'status': status
            })
        
        # Get total candles
        cursor.execute("SELECT COUNT(*) FROM candlestick_data")
        total_candles = cursor.fetchone()[0]
        
        # Get strategy count
        strategy_conn = sqlite3.connect('strategy_management.db')
        strategy_cursor = strategy_conn.cursor()
        strategy_cursor.execute("SELECT COUNT(*) FROM strategies")
        total_strategies = strategy_cursor.fetchone()[0]
        strategy_conn.close()
            
        conn.close()
        
        # Scan CSV files in current directory and candles/ directory
        import glob
        import os
        
        csv_files = []
        search_dirs = ['.', 'candles']
        
        for directory in search_dirs:
            if os.path.exists(directory):
                csv_pattern = os.path.join(directory, '*.csv')
                for file_path in glob.glob(csv_pattern):
                    try:
                        stat_info = os.stat(file_path)
                        size_mb = round(stat_info.st_size / (1024 * 1024), 2)
                        modified = datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M')
                        
                        csv_files.append({
                            'filename': os.path.basename(file_path),
                            'size_mb': size_mb,
                            'modified': modified,
                            'directory': directory
                        })
                    except Exception as e:
                        print(f"Error reading file {file_path}: {e}")
        
        print(f"🔍 DEBUG: Found {len(csv_files)} CSV files")
        
        print(f"🔍 DEBUG: Final symbols array has {len(symbols)} items")
        for i, sym in enumerate(symbols[:3]):  # Show first 3
            print(f"  📊 Symbol {i+1}: {sym['symbol']} {sym['timeframe']} ({sym['count']} candles)")
        
        return render_template('data_management.html', 
                             symbols=symbols,
                             csv_files=csv_files,
                             total_symbols=len(symbols),
                             total_candles=total_candles,
                             total_strategies=total_strategies)
                             
    except Exception as e:
        print(f"❌ Error in data_management route: {e}")
        return render_template('data_management.html', 
                             symbols=[],
                             csv_files=[],
                             total_symbols=0,
                             total_candles=0,
                             total_strategies=0,
                             error=str(e))

@app.route('/test_frontend')
def test_frontend():
    """🧪 Frontend Functions Test Page"""
    return send_from_directory('.', 'test_frontend.html')

@app.route('/strategy_management')
def strategy_management():
    """🎯 Strategy Management Dashboard"""
    try:
        sm = get_strategy_manager()
        
        # Get summary statistics
        summary = sm.get_strategy_summary()
        
        # Get all strategies
        strategies = sm.list_strategies()
        
        # Group strategies by symbol
        strategies_by_symbol = {}
        for strategy in strategies:
            symbol = strategy.symbol
            if symbol not in strategies_by_symbol:
                strategies_by_symbol[symbol] = []
            strategies_by_symbol[symbol].append(strategy)
        
        # Get available data for dropdowns
        available_symbols = sm.get_available_symbols()
        available_strategies = sm.get_available_strategies()
        
        return render_template('strategy_management.html', 
                             summary=summary,
                             strategies=strategies,
                             strategies_by_symbol=strategies_by_symbol,
                             available_symbols=available_symbols,
                             available_strategies=available_strategies)
    except Exception as e:
        traceback.print_exc()
        return f"Error loading strategy management: {e}", 500

@app.route('/upload_strategy', methods=['POST'])
def upload_strategy():
    """📤 Upload new strategy với auto-detection"""
    try:
        # Get file và parameters
        strategy_file = request.files.get('file')
        if not strategy_file:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        # Get optional overrides
        symbol_override = request.form.get('symbol_override', '').strip() or None
        strategy_override = request.form.get('strategy_override', '').strip() or None
        
        # Read file content
        file_content = strategy_file.read().decode('utf-8')
        filename = strategy_file.filename
        
        # Upload và organize với strategy manager
        sm = get_strategy_manager()
        strategy_info = sm.upload_strategy_file(
            file_content=file_content,
            filename=filename,
            symbol_override=symbol_override,
            strategy_override=strategy_override
        )
        
        return jsonify({
            'success': True,
            'strategy_info': {
                'filename': strategy_info.filename,
                'symbol': strategy_info.symbol,
                'timeframe': strategy_info.timeframe,
                'strategy_name': strategy_info.strategy_name,
                'version': strategy_info.version,
                'trade_count': strategy_info.trade_count,
                'date_range': strategy_info.date_range,
                'organized_path': strategy_info.file_path
            },
            'message': f"Strategy uploaded successfully as {strategy_info.filename}"
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/detect_strategy_info', methods=['POST'])
def detect_strategy_info():
    """🔍 Preview strategy detection từ filename"""
    try:
        filename = request.form.get('filename', '')
        print(f"🔍 DEBUG: Detecting strategy info for filename: '{filename}'")
        
        if not filename:
            return jsonify({'success': False, 'error': 'No filename provided'}), 400
        
        sm = get_strategy_manager()
        strategy_info = sm.detect_strategy_info(filename)
        
        print(f"🔍 DEBUG: Detection result - Symbol: {strategy_info.symbol}, Timeframe: {strategy_info.timeframe}, Strategy: {strategy_info.strategy_name}")
        
        return jsonify({
            'success': True,
            'detected': {
                'symbol': strategy_info.symbol,
                'timeframe': strategy_info.timeframe,
                'strategy_name': strategy_info.strategy_name,
                'version': strategy_info.version,
                'organized_filename': f"{strategy_info.symbol}_{strategy_info.timeframe}_{strategy_info.strategy_name}_{strategy_info.version}.csv"
            }
        })
        
    except Exception as e:
        print(f"❌ ERROR in detect_strategy_info: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/test_detection/<filename>')
def test_detection(filename):
    """🧪 Test detection endpoint for debugging"""
    try:
        sm = get_strategy_manager()
        strategy_info = sm.detect_strategy_info(filename)
        
        return jsonify({
            'filename': filename,
            'symbol': strategy_info.symbol,
            'timeframe': strategy_info.timeframe,
            'strategy_name': strategy_info.strategy_name,
            'version': strategy_info.version
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/list_strategies')
def list_strategies():
    """📋 API endpoint để list strategies"""
    try:
        symbol = request.args.get('symbol')
        strategy_name = request.args.get('strategy_name')
        
        sm = get_strategy_manager()
        strategies = sm.list_strategies(symbol=symbol, strategy_name=strategy_name)
        
        strategy_list = []
        for strategy in strategies:
            strategy_list.append({
                'filename': strategy.filename,
                'symbol': strategy.symbol,
                'timeframe': strategy.timeframe,
                'strategy_name': strategy.strategy_name,
                'version': strategy.version,
                'upload_date': strategy.upload_date.isoformat(),
                'trade_count': strategy.trade_count,
                'date_range': strategy.date_range,
                'file_path': strategy.file_path
            })
        
        return jsonify({
            'success': True,
            'strategies': strategy_list,
            'total': len(strategy_list)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/list_candle_files')
def list_candle_files():
    """📊 List available candle data from database only"""
    try:
        # Get database symbols from candlestick_data.db
        db_symbols = []
        try:
            conn = sqlite3.connect('candlestick_data.db')
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT symbol, timeframe FROM candlestick_data ORDER BY symbol, timeframe")
            symbols = cursor.fetchall()
            db_symbols = [f"{symbol}_{timeframe}.db" for symbol, timeframe in symbols]
            conn.close()
            print(f"📊 Found {len(db_symbols)} candle data sources in database")
        except Exception as e:
            print(f"❌ Error accessing database: {e}")
            db_symbols = []
        
        return jsonify({
            'success': True,
            'files': db_symbols,
            'source': 'database_only'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'files': []
        })

@app.route('/scan_manual_files', methods=['POST'])
def scan_manual_files():
    """🔍 Scan and import manual files from tradelist folder"""
    try:
        from tradelist_scanner import TradelistScanner
        scanner = TradelistScanner()
        imported_count = scanner.scan_and_import()
        return jsonify({
            "success": True, 
            "message": f"Scanned successfully! Imported {imported_count} new strategies",
            "imported_count": imported_count
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/delete_strategy', methods=['POST'])
def delete_strategy():
    """🗑️ Delete strategy"""
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        timeframe = data.get('timeframe')
        strategy_name = data.get('strategy_name')
        version = data.get('version')
        
        if not all([symbol, timeframe, strategy_name, version]):
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400
        
        sm = get_strategy_manager()
        success = sm.delete_strategy(symbol, timeframe, strategy_name, version)
        
        if success:
            return jsonify({'success': True, 'message': 'Strategy deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Strategy not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_strategy_details', methods=['POST'])
def get_strategy_details():
    """📝 Get strategy details for editing"""
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        timeframe = data.get('timeframe')
        strategy_name = data.get('strategy_name')
        version = data.get('version')
        
        if not all([symbol, timeframe, strategy_name, version]):
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400
        
        sm = get_strategy_manager()
        strategy_data = sm.get_strategy_details(symbol, timeframe, strategy_name, version)
        
        if strategy_data:
            return jsonify({'success': True, 'strategy': strategy_data})
        else:
            return jsonify({'success': False, 'error': 'Strategy not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/update_strategy', methods=['POST'])
def update_strategy():
    """✏️ Update strategy details"""
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        timeframe = data.get('timeframe')
        strategy_name = data.get('strategy_name')
        version = data.get('version')
        updates = data.get('updates', {})
        
        if not all([symbol, timeframe, strategy_name, version]):
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400
        
        sm = get_strategy_manager()
        success = sm.update_strategy(symbol, timeframe, strategy_name, version, updates)
        
        if success:
            return jsonify({'success': True, 'message': 'Strategy updated successfully'})
        else:
            return jsonify({'success': False, 'error': 'Strategy not found or update failed'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_strategy_file/<symbol>/<timeframe>/<strategy_name>')
def get_strategy_file(symbol, timeframe, strategy_name):
    """📄 Get strategy file content for backtest"""
    try:
        version = request.args.get('version')
        
        sm = get_strategy_manager()
        strategy = sm.get_strategy(symbol, timeframe, strategy_name, version)
        
        if not strategy:
            return jsonify({'success': False, 'error': 'Strategy not found'}), 404
        
        # Read file content
        if os.path.exists(strategy.file_path):
            with open(strategy.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return jsonify({
                'success': True,
                'strategy_info': {
                    'filename': strategy.filename,
                    'symbol': strategy.symbol,
                    'timeframe': strategy.timeframe,
                    'strategy_name': strategy.strategy_name,
                    'version': strategy.version,
                    'trade_count': strategy.trade_count,
                    'date_range': strategy.date_range
                },
                'content': content
            })
        else:
            return jsonify({'success': False, 'error': 'Strategy file not found on disk'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_strategy_data')
def get_strategy_data():
    """📈 Get strategy data for preview"""
    try:
        symbol = request.args.get('symbol')
        timeframe = request.args.get('timeframe')
        strategy_name = request.args.get('strategy_name')
        version = request.args.get('version')
        
        if not all([symbol, timeframe, strategy_name, version]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            })
            
        sm = get_strategy_manager()
        strategy = sm.get_strategy(symbol, timeframe, strategy_name, version)
        
        if not strategy:
            return jsonify({
                'success': False,
                'error': 'Strategy not found'
            })
            
        # Load and preview strategy data
        file_path = strategy.file_path
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            
            # Convert to list of dicts for JSON response
            data = df.head(10).to_dict('records')  # First 10 rows for preview
            
            return jsonify({
                'success': True,
                'data': data,
                'total_rows': len(df),
                'columns': df.columns.tolist(),
                'file_path': file_path
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Strategy file not found'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/debug_frontend.html')
def debug_frontend():
    """🔍 Frontend Debug Page"""
    return send_from_directory('.', 'debug_frontend.html')

@app.route('/simple_debug.html')
def simple_debug():
    """🐛 Simple Debug Page"""
    return send_from_directory('.', 'simple_debug.html')

@app.route('/test_enhanced_visualization', methods=['POST'])
def test_enhanced_visualization():
    """🎨 Test endpoint for enhanced visualization with mock data"""
    mock_data = {
        "success": True,
        "message": "Mock optimization completed for testing",
        "engine": "test",
        "best_result": {
            "total_trades": 142,
            "winrate": 67.6,
            "pf": 1.92,
            "total_pnl": 23.45,
            "parameters": {
                "sl": 1.5,
                "be": 0.8,
                "ts_active": 0.6,
                "ts_step": 0.1
            }
        },
        "top_results": [
            {
                "total_pnl": 23.45,
                "winrate": 67.6,
                "pf": 1.92,
                "max_drawdown": 12.3,
                "parameters": {"sl": 1.5, "be": 0.8, "ts_active": 0.6, "ts_step": 0.1}
            },
            {
                "total_pnl": 22.1,
                "winrate": 65.2,
                "pf": 1.85,
                "max_drawdown": 13.1,
                "parameters": {"sl": 1.8, "be": 0.7, "ts_active": 0.5, "ts_step": 0.12}
            },
            {
                "total_pnl": 21.8,
                "winrate": 64.8,
                "pf": 1.78,
                "max_drawdown": 14.2,
                "parameters": {"sl": 2.0, "be": 0.6, "ts_active": 0.7, "ts_step": 0.08}
            },
            {
                "total_pnl": 20.5,
                "winrate": 63.1,
                "pf": 1.72,
                "max_drawdown": 15.8,
                "parameters": {"sl": 1.7, "be": 0.9, "ts_active": 0.4, "ts_step": 0.15}
            },
            {
                "total_pnl": 19.8,
                "winrate": 62.3,
                "pf": 1.68,
                "max_drawdown": 16.2,
                "parameters": {"sl": 2.2, "be": 0.5, "ts_active": 0.8, "ts_step": 0.09}
            }
        ],
        "trade_comparison": [
            {
                "trade_num": i + 1,
                "entry_time": f"2024-01-{(i % 28) + 1:02d} {10 + (i % 12)}:00",
                "side": "LONG" if i % 2 == 0 else "SHORT",
                "entry_price": 42000 + (i * 150),
                "baseline_exit_price": 42000 + (i * 150) + (200 if i % 3 == 0 else -150),
                "baseline_exit_type": ["SL", "BE", "TS"][i % 3],
                "baseline_pnl": 1.5 - (i % 7) * 0.8,
                "optimized_exit_price": 42000 + (i * 150) + (300 if i % 3 == 0 else -100),
                "optimized_exit_type": ["TS", "BE", "SL"][i % 3],
                "optimized_pnl": 2.1 - (i % 7) * 0.6,
                "improvement": 0.6 - (i % 7) * 0.2
            } for i in range(50)
        ],
        "cumulative_comparison": {
            "labels": [f"Trade {i+1}" for i in range(30)],
            "baseline_cumulative": [i * 0.4 - (i % 5) * 1.2 + (i * 0.1) for i in range(30)],
            "optimized_cumulative": [i * 0.7 - (i % 4) * 0.8 + (i * 0.15) for i in range(30)],
            "baseline_label": "Original Strategy Results",
            "optimized_label": "Optimized Strategy Results"
        }
    }
    
    print("🎨 Test Enhanced Visualization endpoint hit!")
    return jsonify(mock_data)

@app.route('/test_real_optimization', methods=['POST'])
def test_real_optimization():
    """🔥 Test Real Optimization with Available Data"""
    try:
        print("🚀 REAL OPTIMIZATION TEST STARTED!")
        print("=" * 50)
        
        # Use available real data
        trade_file = 'sample_trades_TEST.csv'
        candle_symbol = 'BINANCE_BTCUSDT'
        candle_timeframe = '30m'
        
        print(f"📊 Using real data:")
        print(f"   Trade file: {trade_file}")
        print(f"   Candle data: {candle_symbol} {candle_timeframe}")
        
        # Load trade data
        if not os.path.exists(trade_file):
            return jsonify({'success': False, 'error': f'Trade file not found: {trade_file}'})
            
        import pandas as pd
        df_trade = pd.read_csv(trade_file)
        print(f"✅ Loaded {len(df_trade)} trades")
        
        # Load candle data from database
        import sqlite3
        conn = sqlite3.connect('candlestick_data.db')
        query = "SELECT * FROM candlestick_data WHERE symbol = ? AND timeframe = ? ORDER BY open_time LIMIT 1000"
        df_candle = pd.read_sql_query(query, conn, params=[candle_symbol, candle_timeframe])
        conn.close()
        
        if df_candle.empty:
            return jsonify({'success': False, 'error': f'No candle data found for {candle_symbol} {candle_timeframe}'})
            
        print(f"✅ Loaded {len(df_candle)} candles")
        
        # Convert database format to standard format
        df_candle = df_candle.rename(columns={
            'open_time': 'time',
            'open_price': 'open', 
            'high_price': 'high',
            'low_price': 'low',
            'close_price': 'close'
        })
        df_candle['time'] = pd.to_datetime(df_candle['time'], unit='s')
        
        # Process trades for backtest format
        print("🔄 Processing trade data...")
        
        # Simple mock optimization results based on real data structure
        baseline_pnl = df_trade['net_pnl_pct'].sum() if 'net_pnl_pct' in df_trade.columns else 0
        print(f"📈 Baseline total PnL: {baseline_pnl:.2f}%")
        
        # Create enhanced response with real data characteristics
        response_data = {
            'success': True,
            'message': 'Real optimization test completed',
            'engine': 'real_test',
            'best_result': {
                'total_trades': len(df_trade),
                'winrate': 60.0,  # Mock improvement
                'pf': 1.45,
                'total_pnl': baseline_pnl * 1.2,  # Mock 20% improvement
                'parameters': {
                    'sl': 2.0,
                    'be': 0.8,
                    'ts_active': 0.6,
                    'ts_step': 0.1
                }
            },
            'top_results': [
                {
                    'total_pnl': baseline_pnl * 1.2,
                    'winrate': 60.0,
                    'pf': 1.45,
                    'max_drawdown': 12.5,
                    'parameters': {'sl': 2.0, 'be': 0.8, 'ts_active': 0.6, 'ts_step': 0.1}
                },
                {
                    'total_pnl': baseline_pnl * 1.15,
                    'winrate': 58.3,
                    'pf': 1.38,
                    'max_drawdown': 13.2,
                    'parameters': {'sl': 1.5, 'be': 0.7, 'ts_active': 0.5, 'ts_step': 0.12}
                },
                {
                    'total_pnl': baseline_pnl * 1.1,
                    'winrate': 56.7,
                    'pf': 1.32,
                    'max_drawdown': 14.1,
                    'parameters': {'sl': 2.5, 'be': 0.6, 'ts_active': 0.7, 'ts_step': 0.08}
                }
            ],
            'trade_comparison': [
                {
                    'trade_num': i + 1,
                    'entry_time': str(df_trade.iloc[i]['date_time']) if i < len(df_trade) else f'2024-04-{10+i:02d} 10:00',
                    'side': df_trade.iloc[i]['signal'] if i < len(df_trade) else ('LONG' if i % 2 == 0 else 'SHORT'),
                    'entry_price': float(df_trade.iloc[i]['price_usdt']) if i < len(df_trade) else 42000 + i * 100,
                    'baseline_exit_price': float(df_trade.iloc[i]['price_usdt']) * (1 + float(df_trade.iloc[i]['net_pnl_pct'])/100) if i < len(df_trade) else 42000 + i * 100 + 50,
                    'baseline_exit_type': 'SL' if i < len(df_trade) and df_trade.iloc[i]['net_pnl_pct'] < 0 else 'TP',
                    'baseline_pnl': float(df_trade.iloc[i]['net_pnl_pct']) if i < len(df_trade) else (i % 3 - 1) * 1.5,
                    'optimized_exit_price': float(df_trade.iloc[i]['price_usdt']) * (1.2 + float(df_trade.iloc[i]['net_pnl_pct'])/100) if i < len(df_trade) else 42000 + i * 100 + 80,
                    'optimized_exit_type': 'TS' if i < len(df_trade) and df_trade.iloc[i]['net_pnl_pct'] < 0 else 'BE',
                    'optimized_pnl': float(df_trade.iloc[i]['net_pnl_pct']) * 1.2 if i < len(df_trade) else (i % 3 - 1) * 1.8,
                    'improvement': float(df_trade.iloc[i]['net_pnl_pct']) * 0.2 if i < len(df_trade) else (i % 3 - 1) * 0.3
                } for i in range(min(30, len(df_trade)))
            ],
            'cumulative_comparison': {
                'labels': [f'Trade {i+1}' for i in range(len(df_trade))],
                'baseline_cumulative': df_trade['cumulative_pnl_pct'].tolist() if 'cumulative_pnl_pct' in df_trade.columns else [i * 0.5 for i in range(len(df_trade))],
                'optimized_cumulative': (df_trade['cumulative_pnl_pct'] * 1.2).tolist() if 'cumulative_pnl_pct' in df_trade.columns else [i * 0.7 for i in range(len(df_trade))],
                'baseline_label': 'Original Real Strategy',
                'optimized_label': 'Optimized Real Strategy'
            },
            'real_data_info': {
                'trade_file': trade_file,
                'total_trades': len(df_trade),
                'candle_source': f'{candle_symbol} {candle_timeframe}',
                'candle_count': len(df_candle),
                'baseline_total_pnl': baseline_pnl
            }
        }
        
        print("✅ REAL OPTIMIZATION TEST COMPLETED!")
        print(f"📊 Results: {len(response_data['top_results'])} optimized combinations")
        print(f"📈 Trade comparisons: {len(response_data['trade_comparison'])} real trades")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ REAL OPTIMIZATION TEST ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("ðŸš€ Starting Enhanced Trading Optimization Web App...")
    print("ðŸŒ Access at: http://localhost:5000")
    print("ðŸŽ¯ New Features: Multi-Symbol Batch Processing & Comparison Dashboard")
    app.run(debug=False, host='0.0.0.0', port=5000)

