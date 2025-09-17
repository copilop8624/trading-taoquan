#!/usr/bin/env python3
"""
📊 Data Management Dashboard
Web interface for managing CSV import and Binance data updates
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import os
import glob
from datetime import datetime, timedelta
import threading
import subprocess
import sys

# Import our modules
from csv_to_db import migrate_csv_to_db, show_database_status
from binance_fetcher import BinanceFetcher

app = Flask(__name__)

class DataManager:
    def __init__(self):
        self.fetcher = BinanceFetcher()
        self.update_status = {
            'running': False,
            'progress': 0,
            'current_symbol': '',
            'log': []
        }
    
    def get_database_stats(self):
        """Get database statistics"""
        try:
            conn = sqlite3.connect('candlestick_data.db')
            cursor = conn.cursor()
            
            # Get all symbols with stats
            cursor.execute("""
                SELECT symbol, timeframe, COUNT(*) as candle_count, 
                       MIN(open_time) as first_candle, 
                       MAX(open_time) as last_candle
                FROM candlestick_data 
                GROUP BY symbol, timeframe 
                ORDER BY symbol, timeframe
            """)
            
            results = cursor.fetchall()
            symbols = []
            
            for row in results:
                symbol, timeframe, count, first_time, last_time = row
                first_date = datetime.fromtimestamp(first_time).strftime('%Y-%m-%d %H:%M')
                last_date = datetime.fromtimestamp(last_time).strftime('%Y-%m-%d %H:%M')
                
                # Check if data is recent (within last 7 days)
                last_update = datetime.fromtimestamp(last_time)
                days_old = (datetime.now() - last_update).days
                status = 'recent' if days_old <= 7 else 'outdated' if days_old <= 30 else 'old'
                
                symbols.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'count': count,
                    'first_date': first_date,
                    'last_date': last_date,
                    'days_old': days_old,
                    'status': status
                })
            
            conn.close()
            return symbols
            
        except Exception as e:
            print(f"Error getting database stats: {e}")
            return []
    
    def get_csv_files(self):
        """Get list of CSV files in candles directory"""
        try:
            csv_files = []
            candles_dir = 'candles'
            
            if os.path.exists(candles_dir):
                for file_path in glob.glob(os.path.join(candles_dir, '*.csv')):
                    filename = os.path.basename(file_path)
                    file_size = os.path.getsize(file_path)
                    file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    csv_files.append({
                        'filename': filename,
                        'size_mb': round(file_size / (1024*1024), 2),
                        'modified': file_modified.strftime('%Y-%m-%d %H:%M')
                    })
            
            return csv_files
            
        except Exception as e:
            print(f"Error getting CSV files: {e}")
            return []

data_manager = DataManager()

@app.route('/')
def dashboard():
    """Main data management dashboard"""
    symbols = data_manager.get_database_stats()
    csv_files = data_manager.get_csv_files()
    
    return render_template('data_management.html', 
                         symbols=symbols, 
                         csv_files=csv_files,
                         update_status=data_manager.update_status)

@app.route('/api/database/stats')
def api_database_stats():
    """API endpoint for database statistics"""
    symbols = data_manager.get_database_stats()
    return jsonify({'symbols': symbols})

@app.route('/api/csv/migrate', methods=['POST'])
def api_csv_migrate():
    """API endpoint to migrate CSV files to database"""
    try:
        # Run migration in background
        def run_migration():
            data_manager.update_status['running'] = True
            data_manager.update_status['current_symbol'] = 'Migrating CSV files...'
            data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting CSV migration")
            
            try:
                migrate_csv_to_db()
                data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] CSV migration completed successfully")
            except Exception as e:
                data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Migration error: {e}")
            finally:
                data_manager.update_status['running'] = False
                data_manager.update_status['current_symbol'] = ''
        
        thread = threading.Thread(target=run_migration)
        thread.start()
        
        return jsonify({'success': True, 'message': 'CSV migration started'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/binance/update', methods=['POST'])
def api_binance_update():
    """API endpoint to update data from Binance"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', 'all')
        timeframe = data.get('timeframe', '')
        
        def run_update():
            data_manager.update_status['running'] = True
            data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting Binance update")
            
            try:
                if symbol == 'all':
                    data_manager.fetcher.update_all_symbols()
                else:
                    data_manager.update_status['current_symbol'] = f"{symbol} {timeframe}"
                    data_manager.fetcher.update_symbol(symbol, timeframe)
                
                data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Binance update completed")
            except Exception as e:
                data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Update error: {e}")
            finally:
                data_manager.update_status['running'] = False
                data_manager.update_status['current_symbol'] = ''
        
        thread = threading.Thread(target=run_update)
        thread.start()
        
        return jsonify({'success': True, 'message': 'Binance update started'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/binance/add', methods=['POST'])
def api_binance_add():
    """API endpoint to add new symbol from Binance"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper()
        timeframe = data.get('timeframe', '30m')
        days = int(data.get('days', 365))
        
        # Add BINANCE_ prefix if not present
        if not symbol.startswith('BINANCE_'):
            symbol = f"BINANCE_{symbol}"
        
        def run_add():
            data_manager.update_status['running'] = True
            data_manager.update_status['current_symbol'] = f"Adding {symbol} {timeframe}"
            data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Adding new symbol {symbol} {timeframe}")
            
            try:
                success = data_manager.fetcher.add_new_symbol(symbol, timeframe, days)
                if success:
                    data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully added {symbol} {timeframe}")
                else:
                    data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to add {symbol} {timeframe}")
            except Exception as e:
                data_manager.update_status['log'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Add symbol error: {e}")
            finally:
                data_manager.update_status['running'] = False
                data_manager.update_status['current_symbol'] = ''
        
        thread = threading.Thread(target=run_add)
        thread.start()
        
        return jsonify({'success': True, 'message': f'Adding {symbol} {timeframe}'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/status')
def api_status():
    """API endpoint for update status"""
    return jsonify(data_manager.update_status)

if __name__ == '__main__':
    print("🚀 Starting Data Management Dashboard...")
    print("🌐 Access at: http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)