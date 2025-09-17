# Web Backtest Grid Search

## Hướng dẫn sử dụng

1. Cài đặt thư viện:
```
pip install flask pandas numpy tqdm
```

2. Đảm bảo file `backtest_gridsearch_slbe_ts_Version3.py` (code backtest gốc) nằm cùng thư mục với `web_backtest`.

3. Chạy app:
```
cd web_backtest
python app.py
```

4. Truy cập giao diện tại: [http://localhost:5000](http://localhost:5000)

5. Upload file trade/candle, nhập dải tham số, chọn số lệnh khảo sát, nhấn "Chạy Backtest" để xem kết quả, biểu đồ, log.

## Cấu trúc thư mục
```
web_backtest/
├── app.py
├── backtest_gridsearch.py
├── templates/
│   ├── index.html
│   └── result.html
├── static/
└── README.md
```

## Lưu ý
- Nếu muốn sửa logic backtest, hãy sửa file `backtest_gridsearch_slbe_ts_Version3.py` và đảm bảo import đúng trong `backtest_gridsearch.py`.
- Có thể mở rộng thêm export kết quả, log, hoặc vẽ biểu đồ chi tiết hơn nếu cần.
