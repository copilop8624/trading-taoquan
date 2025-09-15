import os
import pandas as pd
from pathlib import Path


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


class DataManager:
    def __init__(self, data_dir='data'):
        self.data_dir = Path(data_dir)
        ensure_dir(self.data_dir)

    def _csv_path(self, symbol, timeframe):
        tf = timeframe.replace('/', '_')
        return self.data_dir / f"{symbol}_{tf}.csv"

    def load_candles(self, symbol, timeframe):
        p = self._csv_path(symbol, timeframe)
        if not p.exists():
            return pd.DataFrame(columns=['timestamp','open','high','low','close','volume'])
        df = pd.read_csv(p, parse_dates=['timestamp'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        return df

    def append_new_candles(self, symbol, timeframe, new_df):
        """Append only rows whose timestamp is greater than last row in CSV (if exists).
        new_df expected to have 'timestamp' as datetime64[ns, UTC].
        Returns number of appended rows.
        """
        p = self._csv_path(symbol, timeframe)
        ensure_dir(p.parent)
        if p.exists():
            existing = pd.read_csv(p, parse_dates=['timestamp'])
            existing['timestamp'] = pd.to_datetime(existing['timestamp'], utc=True)
            if not existing.empty:
                last_ts = existing['timestamp'].max()
                # Only consider strictly newer timestamps
                to_append = new_df[new_df['timestamp'] > last_ts].copy()
            else:
                to_append = new_df.copy()
            if to_append.empty:
                return 0
            # Remove duplicates inside to_append (by timestamp)
            to_append = to_append.drop_duplicates(subset=['timestamp'])
            # Concatenate and ensure ordering by timestamp asc, also drop any accidental duplicates
            combined = pd.concat([existing, to_append], ignore_index=True)
            combined['timestamp'] = pd.to_datetime(combined['timestamp'], utc=True)
            combined = combined.sort_values('timestamp').drop_duplicates(subset=['timestamp'], keep='first')
            combined.to_csv(p, index=False)
            return len(to_append)
        else:
            # Ensure new_df has unique timestamps and sorted
            nd = new_df.copy()
            nd['timestamp'] = pd.to_datetime(nd['timestamp'], utc=True)
            nd = nd.sort_values('timestamp').drop_duplicates(subset=['timestamp'], keep='first')
            nd.to_csv(p, index=False)
            return len(nd)
