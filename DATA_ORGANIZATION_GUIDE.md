# 📁 Hướng Dẫn Tổ Chức Dữ Liệu Trading

## 🎯 Cấu Trúc Khuyến Nghị

### **Phương Án 1: Tổ Chức Theo Symbol (KHUYẾN NGHỊ)**

```
data_organized/
├── candles/                    # 📈 Dữ liệu nến (OHLCV)
│   ├── BTCUSDT/
│   │   ├── 5m.csv             # BINANCE_BTCUSDT.P, 5.csv
│   │   ├── 30m.csv            # BINANCE_BTCUSDT.P, 30.csv
│   │   └── 60m.csv            # BINANCE_BTCUSDT, 60.csv
│   ├── BOMEUSDT/
│   │   └── 240m.csv           # BINANCE_BOMEUSDT.P, 240.csv
│   └── SAGAUSDT/
│       └── 30m.csv            # BINANCE_SAGAUSDT.P, 30.csv
│
├── tradelists/                 # 📊 Danh sách giao dịch
│   ├── BTCUSDT/
│   │   ├── 5m_BSATR.csv       # M5-tradelist-BSATR.csv
│   │   ├── 30m_BS4.csv        # 30-tradelist-BS4.csv
│   │   └── 60m_LONGSHORT.csv  # 60-tradelist-LONGSHORT.csv
│   ├── BOMEUSDT/
│   │   └── 240m_signals.csv
│   └── SAGAUSDT/
│       └── 30m_signals.csv
│
└── results/                    # 💰 Kết quả optimization
    ├── batch_results/
    ├── single_symbol/
    └── comparisons/
```

## 🔄 Hướng Dẫn Di Chuyển Dữ Liệu

### **Bước 1: Copy File Candle**
```powershell
# Copy vào thư mục theo symbol
copy "BINANCE_BTCUSDT.P, 5.csv" "data_organized\candles\BTCUSDT\5m.csv"
copy "BINANCE_BTCUSDT.P, 30.csv" "data_organized\candles\BTCUSDT\30m.csv"  
copy "BINANCE_BTCUSDT, 60.csv" "data_organized\candles\BTCUSDT\60m.csv"
copy "BINANCE_BOMEUSDT.P, 240.csv" "data_organized\candles\BOMEUSDT\240m.csv"
copy "BINANCE_SAGAUSDT.P, 30.csv" "data_organized\candles\SAGAUSDT\30m.csv"
```

### **Bước 2: Copy File Tradelist**
```powershell
copy "M5-tradelist-BSATR.csv" "data_organized\tradelists\BTCUSDT\5m_BSATR.csv"
copy "30-tradelist-BS4.csv" "data_organized\tradelists\BTCUSDT\30m_BS4.csv"
copy "60-tradelist-LONGSHORT.csv" "data_organized\tradelists\BTCUSDT\60m_LONGSHORT.csv"
```

### **Bước 3: Cập Nhật Web App**
Sửa web_app.py để scan từ data_organized thay vì thư mục gốc.

## 📋 Phương Án 2: Giữ Nguyên + Tạo Symlinks (Đơn Giản)

**Ưu điểm:**
- Không cần di chuyển file
- Không phá vỡ hệ thống hiện tại
- Chỉ tạo shortcuts tổ chức

**Cách làm:**
```powershell
# Tạo symbolic links đến file gốc
mklink "data_organized\candles\BTCUSDT\30m.csv" "..\..\..\BINANCE_BTCUSDT.P, 30.csv"
```

## 🎯 Lợi Ích Tổ Chức

### **Trước khi tổ chức:**
```
❌ BINANCE_BTCUSDT.P, 30.csv      # Khó đọc
❌ 30-tradelist-BS4.csv           # Không rõ symbol
❌ File rải rác khắp nơi
```

### **Sau khi tổ chức:**
```
✅ candles/BTCUSDT/30m.csv        # Rõ ràng
✅ tradelists/BTCUSDT/30m_BS4.csv # Dễ tìm
✅ Cấu trúc logic, dễ scale
```

## 🚀 Khuyến Nghị Cho Bạn

**GIẢI PHÁP ĐƯỢC KHUYẾN NGHỊ:**

1. **Giữ nguyên file hiện tại** (để hệ thống vẫn hoạt động)
2. **Tạo thư mục data_organized** (như đã tạo)
3. **Copy file vào cấu trúc mới** 
4. **Sau đó update web_app.py** để scan từ cả 2 nơi

### **Tại sao khuyến nghị cách này:**
- ✅ An toàn: Không phá vỡ hệ thống
- ✅ Linh hoạt: Có thể rollback
- ✅ Scale: Dễ thêm symbol mới
- ✅ Maintain: Dễ bảo trì code

## 📝 Các Bước Tiếp Theo

1. **Di chuyển dữ liệu** (script tự động)
2. **Cập nhật web_app.py** 
3. **Test hệ thống**
4. **Xóa file cũ** (sau khi confirm hoạt động)

## 🔧 Script Tự Động

Tôi có thể tạo script PowerShell để tự động:
- Scan tất cả file CSV hiện tại
- Phân loại candle vs tradelist  
- Copy vào cấu trúc mới
- Cập nhật web_app.py

**Bạn có muốn tôi tạo script tự động không?**