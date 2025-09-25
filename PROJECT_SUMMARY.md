TÓM TẮT DỰ ÁN "trading-taoquan"

1) Mục tiêu dự án
- Là một bộ công cụ backtest/optimizer cho chiến lược giao dịch (cụ thể cho BTC và các cặp khác).
- Chạy tối ưu hoá các tham số (SL/BE/TS/TS_step), mô phỏng trade-by-trade, tính các chỉ số hiệu suất (PnL, win_rate, max_drawdown, PF, sharpe, trades, v.v.).
- Cung cấp UI web đơn giản để chạy tối ưu hóa, xem "Top Results", so sánh "Baseline" vs "Optimized", và xuất/kiểm tra log.

2) Kiến trúc tổng quan
- Backend: Flask app đơn file `web_app.py` (có thể các file Python khác thực hiện tính toán/engine).
  - Chịu trách nhiệm chạy engine tối ưu, lưu kết quả (có DB/local storage), và trả JSON cho frontend.
  - Sinh `response_data` chứa các keys: `baseline_result`, `best_result`, `top_results` (danh sách), `cumulative_comparison`, `data`, `database_id`, v.v.
- Frontend: single-file template `templates/index.html` (client-side JS).
  - Hiển thị Top Results table, Optimized Strategy box, Baseline vs Optimized comparison, charts/tables.
  - Các hàm rendering chính: `displayOptimizationResults(data)`, `displayRangeOptimizationResults(data, params)`, `generateBaselineComparisonSection(data)`, v.v.
- Data: CSVs chứa dữ liệu nến (nhiều file), trade lists, và các file log/CSV kết quả. Có folder `__pycache__` và nhiều script hỗ trợ.

3) Dữ liệu và format quan trọng
- `results_data` (raw): mỗi mục chứa fields như `sl`, `be`, `ts`, `ts_step`, `total_profit` (float), `win_rate` (decimal, ex: 0.26666), `total_trades`, `win_trades`, `loss_trades`, `avg_win`, `avg_loss`, `max_drawdown` (float in %), `pf`, `sharpe_ratio`, `optimization_engine`, etc.
- `response_data['top_results']` (frontend-friendly): mapping tạo ra keys:
  - `total_pnl`: từ `result['total_profit']`
  - `winrate`: backend nhân `result['win_rate'] * 100` (so hiển thị phần trăm)
  - `pf`: từ `result.get('pf', 1.0)`
  - `max_drawdown`: try `result.get('max_drawdown') or result.get('drawdown') or result.get('max_dd') or 0.0`
  - `parameters`: mapping các giá trị `sl`, `be`, `ts_active`, `ts_step` có thể nhân *100 (tùy chỗ).
- Lưu ý về đơn vị: có sự không đồng nhất giữa nơi backend trả `win_rate` là decimal vs `top_results.winrate` là porcent — frontend cần thống nhất để tránh *100 nhầm.

4) File quan trọng
- `web_app.py` — Flask server core, tạo `response_data` và endpoints.
- `templates/index.html` — template UI; chứa phần lớn JavaScript render.
- `requirements.txt` — dependencies (để cài môi trường Python).
- Nhiều script tiện ích: `full_simulation_141.py`, `full_engine_test.py`, `debug_*`, `verify_*`, `simulate_*`, `optimization`-related scripts.
- CSV data files: nhiều tên bắt đầu `BINANCE_*` và `tradelist-*.csv`.
- Docs: `README_DEPLOYMENT.md`, `OPTIMIZATION_SOP.md`, nhiều README/MD khác.

5) Luồng chạy (how-to)
- Thiết lập môi trường Python (virtualenv) và cài `requirements.txt`.
- Start server (có tasks trong workspace): ví dụ `.\\.venv_new\\Scripts\\python.exe web_app.py` hoặc chạy `run_server.py`/`start_server.bat`.
- Mở trình duyệt tới `http://127.0.0.1:5000` (hoặc host:port log console).
- Trong UI: chọn dataset/chiến lược → chạy optimization → xem Top Results và Optimized vs Baseline.
- Logs: backend in terminal, frontend in browser console. Kết quả lưu vào CSV `slbe_ts_opt_results.csv` hoặc DB.

6) Vấn đề hiện tại (most relevant bugs & symptoms)
- Triệu chứng chính đã thấy:
  - Optimized Strategy hiển thị `Max Drawdown = 0%` trong UI trong khi Top Results show đúng giá trị (ví dụ 8%).
  - Win Rate hiển thị bị nhân sai (ví dụ 26.67% hiển thị là 2667% hoặc 4340% do nhân 100 hai lần).
- Nguyên nhân đã xác định:
  - Backend đôi lúc trả `win_rate` là decimal (0.26), nhưng `top_results` mapping đã nhân *100. Frontend có nhiều chỗ vẫn nhân thêm *100 → double multiply.
  - Frontend có hai hàm cùng tên `displayOptimizationResults()` — hàm sau ghi đè hàm trước dẫn tới lộ trình render không như mong đợi.
  - Một số chỗ sử dụng field name không thống nhất (`pnl_total` vs `total_pnl`, `max_dd` vs `max_drawdown`) → mapping sai.
  - Một lần chỉnh sửa debug trên `web_app.py` đã gây lỗi cú pháp (unclosed bracket) — đã được sửa.
- Debugging đã làm:
  - Thêm debug prints trong `web_app.py` để in `results_data[0].keys()` và `response_data['top_results'][0]`.
  - Thêm console.log trong `templates/index.html` để in `bestResult`, `topResult`, `data.baseline_result`.
  - Renamed duplicate JS function `displayOptimizationResults` → `displayLegacyOptimizationResults`.
  - Sửa `displayRangeOptimizationResults()` để lấy `topResult = data.top_results[0]` và dùng `topResult?.max_drawdown`.
  - Sửa `pnl_total` → `total_pnl` và xóa các `* 100` thừa ở UI khi `top_results.winrate` đã là percent.
  - Kết quả debug cho thấy backend và top_results đã có `max_drawdown = 8.000000000000028` và `winrate = 26.6666`, nên vấn đề là mapping/frontend, đã fix nhiều nơi.

7) Những thay đổi gần đây (chú ý)
- `web_app.py`:
  - Sửa lỗi cú pháp do debug insertion.
  - Thêm fallback mapping cho `max_drawdown`.
  - Nhân `win_rate * 100` trong lúc tạo `top_results`.
  - In debug nội dung `top_results[0]`.
- `templates/index.html`:
  - Thêm nhiều `console.log` debug.
  - Đổi tên hàm `displayOptimizationResults` (duplicate) → `displayLegacyOptimizationResults`.
  - Sửa `displayRangeOptimizationResults()` để dùng `topResult?.max_drawdown`.
  - Sửa `pnl_total` → `total_pnl` và các chỗ nhân `*100` không cần thiết.

8) Kiểm tra / cách reproduce
- Bật server: `.\\.venv_new\\Scripts\\python.exe web_app.py`.
- Mở UI, chạy optimization test trên dataset (như đã dùng trước đó).
- Kiểm tra log terminal: tìm các dòng debug "🔍 DEBUG top_results[0] FULL:" để xác nhận `max_drawdown` tồn tại.
- Mở console trình duyệt: tìm `🔍 DEBUG topResult.max_drawdown: 8.000000000000028` hoặc tương tự.
- Kiểm tra UI: Optimized Strategy box phải hiển thị `Max Drawdown` bằng giá trị từ `top_results[0]` (ví dụ 8.00%).

9) Điểm cần chú ý / kỹ thuật đề xuất
- Chuẩn hoá một nơi duy nhất cho tỷ lệ (win_rate):
  - Option A (recommended): Backend trả tất cả tỷ lệ ở dạng phần trăm (winrate = 26.66) và frontend không nhân thêm. Thêm comment/document để dev khác biết.
  - Option B: Backend luôn trả decimal (0.2666) và frontend chịu trách nhiệm nhân *100 khi hiển thị. (Tránh lẫn lộn).
- Chuẩn hoá tên field: chọn `total_pnl`, `winrate`, `max_drawdown` làm chuẩn và refactor cả frontend/backend để phù hợp.
- Tránh duplicate JS function names; tách module hoặc đặt tên rõ ràng.
- Thêm unit tests cho mapping `results_data` → `response_data['top_results']`.
- Khi thêm debug prints, dùng logging module với mức độ (INFO/DEBUG) thay vì print, tránh gây lỗi cú pháp và dễ bật/tắt.

10) Bước tiếp theo cụ thể (gợi ý cho AI hoặc dev)
- Ngắn hạn (để fix ngay):
  - Refresh browser và chạy optimization; copy/paste 3 outputs: backend "🔍 DEBUG top_results[0] FULL", frontend console logs for `topResult` & `bestResult`, và screenshot/text của Optimized Strategy box.
  - Tìm và sửa mọi chỗ còn nhân `* 100` không cần thiết (search `* 100` trong `templates/index.html`).
- Trung hạn (ổn định codebase):
  - Tạo helper function ở backend `format_top_result(result)` để produce canonical dict used by frontend.
  - Refactor frontend renderers into smaller functions and remove duplicate names.
  - Add small tests to ensure fields map correctly.
- Dài hạn:
  - Migrate front-end JS into modular codebase (separate files), or adopt a frontend framework (React/Vue) for maintainability if project sẽ phát triển.
  - Document API (endpoints and response schema) so external tools can integrate easily.

11) Quick references (các lệnh hữu dụng)
- Start server (PowerShell):
````powershell
.\\.venv_new\\Scripts\\python.exe web_app.py
````
- Search for `* 100` in project (PowerShell):
````powershell
Select-String -Path * -Pattern "\* 100" -SimpleMatch -List
````
- Grep-like search (POSIX):
````sh
grep -R --line-number "\* 100" .
````

12) Contact points in repo (file list gợi ý để AI phân tích tiếp)
- `web_app.py`
- `templates/index.html`
- `requirements.txt`
- Các script: `full_engine_test.py`, `full_simulation_141.py`, `optimization*`, `debug_*`, `verify_*`
- Các CSV: `BINANCE_*`, `tradelist-*.csv`, `slbe_ts_opt_results.csv`

---


---

## [Cập nhật 2025-09-22]

**1. Chuẩn hóa symbol/timeframe toàn hệ thống:**
- Tất cả truy vấn DB, xử lý file, endpoint tối ưu hóa đều dùng hàm `normalize_symbol_format` để loại bỏ hoàn toàn lỗi prefix (BINANCE_) hoặc format symbol/timeframe.
- Đã loại bỏ lỗi "No candle data found" do mismatch symbol/timeframe giữa file, DB và UI.

**2. Cleanup debug print:**
- Đã loại bỏ phần lớn các print debug kiểm tra symbol/timeframe, truy vấn DB, chỉ giữ lại print báo lỗi thực sự, print trạng thái hệ thống, log tiến trình batch/optimize.

**3. Backup code:**
- Đã backup đầy đủ file `web_app.py` trước khi cleanup debug vào thư mục `backup/` với hậu tố ngày tháng.

**4. Fix circular import:**
- Đã kiểm tra và fix lỗi circular import ở các module data management (nếu có).

**5. Xác nhận chuẩn hóa luồng dữ liệu:**
- Đã kiểm tra lại toàn bộ luồng lấy tên file candle, tách symbol/timeframe, normalize, truyền vào truy vấn DB, mapping với dữ liệu thật trong DB. Đảm bảo không còn sai sót logic hoặc nhầm lẫn tên ở bất kỳ bước nào.

---

File này được tạo bởi trợ lý để bạn có thể copy/paste cho AI khác hoặc lưu làm tài liệu.
