import os
import pandas as pd

def fix_csv_add_volume(filepath, time_col_candidates=["d", "date", "datetime", "timestamp", "time"]):
    df = pd.read_csv(filepath)
    # Tìm cột thời gian
    for col in time_col_candidates:
        if col in df.columns:
            df.rename(columns={col: "time"}, inplace=True)
            break
    # Đảm bảo các cột OHLC
    for col in ["open", "high", "low", "close"]:
        if col not in df.columns:
            raise Exception(f"File {filepath} thiếu cột {col}")
    # Thêm cột volume nếu thiếu
    if "volume" not in df.columns:
        df.insert(df.columns.get_loc("close") + 1, "volume", 0)
    # Đưa cột time lên đầu
    cols = list(df.columns)
    if cols[0] != "time":
        cols.remove("time")
        cols = ["time"] + cols
    df = df[cols]
    # Ghi đè lại file
    df.to_csv(filepath, index=False)
    print(f"Đã sửa file: {filepath}")

if __name__ == "__main__":
    # Quét toàn bộ file CSV trong thư mục hiện tại
    for fname in os.listdir('.'):
        if fname.lower().endswith('.csv'):
            try:
                fix_csv_add_volume(fname)
            except Exception as e:
                print(f"Lỗi với file {fname}: {e}")
