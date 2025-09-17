# ⚡ QUICK START GUIDE - 5 phút bắt đầu

## 🚀 Bước 1: Khởi động (30 giây)
```bash
# Mở terminal tại folder BTC
python web_app.py

# Đợi thấy:
✅ CHẾ ĐỘ NÂNG CAO ĐÃ KÍCH HOẠT
🌐 Access at: http://localhost:5000
```

## 🎯 Bước 2: Truy cập Web (10 giây)
- Mở browser: **http://localhost:5000**
- Thấy dashboard với symbols có sẵn

## 📊 Bước 3: Chạy Batch đầu tiên (2 phút)

### 3.1 Vào Batch Processing
- Click **📊 Batch Processing** trên menu

### 3.2 Cấu hình đơn giản
```
✅ Chọn 1-2 symbols (click vào cards)
✅ Optimization Method: Optuna  
✅ Number of Trials: 50 (cho nhanh)
✅ Parallel Workers: 2-4
✅ Timeout: 30 minutes
```

### 3.3 Start Batch
- Click **🚀 Start Batch Optimization**
- Xem real-time progress

## 📈 Bước 4: Xem kết quả (1 phút)
- Đợi batch hoàn thành
- Xem results table
- Click **View Details** để xem chi tiết

## 🔍 Bước 5: Khám phá Analytics (1 phút)
- Click **📈 Analytics** trên menu
- Xem các charts tự động generate
- Try các filter controls

---

## 🎮 Test Drive - Workflow mẫu:

### Test 1: Single Symbol Quick (5 phút)
```
1. Chọn BINANCE_BTCUSDT (có nhiều timeframes)
2. Trials: 30, Workers: 2
3. Xem kết quả và so sánh timeframes
```

### Test 2: Multi-Symbol Compare (10 phút)  
```
1. Chọn tất cả symbols available
2. Trials: 100, Workers: 4
3. Vào Compare để so sánh performance
4. Vào Analytics để xem correlations
```

### Test 3: Deep Analysis (20 phút)
```
1. Chọn symbol tốt nhất từ Test 2
2. Trials: 300, Grid Search
3. Analyze parameters trong Analytics
4. Export results
```

---

## 🚨 Lưu ý quan trọng:

### ✅ DOs:
- Start với ít trials trước (30-50)
- Test 1 symbol trước khi chạy batch lớn
- Save/screenshot kết quả tốt
- Backup data định kỳ

### ❌ DON'Ts:  
- Đừng chạy quá nhiều symbols cùng lúc lần đầu
- Đừng set timeout quá thấp (<15 phút)
- Đừng close browser khi batch đang chạy
- Đừng run multiple batches đồng thời

---

## 🔥 Pro Tips:

### Shortcut Keys:
- **F5**: Refresh page
- **Ctrl+Shift+R**: Hard refresh
- **F12**: Open dev tools (check console)

### Best Settings cho bắt đầu:
```
Symbols: 1-2 symbols
Trials: 50-100  
Workers: 2-4
Timeout: 30-60 minutes
Method: Optuna (faster)
```

### Đọc kết quả:
- **PnL > 0**: Profitable
- **Win Rate > 50%**: Good hit rate  
- **Max DD < 20%**: Acceptable risk
- **Sharpe > 1.0**: Good risk-adjusted return

---

## 🆘 SOS - Nếu có vấn đề:

### Problem: Web app không start
**Solution**: 
```bash
pip install flask optuna pandas
python web_app.py
```

### Problem: 404 errors
**Solution**: Restart web app
```bash
Ctrl+C
python web_app.py  
```

### Problem: No symbols found
**Solution**: Check data files có đúng format không
```
BINANCE_BTCUSDT.P, 30.csv ✅
BINANCE_BTCUSDT, 60.csv ✅
tradelist-*.csv ✅
```

### Problem: Batch stuck
**Solution**: 
1. Check terminal for errors
2. Reduce trials number
3. Restart web app

---

## 🎉 Kết quả mong đợi sau 5 phút:

✅ Web app running on localhost:5000
✅ 1 batch optimization completed  
✅ Results table với best parameters
✅ Charts trong Analytics dashboard
✅ Hiểu workflow cơ bản

**➡️ Giờ đọc USER_GUIDE.md để advanced usage! 🚀**