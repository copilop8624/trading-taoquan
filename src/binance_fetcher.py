import time
import pandas as pd
from datetime import datetime, timezone
import random


CUSTOM_TIMEFRAME_MAP = {
    '1m': '1m',
    '5m': '5m',
    '15m': '15m',
    '30m': '30m',
    '1h': '1h',
    '4h': '4h',
    '1d': '1d'
}


class BinanceFetcher:
    def __init__(self, rate_limit=True, **kwargs):
        # Import ccxt lazily to avoid import-time dependency for tests/dry-run
        try:
            import ccxt as _ccxt
        except Exception as e:
            # Defer raising until fetch methods are invoked
            _ccxt = None
        if _ccxt is None:
            self.exchange = None
        else:
            self.exchange = _ccxt.binance({
                'enableRateLimit': rate_limit
            })
        # optional verbose flag
        self.verbose = bool(kwargs.get('verbose', False))

    def _is_retryable(self, exc):
        # If ccxt types are not available, conservatively retry on generic network errors
        try:
            name = exc.__class__.__name__
            retryable = name in ('NetworkError', 'RequestTimeout', 'DDoSProtection', 'ExchangeError')
            return retryable
        except Exception:
            return False

    def fetch_klines(self, symbol, timeframe='1m', since=None, limit=1000, max_retries=5):
        """Fetch klines from Binance (ccxt) starting from `since` (ms epoch) or latest `limit` candles.
        Returns pandas DataFrame with columns: ['timestamp','open','high','low','close','volume'] and timestamp in UTC datetime.
        """
        tf = CUSTOM_TIMEFRAME_MAP.get(timeframe, timeframe)
        all_rows = []
        # ccxt returns [timestamp, open, high, low, close, volume]
        since_ms = int(since) if since is not None else None
        attempt = 0
        backoff = 1
        if self.exchange is None:
            # ccxt not available in this environment
            if self.verbose:
                print("ccxt library not available; fetch_klines will return empty DataFrame")
            return pd.DataFrame(columns=['timestamp','open','high','low','close','volume'])

        while attempt < max_retries:
            try:
                fetched = self.exchange.fetch_ohlcv(symbol, timeframe=tf, since=since_ms, limit=limit)
                df = pd.DataFrame(fetched, columns=['timestamp','open','high','low','close','volume'])
                if not df.empty:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                if self.verbose:
                    print(f"Fetched {len(df)} rows for {symbol} {tf}")
                return df
            except Exception as e:
                attempt += 1
                should_retry = self._is_retryable(e)
                if self.verbose:
                    print(f"Fetch klines error for {symbol} {timeframe} (attempt {attempt}/{max_retries}): {e}")
                if attempt >= max_retries or not should_retry:
                    if self.verbose:
                        print(f"Giving up on {symbol} {timeframe} after {attempt} attempts.")
                    return pd.DataFrame(columns=['timestamp','open','high','low','close','volume'])
                else:
                    # Add jitter +/-20%
                    jitter = random.uniform(0.8, 1.2)
                    delay = min(backoff * jitter, 16)
                    if self.verbose:
                        print(f"Retrying in {delay:.2f}s (base {backoff}s, jitter {jitter:.2f})...")
                    time.sleep(delay)
                    backoff = min(backoff * 2, 16)
        return pd.DataFrame(columns=['timestamp','open','high','low','close','volume'])

    def fetch_for_symbol(self, symbol, timeframes, data_manager, since_map=None, limit=1000):
        """Fetch all timeframes sequentially for a single symbol and append to CSVs.
        since_map: optional dict mapping timeframe->since_ms to start from specific timestamps.
        Returns dict timeframe->appended_count
        """
        results = {}
        for tf in timeframes:
            since_ms = None
            if since_map and tf in since_map and since_map[tf] is not None:
                since_ms = int(since_map[tf])
            if self.verbose:
                print(f"Fetching {symbol} {tf} since={since_ms}")
            df = self.fetch_klines(symbol, timeframe=tf, since=since_ms, limit=limit)
            # ensure timestamp column exists
            if df is None or df.empty:
                if self.verbose:
                    print(f"No data fetched for {symbol} {tf}")
                results[tf] = 0
                continue
            # append to CSV using data_manager
            appended = data_manager.append_new_candles(symbol, tf, df)
            if self.verbose:
                print(f"Appended {appended} rows for {symbol} {tf}")
            results[tf] = appended
        return results
