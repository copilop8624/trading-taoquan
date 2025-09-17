# 🚀 Hướng Dẫn Sử Dụng Multi-Symbol Trading Platform

## 📋 Mục Lục
1. [Khởi Động Hệ Thống](#khởi-động-hệ-thống)
2. [Trang Chủ - Dashboard](#trang-chủ---dashboard)
3. [Batch Processing - Xử Lý Hàng Loạt](#batch-processing---xử-lý-hàng-loạt)
4. [Compare Results - So Sánh Kết Quả](#compare-results---so-sánh-kết-quả)
5. [Analytics - Phân Tích Dữ Liệu](#analytics---phân-tích-dữ-liệu)
6. [Tips & Tricks](#tips--tricks)
7. [Troubleshooting](#troubleshooting)

---

## 🔥 Khởi Động Hệ Thống

### Bước 1: Khởi động Web App
```bash
# Mở terminal tại thư mục BTC
cd "C:\Users\aio\OneDrive\Desktop\DATA TRADINGVIEW\backtest\BTC"

# Chạy web app
python web_app.py
```

### Bước 2: Truy cập Web Interface
- Mở browser và vào: **http://localhost:5000**
- Hoặc click vào link hiển thị trong terminal

### Bước 3: Kiểm tra System Status
- Web app sẽ hiển thị symbols và timeframes có sẵn
- Ví dụ output:
```
📊 Discovered 3 symbols with data:
   BINANCE_BOMEUSDT: ['240']
   BINANCE_BTCUSDT: ['60', '30', '5'] 
   BINANCE_SAGAUSDT: ['30']
✅ CHẾ ĐỘ NÂNG CAO ĐÃ KÍCH HOẠT
```

---

## 🏠 Trang Chủ - Dashboard

### Navigation Menu
- **🏠 Home**: Trang chủ với overview
- **📊 Batch Processing**: Xử lý optimization hàng loạt
- **🔍 Compare Results**: So sánh kết quả
- **📈 Analytics**: Dashboard phân tích

### Main Dashboard Features
1. **System Overview**: Thống kê tổng quan
2. **Quick Optimization**: Chạy optimization nhanh cho 1 symbol
3. **Recent Results**: Kết quả optimization gần đây
4. **Performance Chart**: Biểu đồ hiệu suất

---

## 📊 Batch Processing - Xử Lý Hàng Loạt

### Truy cập: `http://localhost:5000/batch`

### Workflow Batch Processing:

#### 1. **Chọn Symbols**
- Click vào các symbol cards để chọn
- **Select All**: Chọn tất cả symbols
- **Clear All**: Bỏ chọn tất cả
- Symbols được chọn sẽ có viền xanh

#### 2. **Cấu hình Parameters**
```
🎯 Optimization Method:
- Optuna (Bayesian) - Thông minh, 500 trials
- Grid Search - Toàn diện nhưng lâu hơn

📊 Number of Trials: 10-1000 (default: 100)
⚡ Parallel Workers: 1-8 (default: 4) 
⏱️ Timeout: 5-480 minutes (default: 60)
```

#### 3. **Bắt đầu Batch**
- Click **🚀 Start Batch Optimization**
- System sẽ hiển thị real-time progress
- Mỗi symbol có progress bar riêng

#### 4. **Theo dõi Progress**
```
Overall Progress: [████████░░] 80%
Symbol Progress:
├── BINANCE_BTCUSDT: Running (65%) - Best PnL: $1,234
├── BINANCE_BOMEUSDT: Completed (100%) - Best PnL: $890
└── BINANCE_SAGAUSDT: Pending (0%)
```

#### 5. **Xem Kết Quả**
- Kết quả hiển thị ngay khi hoàn thành
- Table với Best PnL, Win Rate, Max DD, Sharpe
- Click **View Details** để xem chi tiết

---

## 🔍 Compare Results - So Sánh Kết Quả

### Truy cập: `http://localhost:5000/compare`

### Tính năng chính:

#### 1. **Compare Configuration**
- Chọn symbols để so sánh
- Filter theo timeframe
- Filter theo date range
- Chọn metrics để so sánh

#### 2. **Comparison Views**
```
📋 Table View:
- Side-by-side parameter comparison
- Performance metrics comparison
- Statistical significance tests

📊 Chart View:
- Performance scatter plots
- Parameter distribution charts
- Risk-return analysis
- Correlation matrices
```

#### 3. **Export Functions**
- Export comparison results to CSV
- Save charts as PNG
- Generate comparison reports

---

## 📈 Analytics - Phân Tích Dữ Liệu

### Truy cập: `http://localhost:5000/analytics`

### Dashboard có 6 loại charts:

#### 1. **📈 Performance Radar Chart**
```
Hiển thị:
- PnL, Win Rate, Profit Factor
- Max Drawdown, Sharpe Ratio
- Trade Count, Average Trade
So sánh đa chiều performance
```

#### 2. **📊 Parameter Distribution**
```
Bar Charts cho:
- SL, BE, TS parameter distribution
- Frequency của best parameters
- Optimal range identification
```

#### 3. **🎯 Risk-Return Scatter**
```
Scatter Plot:
- X-axis: Risk (Max Drawdown)
- Y-axis: Return (Total PnL)
- Bubble size: Trade Count
- Color: Win Rate
```

#### 4. **🔥 Performance Heatmap**
```
Heatmap matrix:
- Symbols vs Timeframes
- Parameter combinations
- Performance correlations
```

#### 5. **📉 Time Series Analysis**
```
Timeline Charts:
- Performance over time
- Parameter evolution
- Trend analysis
```

#### 6. **💹 Correlation Matrix**
```
Correlation between:
- Different symbols
- Parameter effectiveness
- Risk factors
```

### Interactive Controls:
- **Symbol Filter**: Chọn symbols cụ thể
- **Timeframe Filter**: Filter theo timeframe
- **Date Range**: Chọn khoảng thời gian
- **Metric Selection**: Chọn metrics hiển thị
- **Chart Type Toggle**: Chuyển đổi loại chart

---

## 💡 Tips & Tricks

### 🚀 Optimization Best Practices:

#### 1. **Chọn Parameters Hiệu Quả**
```
Recommended ranges:
- SL: 1.0-5.0 (step 0.5)
- BE: 0.5-3.0 (step 0.5)  
- TS: 1.0-4.0 (step 0.5)
```

#### 2. **Batch Processing Strategy**
```
Giai đoạn 1: Quick scan (100 trials, Optuna)
- Tìm rough optimal ranges
- Identify promising symbols

Giai đoạn 2: Deep dive (500+ trials, Grid)
- Focus vào best symbols
- Fine-tune parameters
```

#### 3. **Performance Analysis**
```
Key Metrics Priority:
1. Sharpe Ratio > 1.5
2. Max Drawdown < 15%
3. Win Rate > 55%
4. Profit Factor > 1.3
5. Minimum 100+ trades
```

### 📊 Reading Charts Effectively:

#### **Radar Chart** - Overall Performance
- Càng rộng = càng tốt
- Cân bằng giữa risk và return
- Tìm symbols có shape đều

#### **Scatter Plot** - Risk vs Return  
- Top-right quadrant = best (high return, low risk)
- Avoid bottom-left (low return, high risk)
- Bubble size = sample size reliability

#### **Heatmap** - Correlation Analysis
- Dark red = strong positive correlation
- Dark blue = strong negative correlation  
- Use để diversify portfolio

---

## 🔧 Troubleshooting

### Common Issues & Solutions:

#### 1. **Web App không start**
```bash
# Check Python environment
python --version  # Should be 3.8+

# Install missing packages
pip install flask optuna pandas numpy

# Check port availability
netstat -an | findstr 5000
```

#### 2. **404 Error trên routes**
```bash
# Restart web app
Ctrl+C (stop current)
python web_app.py (restart)

# Check templates folder exists
ls templates/
```

#### 3. **No data symbols found**
```bash
# Check data files
ls *.csv

# Verify file format:
# BINANCE_SYMBOL.P, TIMEFRAME.csv
# hoặc SYMBOL-tradelist-*.csv
```

#### 4. **Batch processing stuck**
```
- Check terminal for error messages
- Reduce number of trials
- Try single symbol first
- Check memory usage (Task Manager)
```

#### 5. **Charts không load**
```
- Check internet connection (Chart.js CDN)
- Refresh browser (F5)
- Clear browser cache
- Try different browser
```

### 🔍 Debug Commands:

#### System Health Check:
```bash
python -c "
from data_manager import get_data_manager
from results_manager import get_results_manager
dm = get_data_manager()
rm = get_results_manager()
print(f'Symbols: {dm.get_available_symbols()}')
print(f'Results: {len(rm.get_summary_statistics())}')
"
```

#### Test Individual Components:
```bash
# Test data manager
python -c "from data_manager import get_data_manager; print('Data OK')"

# Test results manager  
python -c "from results_manager import get_results_manager; print('Results OK')"

# Test web imports
python -c "import web_app; print('Web OK')"
```

---

## 🎯 Advanced Usage

### 1. **Custom Parameter Ranges**
Modify trong batch form để test specific ranges:
```javascript
// Custom SL range
sl_min: 2.0, sl_max: 4.0, sl_step: 0.2

// Custom BE range  
be_min: 1.0, be_max: 2.5, be_step: 0.25
```

### 2. **API Endpoints**
Hệ thống cung cấp REST APIs:
```
GET /api/analytics/history - Lịch sử optimization
GET /api/analytics/parameters - Parameter analysis
GET /api/analytics/symbols - Symbol statistics
POST /api/compare - Compare multiple results
GET /batch_status/<batch_id> - Batch progress
```

### 3. **Export & Backup**
```bash
# Export results to CSV
# Qua Analytics dashboard > Export button

# Backup optimization database
cp slbe_ts_opt_results.csv backup_results_$(date +%Y%m%d).csv
```

---

## 📞 Support & Contact

Nếu gặp vấn đề:
1. Check troubleshooting section trước
2. Xem terminal output để debug
3. Restart web app là solution cho 80% issues
4. Backup data trước khi thử fixes

**Happy Trading! 🚀📈**