import os
import pandas as pd
from pathlib import Path


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


class TradelistManager:
    def __init__(self, tradelist_dir='tradelists'):
        self.tradelist_dir = Path(tradelist_dir)
        ensure_dir(self.tradelist_dir)

    def _path(self, strategy, symbol):
        return self.tradelist_dir / f"{strategy}_{symbol}.csv"

    def load_tradelist(self, strategy, symbol):
        p = self._path(strategy, symbol)
        if not p.exists():
            return pd.DataFrame()
        df = pd.read_csv(p, parse_dates=['date'])
        # Ensure date column is timezone-naive for matching with candle times
        try:
            df['date'] = pd.to_datetime(df['date'])
            try:
                df['date'] = df['date'].dt.tz_convert(None)
            except Exception:
                try:
                    df['date'] = df['date'].dt.tz_localize(None)
                except Exception:
                    pass
        except Exception:
            pass
        return df

    def merge_tradelist(self, strategy, symbol, uploaded_df):
        """Merge uploaded tradelist DataFrame into existing file, append only new trades based on timestamp+side."""
        p = self._path(strategy, symbol)
        ensure_dir(p.parent)
        uploaded = uploaded_df.copy()
        # Normalize date column
        if 'date' in uploaded.columns:
            uploaded['date'] = pd.to_datetime(uploaded['date'], utc=True)
        elif 'date_time' in uploaded.columns:
            uploaded['date'] = pd.to_datetime(uploaded['date_time'], utc=True)
        else:
            # Try to find a date-like column
            for col in uploaded.columns:
                if 'date' in col.lower() or 'time' in col.lower():
                    uploaded['date'] = pd.to_datetime(uploaded[col], utc=True)
                    break

        # Normalize side
        if 'side' not in uploaded.columns and 'signal' in uploaded.columns:
            uploaded['side'] = uploaded['signal'].astype(str).str.lower()
        if 'side' in uploaded.columns:
            uploaded['side'] = uploaded['side'].astype(str).str.lower()

        # Normalize price column: prefer 'price', fall back to known alternatives
        if 'price' not in uploaded.columns:
            if 'price_usdt' in uploaded.columns:
                uploaded['price'] = uploaded['price_usdt']
            elif 'price_usd' in uploaded.columns:
                uploaded['price'] = uploaded['price_usd']
            elif 'entry_price' in uploaded.columns:
                uploaded['price'] = uploaded['entry_price']
        # Clean price formatting
        if 'price' in uploaded.columns:
            try:
                uploaded['price'] = uploaded['price'].astype(str).str.replace(',', '').str.replace('"', '')
                uploaded['price'] = pd.to_numeric(uploaded['price'], errors='coerce')
            except Exception:
                pass

        uploaded = uploaded.dropna(subset=['date']).copy()
        if uploaded.empty:
            return 0

        # Create unique key for deduplication
        if 'side' in uploaded.columns:
            side_series = uploaded['side'].astype(str)
        else:
            side_series = pd.Series([''] * len(uploaded), index=uploaded.index)
        uploaded['__k'] = uploaded['date'].astype(str) + '::' + side_series.astype(str)

        if p.exists():
            existing = pd.read_csv(p, parse_dates=['date'])
            existing['date'] = pd.to_datetime(existing['date'], utc=True)
            # store as timezone-naive to match candle files
            try:
                existing['date'] = pd.to_datetime(existing['date'])
                try:
                    existing['date'] = existing['date'].dt.tz_convert(None)
                except Exception:
                    try:
                        existing['date'] = existing['date'].dt.tz_localize(None)
                    except Exception:
                        pass
            except Exception:
                pass
            if 'side' in existing.columns:
                existing['side'] = existing['side'].astype(str).str.lower()
                existing_side = existing['side'].astype(str)
            else:
                existing['side'] = ''
                existing_side = pd.Series([''] * len(existing), index=existing.index)
            existing['__k'] = existing['date'].astype(str) + '::' + existing_side.astype(str)

            # Find new rows not present in existing by key
            to_append = uploaded[~uploaded['__k'].isin(existing['__k'])].copy()
            if to_append.empty:
                return 0

            # Combine and sort by date ascending, drop any duplicate keys
            combined = pd.concat([existing.drop(columns=['__k'], errors='ignore'), to_append.drop(columns=['__k'])], ignore_index=True)
            combined['date'] = pd.to_datetime(combined['date'], utc=True)
            # Normalize to timezone-naive datetimes before saving
            try:
                combined['date'] = pd.to_datetime(combined['date'])
                try:
                    combined['date'] = combined['date'].dt.tz_convert(None)
                except Exception:
                    try:
                        combined['date'] = combined['date'].dt.tz_localize(None)
                    except Exception:
                        pass
            except Exception:
                pass
            combined = combined.sort_values('date').reset_index(drop=True)
            if 'side' in combined.columns:
                combined_side = combined['side'].astype(str)
            else:
                combined_side = pd.Series([''] * len(combined), index=combined.index)
            combined['__k'] = combined['date'].astype(str) + '::' + combined_side.astype(str)
            combined = combined.drop_duplicates(subset=['__k'], keep='first').drop(columns=['__k'])
            combined.to_csv(p, index=False)
            return len(to_append)
        else:
            # First time: sort and drop duplicates in uploaded
            uploaded = uploaded.sort_values('date').reset_index(drop=True)
            # Ensure date is timezone-naive before saving
            try:
                uploaded['date'] = pd.to_datetime(uploaded['date'])
                try:
                    uploaded['date'] = uploaded['date'].dt.tz_convert(None)
                except Exception:
                    try:
                        uploaded['date'] = uploaded['date'].dt.tz_localize(None)
                    except Exception:
                        pass
            except Exception:
                pass
            uploaded = uploaded.drop_duplicates(subset=['__k'], keep='first').drop(columns=['__k'])
            uploaded.to_csv(p, index=False)
            return len(uploaded)
