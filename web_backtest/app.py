from flask import Flask, request, render_template, redirect, url_for, send_file, jsonify
import os
import pandas as pd
from werkzeug.utils import secure_filename
from backtest_gridsearch_slbe_ts_Version3 import (
    load_trade_csv, load_candle_csv, get_trade_pairs, grid_search_parallel
)
import numpy as np

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Lấy file và tham số
        trade_file = request.files['trade_file']
        candle_file = request.files['candle_file']
        if not (trade_file and allowed_file(trade_file.filename) and candle_file and allowed_file(candle_file.filename)):
            return render_template('index.html', error='Vui lòng upload đúng định dạng file CSV!')
        trade_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(trade_file.filename))
        candle_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(candle_file.filename))
        trade_file.save(trade_path)
        candle_file.save(candle_path)
        # Lấy tham số
        sl_min = float(request.form['sl_min'])
        sl_max = float(request.form['sl_max'])
        sl_step = float(request.form['sl_step'])
        be_min = float(request.form['be_min'])
        be_max = float(request.form['be_max'])
        be_step = float(request.form['be_step'])
        ts_trig_min = float(request.form['ts_trig_min'])
        ts_trig_max = float(request.form['ts_trig_max'])
        ts_trig_step = float(request.form['ts_trig_step'])
        ts_step_min = float(request.form['ts_step_min'])
        ts_step_max = float(request.form['ts_step_max'])
        ts_step_step = float(request.form['ts_step_step'])
        n_trades = int(request.form['n_trades'])
        opt_type = request.form.get('opt_type', 'pnl')
        # Chạy backtest
        df_trade = load_trade_csv(trade_path)
        df_candle = load_candle_csv(candle_path)
        
        # Lọc trade theo số lượng
        if n_trades > 0:
            trade_order = df_trade.sort_values('date', ascending=False)['trade'].unique()[:n_trades]
            df_trade = df_trade[df_trade['trade'].isin(trade_order)]
        
        # Tạo trade pairs
        trade_pairs, log_init = get_trade_pairs(df_trade)
        
        # Tạo parameter lists
        sl_list = list(np.arange(sl_min, sl_max + sl_step/2, sl_step))
        be_list = list(np.arange(be_min, be_max + be_step/2, be_step))
        ts_trig_list = list(np.arange(ts_trig_min, ts_trig_max + ts_trig_step/2, ts_trig_step))
        ts_step_list = list(np.arange(ts_step_min, ts_step_max + ts_step_step/2, ts_step_step))
        
        # Chạy grid search
        results = grid_search_parallel(trade_pairs, df_candle, sl_list, be_list, ts_trig_list, ts_step_list, opt_type)
        
        # Tạo chart data từ top result
        chart_data = results[0]['details'] if results else []
        # Xoá file tạm
        os.remove(trade_path)
        os.remove(candle_path)
        return render_template('result.html', results=results, log=log_init, chart_data=chart_data)
    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    # Chạy trên tất cả network interfaces và port 5000
    # Để truy cập từ điện thoại Android qua WiFi
    app.run(host='0.0.0.0', port=5000, debug=True)
