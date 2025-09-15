import json
import argparse
from pathlib import Path
import pandas as pd
from src.binance_fetcher import BinanceFetcher
from src.data_manager import DataManager
from src.tradelist_manager import TradelistManager
from src.simulator import Simulator
from concurrent.futures import ThreadPoolExecutor, as_completed


def load_config(path='config.json'):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def update_candles_for_symbol(fetcher, manager, symbol, timeframe):
    csv_df = manager.load_candles(symbol, timeframe)
    if not csv_df.empty:
        last_ts = csv_df['timestamp'].max().to_pydatetime()
        since_ms = int(last_ts.timestamp() * 1000) + 1
    else:
        since_ms = None
    fetched = fetcher.fetch_klines(symbol, timeframe=timeframe, since=since_ms, limit=1000)
    if fetched is None or fetched.empty:
        return 0
    count = manager.append_new_candles(symbol, timeframe, fetched)
    return count


def plan_fetches(config_path='config.json'):
    """Return a structured plan of fetches (symbol, timeframe, since_ms, estimated_rows) without calling APIs."""
    cfg = load_config(config_path)
    data_dir = cfg.get('data_dir', 'data')
    manager = DataManager(data_dir)
    plans = []
    tf_map = {'1m': 60, '5m': 300, '15m': 900, '30m': 1800, '1h': 3600, '4h': 14400, '1d': 86400}
    now_ms = int(pd.Timestamp.utcnow().timestamp() * 1000)
    for s in cfg['symbols']:
        symbol = s['symbol']
        for tf in s['timeframes']:
            csv_df = manager.load_candles(symbol, tf)
            if not csv_df.empty and 'timestamp' in csv_df.columns and len(csv_df):
                last_ts = csv_df['timestamp'].max().to_pydatetime()
                since_ms = int(last_ts.timestamp() * 1000) + 1
            else:
                since_ms = None
            est_rows = 'unknown'
            if since_ms is not None and tf in tf_map:
                est_rows = max(0, int((now_ms - since_ms) / (tf_map[tf] * 1000)))
            plans.append({'symbol': symbol, 'timeframe': tf, 'since_ms': since_ms, 'estimated_new_rows': est_rows})
    return {'planned_fetches': plans}


def main(config_path='config.json', strategy_override=None, fetcher=None, manager=None, tradelist_mgr=None, simulator=None):
    cfg = load_config(config_path)
    data_dir = cfg.get('data_dir', 'data')
    tradelist_dir = cfg.get('tradelist_dir', 'tradelists')
    results_dir = cfg.get('results_dir', 'results')
    concurrency = cfg.get('concurrency', 6)

    # create fetcher with verbosity depending on runtime
    # dry_run might be set in cfg, but CLI verbose will be parsed later and injected via temp config
    # allow injection for programmatic use (e.g., tests or Flask)
    fetcher = fetcher or BinanceFetcher(verbose=bool(cfg.get('verbose', False)))
    manager = manager or DataManager(data_dir)
    tradelist_mgr = tradelist_mgr or TradelistManager(tradelist_dir)
    simulator = simulator or Simulator()
    
    # Respect dry-run flag in cfg? We'll accept runtime flag via CLI below (patches to __main__ section)

    # 1. Auto-update candles: fetch per-symbol sequentially for requested timeframes
    dry_run = cfg.get('dry_run', False)
    if dry_run:
        print("DRY-RUN MODE: Will not call Binance API. Planned fetches:")
        for s in cfg['symbols']:
            symbol = s['symbol']
            for tf in s['timeframes']:
                csv_df = manager.load_candles(symbol, tf)
                if not csv_df.empty:
                    last_ts = csv_df['timestamp'].max().to_pydatetime()
                    since_ms = int(last_ts.timestamp() * 1000) + 1
                else:
                    since_ms = None
                # Estimate number of missing rows by comparing last_ts to now
                est_rows = 'unknown'
                if since_ms is not None:
                    now_ms = int(pd.Timestamp.utcnow().timestamp() * 1000)
                    # convert timeframe to seconds (simple mapping)
                    tf_map = {'1m': 60, '5m': 300, '15m': 900, '30m': 1800, '1h': 3600, '4h': 14400, '1d': 86400}
                    tf_seconds = tf_map.get(tf, None)
                    if tf_seconds:
                        est_rows = max(0, int((now_ms - since_ms) / (tf_seconds * 1000)))
                print(f"  - {symbol} {tf} since={since_ms} estimated_new_rows={est_rows}")
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futures = {}
            for s in cfg['symbols']:
                symbol = s['symbol']
                timeframes = s['timeframes']
                # submit one job per symbol which will fetch each timeframe sequentially
                futures[ex.submit(fetcher.fetch_for_symbol, symbol, timeframes, manager)] = symbol

            for f in as_completed(futures):
                symbol = futures[f]
                try:
                    res = f.result()
                    print(f"Updated symbol {symbol}: {res}")
                except Exception as e:
                    print(f"Error updating symbol {symbol}: {e}")

    # 2. Load or merge tradelist for selected strategy
    for s in cfg['symbols']:
        symbol = s['symbol']
        default_strategy = s.get('default_strategy')
        strategy = strategy_override or default_strategy
        # Try to load existing tradelist (if any)
        existing = tradelist_mgr.load_tradelist(strategy, symbol)
        print(f"Loaded {len(existing)} existing trades for {strategy}/{symbol}")
        # For CLI flow, assume user uploaded a file path - skip upload handling here

        # 3. Run simulation
        candles = manager.load_candles(symbol, s['timeframes'][0])
        results_df = simulator.run(symbol, s['timeframes'][0], strategy, existing, candles)
        saved = simulator.save_results(results_df, results_dir, symbol, s['timeframes'][0], strategy)
        print(f"Saved results to {saved}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.json')
    parser.add_argument('--strategy', default=None)
    parser.add_argument('--dry-run', action='store_true', help='Print planned fetches and skip API calls')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output for fetcher and retries')
    args = parser.parse_args()
    # If dry-run is set, inject into config by reading and modifying before call
    if args.dry_run or args.verbose:
        cfg_path = args.config
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
        if args.dry_run:
            cfg['dry_run'] = True
        if args.verbose:
            cfg['verbose'] = True
        # Write a temp config? Simpler: pass a small wrapper that main will ignore because we pass config path.
        # We'll instead set an environment-like override by creating a small temporary config file
        import tempfile
        tf = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(cfg, tf)
        tf.flush()
        tf.close()
        try:
            main(tf.name, args.strategy)
        finally:
            try:
                import os
                os.unlink(tf.name)
            except Exception:
                pass
    else:
        main(args.config, args.strategy)
