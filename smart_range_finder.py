#!/usr/bin/env python3
"""
SMART PARAMETER RANGE FINDER (Entry-based)
=========================================
Refactored to analyze Entry trades (Entry long/short) instead of Exit records.
Adds TP1/TP2/TP3 suggestions derived from run-up percentiles and an
`export_ranges()` method that returns JSON-friendly ranges suitable for Optuna/grid.
Keeps class `SmartRangeFinder` and original flow but switches data source.
"""

import pandas as pd
import numpy as np
import warnings
from warning_codes import TP1_FLOOR, TP2_FLOOR, TP3_CAP, SL_FLOOR, BE_FLOOR, TS_TRIGGER_FLOOR, TS_STEP_FLOOR, TS_FLOOR_CANONICAL, INFO
warnings.filterwarnings('ignore')

# Practical minimum for trailing-stop trigger (percent)
TS_TRIGGER_MIN = 2.5
# Practical minimum for trailing-stop step (percent). Small values like 0.05% are unrealistic.
TS_STEP_FLOOR = 0.2

class SmartRangeFinder:
    def __init__(self, tradelist_path):
        """
        Initialize Smart Range Finder

        Purpose: Find intelligent parameter ranges for efficient grid search
        NOTE: This implementation uses entry-based statistics (from entry records).

        Implementation notes:
        - Trailing-stop trigger (`TS_trigger`) is floored at `TS_TRIGGER_MIN` (percent) to avoid impractically small triggers.
        - Trailing-stop step (`TS_step`) uses a floor (`TS_STEP_FLOOR`) so step values are usable in real trading (e.g. 0.2%).
        """
        self.tradelist_path = tradelist_path
        self.df = None
        self.exit_trades = None  # kept for backward compatibility
        self.entry_trades = None
        self.range_analysis = {}
        self.validation_issues = []
        # internal accumulator for analysis warnings (floor/cap events)
        self._analysis_warnings = []

        print("🎯 SMART RANGE FINDER (entry-based)")
        print(f"Loading: {tradelist_path}")

        # Load and validate data
        self._load_and_validate_data()

    def _load_and_validate_data(self):
        """Load and validate tradelist data with comprehensive error checking"""
        try:
            self.df = pd.read_csv(self.tradelist_path)
            print(f"✅ Loaded {len(self.df)} raw records")

            # Clean column names for consistent access
            orig_columns = list(self.df.columns)
            clean_columns = [col.strip().lower().replace(' ', '_').replace('/', '_').replace('#', '').replace('&', '') for col in orig_columns]
            self.df.columns = clean_columns

            # Identify key columns with flexible naming
            self.runup_col = self._find_key_column(['run_up_%', 'run-up_%', 'runup_%', 'max_favorable_%', 'runup'], 'Run-up')
            self.drawdown_col = self._find_key_column(['drawdown_%', 'draw_down_%', 'max_adverse_%', 'drawdown'], 'Drawdown')
            # PnL candidate detection (flexible)
            self.pnl_col = self._find_key_column(['net_pnl_%', 'net_pl_%', 'pnl_%', 'p_l_%', 'pl_%', 'cumulative_p_l_%', 'netpnl'], 'P&L')
            self.type_col = self._find_key_column(['type', 'signal_type', 'trade_type'], 'Type')

            missing_cols = []
            if not self.runup_col: missing_cols.append('Run-up % column')
            if not self.drawdown_col: missing_cols.append('Drawdown % column')
            if not self.pnl_col: missing_cols.append('P&L % column')
            if not self.type_col: missing_cols.append('Type column')

            if missing_cols:
                raise ValueError(f"Missing critical columns: {missing_cols}")

            print(f"📊 Key columns: runup={self.runup_col}, drawdown={self.drawdown_col}, pnl={self.pnl_col}, type={self.type_col}")

            # Clean percentage-like columns
            self._clean_percentage_columns()

            # Extract entry trades (the core change)
            self._extract_entry_trades()

            # Validate data quality (entry-based)
            self._validate_data_quality()

        except Exception as e:
            msg = f"❌ Data loading failed: {e}"
            print(msg)
            self.validation_issues.append(msg)
            raise

    def _find_key_column(self, patterns, column_name):
        if self.df is None:
            raise ValueError('DataFrame is None')
        def normalize(s):
            return str(s).strip().lower().replace(' ', '').replace('_', '').replace('-', '').replace('#', '').replace('&', '')
        norm_cols = {normalize(c): c for c in self.df.columns}
        for pat in patterns:
            n = normalize(pat)
            for nc, orig in norm_cols.items():
                if n in nc:
                    return orig
        print(f"⚠️ Could not find {column_name}. Available columns: {self.df.columns.tolist()}")
        return None

    def _clean_percentage_columns(self):
        percentage_cols = [self.runup_col, self.drawdown_col, self.pnl_col]
        for col in percentage_cols:
            if col is None or col not in self.df.columns:
                continue
            self.df[col] = self.df[col].astype(str).str.replace('%', '').str.replace(',', '').str.replace('$', '')
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
            null_count = self.df[col].isnull().sum()
            if null_count > 0:
                print(f"   ⚠️ {null_count} null values in {col} (will be excluded)")

    def _extract_entry_trades(self):
        if self.df is None:
            raise ValueError('DataFrame is None')
        if self.type_col is None:
            raise ValueError('Type column not found')

        # Ensure strings
        self.df[self.type_col] = self.df[self.type_col].astype(str)
        # Prefer explicit 'entry' markers; include 'buy'/'open' but avoid generic 'long'/'short'
        entry_patterns = [r'\bentry\b', r'\bbuy\b', r'\bopen\b']
        mask = pd.Series(False, index=self.df.index)
        for p in entry_patterns:
            mask = mask | self.df[self.type_col].str.lower().str.contains(p, regex=True, na=False)

        self.entry_trades = self.df[mask].copy()
        key_cols = [self.runup_col, self.drawdown_col, self.pnl_col]
        before = len(self.entry_trades)
        self.entry_trades = self.entry_trades.dropna(subset=key_cols)
        after = len(self.entry_trades)
        if before != after:
            print(f"🧹 Removed {before-after} rows with missing key data (entry extractor)")
        print(f"📈 Extracted {len(self.entry_trades)} entry trades for analysis")

        if len(self.entry_trades) == 0:
            raise ValueError('No entry trades found for analysis')

    def _extract_exit_trades(self):
        # Keep original exit extractor for backward compatibility
        if self.df is None:
            raise ValueError('DataFrame is None')
        if self.type_col is None:
            raise ValueError('Type column not found')
        self.df[self.type_col] = self.df[self.type_col].astype(str)
        # Explicit exit markers only
        exit_patterns = [r'\bexit\b', r'\bclose\b', r'\bsell\b']
        mask = pd.Series(False, index=self.df.index)
        for p in exit_patterns:
            mask = mask | self.df[self.type_col].str.lower().str.contains(p, regex=True, na=False)
        self.exit_trades = self.df[mask].copy()
        key_cols = [self.runup_col, self.drawdown_col, self.pnl_col]
        self.exit_trades = self.exit_trades.dropna(subset=key_cols)
        print(f"📈 (compat) Extracted {len(self.exit_trades)} exit trades")

    def _validate_data_quality(self):
        if self.entry_trades is None:
            raise ValueError('entry_trades not ready')
        total = len(self.entry_trades)
        if total < 50:
            issue = f"Small sample size: {total} trades (recommend >100)"
            print(f"⚠️ {issue}")
            self.validation_issues.append(issue)

        runup_vals = self.entry_trades[self.runup_col].abs()
        drawdown_vals = self.entry_trades[self.drawdown_col].abs()
        extreme_runups = (runup_vals > 100).sum()
        extreme_drawdowns = (drawdown_vals > 100).sum()
        if extreme_runups > 0:
            issue = f"{extreme_runups} trades with extreme run-ups (>100%)"
            print(f"⚠️ {issue}")
            self.validation_issues.append(issue)
        if extreme_drawdowns > 0:
            issue = f"{extreme_drawdowns} trades with extreme drawdowns (>100%)"
            print(f"⚠️ {issue}")
            self.validation_issues.append(issue)

        wins = (self.entry_trades[self.pnl_col] > 0).sum()
        win_rate = wins / total * 100 if total > 0 else 0
        print(f"📊 Data Quality: total_entries={total}, win_rate={win_rate:.1f}%")

    def analyze_price_movement_patterns(self):
        """
        Core analysis using entry-based run-up/drawdown statistics.
        Computes TP1/TP2/TP3 from run-up percentiles (p50/p75/p90).
        """
        if self.entry_trades is None or len(self.entry_trades) == 0:
            raise ValueError('No entry trades for analysis')

        print('\n🔍 ANALYZING PRICE MOVEMENT PATTERNS (ENTRY-BASED)')

        runup_abs = self.entry_trades[self.runup_col].abs()
        drawdown_abs = self.entry_trades[self.drawdown_col].abs()
        pnl_values = self.entry_trades[self.pnl_col]

        stats = self._analyze_statistical_distributions(runup_abs, drawdown_abs, pnl_values)
        behaviors = self._classify_trading_behaviors(runup_abs, drawdown_abs, pnl_values)
        scenarios = self._map_risk_reward_scenarios(runup_abs, drawdown_abs, pnl_values)
        ranges = self._calculate_smart_ranges(stats, behaviors, scenarios)

        # Compute TP levels from runup percentiles using helper
        tp1, tp2, tp3 = self._suggest_tp_levels(stats)

        # Calculate TP reach rates: percent of trades whose runup >= TP1/2/3
        tp_reach_rates = {}
        total_trades = len(runup_abs)
        for label, tp in zip(['TP1', 'TP2', 'TP3'], [tp1, tp2, tp3]):
            if total_trades > 0:
                reach_count = (runup_abs >= tp).sum()
                tp_reach_rates[label] = round(reach_count / total_trades * 100, 2)
            else:
                tp_reach_rates[label] = 0.0

        # Keep TP levels in range_analysis
        self.range_analysis = {
            'statistics': stats,
            'behaviors': behaviors,
            'scenarios': scenarios,
            'recommended_ranges': ranges,
            'tp_levels': {'TP1': round(float(tp1), 3), 'TP2': round(float(tp2), 3), 'TP3': round(float(tp3), 3)},
            'tp_reach_rates': tp_reach_rates,
            'warnings': list(self._analysis_warnings)
        }

        print(f"\n🎯 Suggested TP levels (from entry-based runup percentiles - p50/p75/p90): TP1={self.range_analysis['tp_levels']['TP1']}% (p50), TP2={self.range_analysis['tp_levels']['TP2']}% (p75), TP3={self.range_analysis['tp_levels']['TP3']}% (p90)")
        print(f"   TP Reach Rates: TP1={tp_reach_rates['TP1']}%, TP2={tp_reach_rates['TP2']}%, TP3={tp_reach_rates['TP3']}%")

        return self.range_analysis

    def _analyze_statistical_distributions(self, runup_abs, drawdown_abs, pnl_values):
        print('\n📊 STATISTICAL DISTRIBUTION ANALYSIS (ENTRY-BASED)')
        percentiles = [5,10,25,50,75,90,95]
        runup_pct = {f'p{p}': runup_abs.quantile(p/100) for p in percentiles}
        drawdown_pct = {f'p{p}': drawdown_abs.quantile(p/100) for p in percentiles}

        stats = {
            'runup': {
                'mean': runup_abs.mean(),
                'median': runup_abs.median(),
                'std': runup_abs.std(),
                'max': runup_abs.max(),
                'percentiles': runup_pct
            },
            'drawdown': {
                'mean': drawdown_abs.mean(),
                'median': drawdown_abs.median(),
                'std': drawdown_abs.std(),
                'max': drawdown_abs.max(),
                'percentiles': drawdown_pct
            },
            'pnl': {
                'mean': pnl_values.mean(),
                'median': pnl_values.median(),
                'positive_rate': (pnl_values>0).mean()*100
            }
        }

        print(f"   Runup median={stats['runup']['median']:.2f}%, p75={stats['runup']['percentiles']['p75']:.2f}%")
        print(f"   Drawdown median={stats['drawdown']['median']:.2f}%")
        return stats

    def _suggest_tp_levels(self, stats):
        """
        Suggest TP1/TP2/TP3 from run-up percentiles (p50, p75, p90).
        Returns numeric values (percent).
        """
        runup_pct = stats['runup']['percentiles']
        # Extract raw percentiles
        p50 = float(runup_pct.get('p50', stats['runup']['median']))
        p75 = float(runup_pct.get('p75', p50 * 1.8))
        p90 = float(runup_pct.get('p90', p75 * 1.5))

        # Floors/caps as requested
        TP1_FLOOR = 2.0
        TP2_FLOOR = 4.0
        TP3_FLOOR = 6.0

        # Apply floors for TP1 and TP2
        tp1 = max(p50, TP1_FLOOR)
        if tp1 != p50:
            print(f"TP1 floored at {TP1_FLOOR}% (original p50={p50:.2f}%)")

        tp2 = max(p75, TP2_FLOOR)
        if tp2 != p75:
            print(f"TP2 floored at {TP2_FLOOR}% (original p75={p75:.2f}%)")

        # TP3: cannot exceed 2x TP2, and must be at least TP3_FLOOR
        tp3_capped = min(p90, tp2 * 2)
        if tp3_capped != p90:
            print(f"TP3 capped to 2x TP2: p90={p90:.2f}% -> capped to {tp2*2:.2f}%")

        tp3 = max(tp3_capped, TP3_FLOOR)
        if tp3 != tp3_capped:
            print(f"TP3 floored at {TP3_FLOOR}% (after cap, value={tp3:.2f}%)")

        return float(tp1), float(tp2), float(tp3)

    def _classify_trading_behaviors(self, runup_abs, drawdown_abs, pnl_values):
        print('\n🎭 TRADING BEHAVIOR CLASSIFICATION (ENTRY-BASED)')
        behaviors = {}
        total = len(runup_abs)
        trending = (runup_abs > runup_abs.quantile(0.75)) & (pnl_values > 0)
        behaviors['trending_winners'] = {
            'count': int(trending.sum()),
            'percentage': float(trending.sum()/total*100) if total>0 else 0,
            'avg_runup': float(runup_abs[trending].mean()) if trending.sum()>0 else 0,
            'avg_drawdown': float(drawdown_abs[trending].mean()) if trending.sum()>0 else 0,
            'description': 'Strong trends with good profits - consider wider TS'
        }
        volatile = (drawdown_abs > drawdown_abs.quantile(0.75)) & (pnl_values > 0)
        behaviors['volatile_winners'] = {
            'count': int(volatile.sum()),
            'percentage': float(volatile.sum()/total*100) if total>0 else 0,
            'avg_runup': float(runup_abs[volatile].mean()) if volatile.sum()>0 else 0,
            'avg_drawdown': float(drawdown_abs[volatile].mean()) if volatile.sum()>0 else 0,
            'description': 'High volatility but profitable - wider SL ranges'
        }
        quick_losers = (drawdown_abs > drawdown_abs.quantile(0.6)) & (runup_abs < runup_abs.quantile(0.4)) & (pnl_values<=0)
        behaviors['quick_losers'] = {
            'count': int(quick_losers.sum()),
            'percentage': float(quick_losers.sum()/total*100) if total>0 else 0,
            'avg_runup': float(runup_abs[quick_losers].mean()) if quick_losers.sum()>0 else 0,
            'avg_drawdown': float(drawdown_abs[quick_losers].mean()) if quick_losers.sum()>0 else 0,
            'description': 'Fast losses - SL should catch these early'
        }
        near_miss = (runup_abs > runup_abs.quantile(0.5)) & (pnl_values<=0)
        behaviors['near_miss_losers'] = {
            'count': int(near_miss.sum()),
            'percentage': float(near_miss.sum()/total*100) if total>0 else 0,
            'avg_runup': float(runup_abs[near_miss].mean()) if near_miss.sum()>0 else 0,
            'avg_drawdown': float(drawdown_abs[near_miss].mean()) if near_miss.sum()>0 else 0,
            'description': 'Had potential but failed - BE/TS could help'
        }

        for name,data in behaviors.items():
            if data['count']>0:
                print(f"{name.upper()}: {data['count']} trades ({data['percentage']:.1f}%) - {data['description']}")
        return behaviors

    def _map_risk_reward_scenarios(self, runup_abs, drawdown_abs, pnl_values):
        print('\n🎯 RISK-REWARD SCENARIO MAPPING (ENTRY-BASED)')
        scenarios = {}
        scenarios['conservative'] = {
            'trade_count': int((drawdown_abs <= drawdown_abs.quantile(0.6)).sum()),
            'percentage': float((drawdown_abs <= drawdown_abs.quantile(0.6)).sum()/len(drawdown_abs)*100),
            'target_sl_max': float(drawdown_abs[drawdown_abs <= drawdown_abs.quantile(0.6)].quantile(0.8)),
            'target_be_range': float(runup_abs[runup_abs <= runup_abs.quantile(0.6)].quantile(0.3)),
            'target_ts_trigger': float(runup_abs[runup_abs <= runup_abs.quantile(0.6)].quantile(0.5)),
            'description': 'Lower risk tolerance - tight parameters'
        }
        balanced_mask = (drawdown_abs > drawdown_abs.quantile(0.3)) & (drawdown_abs <= drawdown_abs.quantile(0.8))
        scenarios['balanced'] = {
            'trade_count': int(balanced_mask.sum()),
            'percentage': float(balanced_mask.sum()/len(drawdown_abs)*100),
            'target_sl_max': float(drawdown_abs[balanced_mask].quantile(0.85)),
            'target_be_range': float(runup_abs[balanced_mask].quantile(0.4)),
            'target_ts_trigger': float(runup_abs[balanced_mask].quantile(0.6)),
            'description': 'Standard risk-reward balance'
        }
        aggressive_mask = drawdown_abs > drawdown_abs.quantile(0.7)
        scenarios['aggressive'] = {
            'trade_count': int(aggressive_mask.sum()),
            'percentage': float(aggressive_mask.sum()/len(drawdown_abs)*100),
            'target_sl_max': float(drawdown_abs[aggressive_mask].quantile(0.9)),
            'target_be_range': float(runup_abs[aggressive_mask].quantile(0.25)),
            'target_ts_trigger': float(runup_abs[aggressive_mask].quantile(0.75)),
            'description': 'Higher risk for higher potential reward'
        }
        for name,data in scenarios.items():
            print(f"{name.upper()} SCENARIO: {data['trade_count']} trades ({data['percentage']:.1f}%)")
        return scenarios

    def _calculate_smart_ranges(self, stats, behaviors, scenarios):
        print('\n🎯 CALCULATING SMART PARAMETER RANGES')
        runup_stats = stats['runup']
        drawdown_stats = stats['drawdown']

        # Helper robust_range (keeps original spirit)
        def robust_range(min_val, max_val, min_step, max_step, desired_n=5, hard_min=None, hard_max=None, param_name=''):
            if hard_min is not None:
                min_val = max(min_val, hard_min)
            if hard_max is not None:
                max_val = min(max_val, hard_max)
            n = max(3, min(desired_n, int((max_val - min_val) / min_step) + 1))
            if n < 3:
                n = 3
            step = (max_val - min_val) / (n - 1) if n > 1 else min_step
            step = max(min_step, min(step, max_step))
            n = int((max_val - min_val) / step) + 1
            if n > 10:
                n = 10
                step = (max_val - min_val) / (n - 1) if n > 1 else min_step
            warnings = []
            if max_val - min_val < min_step:
                warnings.append(f"{param_name}: Range too narrow (min={min_val:.2f}, max={max_val:.2f})")
            return {'min': round(min_val,3), 'max': round(max_val,3), 'step': round(step,3)}

        # Outlier exclusion
        dd_p5 = drawdown_stats['percentiles']['p5']
        dd_p95 = drawdown_stats['percentiles']['p95']
        ru_p5 = runup_stats['percentiles']['p5']
        ru_p95 = runup_stats['percentiles']['p95']

        # Capture original candidates so we can record when we apply floors
        sl_min_cand = {
            'conservative': drawdown_stats['percentiles']['p10'],
            'balanced': drawdown_stats['percentiles']['p50'],
            'aggressive': drawdown_stats['percentiles']['p75']
        }
        sl_ranges = {
            'conservative': robust_range(sl_min_cand['conservative'], drawdown_stats['percentiles']['p50'], 0.2, 2.0, 5, 0.5, 50.0, 'SL-Conservative'),
            'balanced': robust_range(sl_min_cand['balanced'], drawdown_stats['percentiles']['p75'], 0.2, 2.0, 5, 0.5, 50.0, 'SL-Balanced'),
            'aggressive': robust_range(sl_min_cand['aggressive'], drawdown_stats['percentiles']['p95'], 0.5, 5.0, 5, 0.5, 50.0, 'SL-Aggressive')
        }

        be_min_cand = {
            'conservative': runup_stats['percentiles']['p10']*0.5,
            'balanced': runup_stats['percentiles']['p25']*0.8,
            'aggressive': runup_stats['percentiles']['p50']*0.9
        }
        be_ranges = {
            'conservative': robust_range(be_min_cand['conservative'], runup_stats['percentiles']['p25']*0.8, 0.05, 1.0, 5, 0.5, 10.0,'BE-Conservative'),
            'balanced': robust_range(be_min_cand['balanced'], runup_stats['percentiles']['p50']*0.9, 0.05, 1.0, 5, 0.5, 10.0,'BE-Balanced'),
            'aggressive': robust_range(be_min_cand['aggressive'], runup_stats['percentiles']['p95']*0.95, 0.1, 2.0, 5, 0.5, 10.0,'BE-Aggressive')
        }

        # Enforce a practical floor for TS trigger to avoid tiny, impractical trailing-stop triggers
        ts_min_cand = {
            'conservative': runup_stats['percentiles']['p10'],
            'balanced': runup_stats['percentiles']['p25'],
            'aggressive': runup_stats['percentiles']['p75']
        }
        ts_ranges = {
            'conservative': robust_range(ts_min_cand['conservative'], runup_stats['percentiles']['p50'], 0.1, 2.0, 5, TS_TRIGGER_MIN, 20.0,'TS-Conservative'),
            'balanced': robust_range(ts_min_cand['balanced'], runup_stats['percentiles']['p75'], 0.1, 2.0, 5, TS_TRIGGER_MIN, 20.0,'TS-Balanced'),
            'aggressive': robust_range(ts_min_cand['aggressive'], runup_stats['percentiles']['p95'], 0.2, 5.0, 5, TS_TRIGGER_MIN, 20.0,'TS-Aggressive')
        }

        ru_std = runup_stats['std']
        ru_mean = runup_stats['mean']
        volatility_factor = ru_std / ru_mean if ru_mean > 0 else 0.5
        # Base calculation for TS step - ensure a realistic floor
        ts_step_min = max(TS_STEP_FLOOR, ru_p5 * 0.2)
        ts_step_max = max(ts_step_min * 2, runup_stats['percentiles']['p25'] * 0.3)

        ts_step_min_cand = ts_step_min
        ts_step_ranges = {
            'conservative': robust_range(ts_step_min_cand, ts_step_max, TS_STEP_FLOOR, 1.0, 5, TS_STEP_FLOOR, 5.0,'TS-Step-Conservative'),
            'balanced': robust_range(ts_step_min_cand, ts_step_max * 1.5, TS_STEP_FLOOR, 1.5, 5, TS_STEP_FLOOR, 5.0,'TS-Step-Balanced'),
            'aggressive': robust_range(ts_step_min_cand, min(5.0, ts_step_max * 2), TS_STEP_FLOOR, 2.0, 5, TS_STEP_FLOOR, 5.0,'TS-Step-Aggressive')
        }

        # Sanity checks: ensure ranges and steps are reasonable
        for k, r in ts_step_ranges.items():
            minv, maxv, stepv = r['min'], r['max'], r['step']
            # If max <= min, extend max
            if maxv - minv <= 0:
                maxv = minv + TS_STEP_FLOOR
                r['max'] = round(maxv, 3)
            # If step is larger than range, reduce step to be sensible
            if stepv > (r['max'] - r['min']):
                new_step = max(TS_STEP_FLOOR, min((r['max'] - r['min']) / 2 if (r['max'] - r['min'])>0 else TS_STEP_FLOOR, r['max'] - r['min']))
                r['step'] = round(new_step, 3)

        # Enforce floors across returned ranges and log when floors applied
        # SL floor: 0.5%
        SL_FLOOR = 0.5
        for strat, r in sl_ranges.items():
            # if original candidate was below floor, warn
            if sl_min_cand.get(strat, 0) < SL_FLOOR:
                old = r['min']
                r['min'] = round(SL_FLOOR, 3)
                # ensure max >= min
                if r['max'] < r['min']:
                    r['max'] = round(r['min'] + r['step'], 3)
                msg = f"SL {strat}: min {old} -> {r['min']} (floor {SL_FLOOR}% applied)"
                print(msg)
                # Human-readable
                self._analysis_warnings.append(msg)
                # Structured for machine consumption
                try:
                    self._analysis_warnings.append({'code': SL_FLOOR, 'message': msg, 'value': float(r['min']), 'human': msg})
                except Exception:
                    self._analysis_warnings.append({'code': SL_FLOOR, 'message': msg, 'value': None, 'human': msg})

        # BE floor: 0.5%
        BE_FLOOR = 0.5
        for strat, r in be_ranges.items():
            if be_min_cand.get(strat, 0) < BE_FLOOR:
                old = r['min']
                r['min'] = round(BE_FLOOR, 3)
                if r['max'] < r['min']:
                    r['max'] = round(r['min'] + r['step'], 3)
                msg = f"BE {strat}: min {old} -> {r['min']} (floor {BE_FLOOR}% applied)"
                print(msg)
                # Human-readable
                self._analysis_warnings.append(msg)
                # Structured
                try:
                    self._analysis_warnings.append({'code': BE_FLOOR, 'message': msg, 'value': float(r['min']), 'human': msg})
                except Exception:
                    self._analysis_warnings.append({'code': BE_FLOOR, 'message': msg, 'value': None, 'human': msg})

        # TS trigger floor already applied via robust_range hard_min but double-check and log
        for strat, r in ts_ranges.items():
            if ts_min_cand.get(strat, 0) < TS_TRIGGER_MIN:
                old = r['min']
                r['min'] = round(TS_TRIGGER_MIN, 3)
                if r['max'] < r['min']:
                    r['max'] = round(r['min'] + r['step'], 3)
                msg = f"TS {strat}: min {old} -> {r['min']} (floor {TS_TRIGGER_MIN}% applied)"
                print(msg)
                # Human-readable
                self._analysis_warnings.append(msg)
                # Structured
                try:
                    self._analysis_warnings.append({'code': TS_TRIGGER_FLOOR, 'message': msg, 'value': float(r['min']), 'human': msg})
                except Exception:
                    self._analysis_warnings.append({'code': TS_TRIGGER_FLOOR, 'message': msg, 'value': None, 'human': msg})
                # Also add a canonical machine-readable warning string for legacy tests
                try:
                    canonical = f"ts_trig raised to {r['min']}% (floor applied)"
                    self._analysis_warnings.append(canonical)
                    # And a structured canonical entry
                    self._analysis_warnings.append({'code': TS_FLOOR_CANONICAL, 'message': canonical, 'value': float(r['min']), 'human': canonical})
                except Exception:
                    self._analysis_warnings.append("ts_trig raised to floor (value unknown)")

        # TS step floor already used, ensure and log
        for strat, r in ts_step_ranges.items():
            if ts_step_min_cand < TS_STEP_FLOOR:
                old = r['min']
                r['min'] = round(TS_STEP_FLOOR, 3)
                if r['max'] < r['min']:
                    r['max'] = round(r['min'] + r['step'], 3)
                if r['step'] < TS_STEP_FLOOR:
                    r['step'] = round(TS_STEP_FLOOR, 3)
                msg = f"TS-Step {strat}: min {old} -> {r['min']} (floor {TS_STEP_FLOOR}% applied)"
                print(msg)
                # Human-readable
                self._analysis_warnings.append(msg)
                # Structured
                try:
                    self._analysis_warnings.append({'code': TS_STEP_FLOOR, 'message': msg, 'value': float(r['min']), 'human': msg})
                except Exception:
                    self._analysis_warnings.append({'code': TS_STEP_FLOOR, 'message': msg, 'value': None, 'human': msg})

        efficiency = self._calculate_efficiency_gains(sl_ranges, be_ranges, ts_ranges, ts_step_ranges)

        print('\n📋 SMART PARAMETER RANGES SUMMARY:')
        for strat, r in sl_ranges.items():
            print(f"   SL {strat}: {r['min']} - {r['max']} (step {r['step']})")
        for strat, r in be_ranges.items():
            print(f"   BE {strat}: {r['min']} - {r['max']} (step {r['step']})")
        for strat, r in ts_ranges.items():
            # indicate when floor was applied
            applied_min = max(r['min'], TS_TRIGGER_MIN)
            if applied_min != r['min']:
                print(f"   TS {strat}: {r['min']} -> {applied_min} (floor {TS_TRIGGER_MIN} applied) - {r['max']} (step {r['step']})")
            else:
                print(f"   TS {strat}: {r['min']} - {r['max']} (step {r['step']})")

        return {
            'sl_ranges': sl_ranges,
            'be_ranges': be_ranges,
            'ts_ranges': ts_ranges,
            'ts_step_ranges': ts_step_ranges,
            'efficiency_analysis': efficiency
        }

    def _calculate_efficiency_gains(self, sl_ranges, be_ranges, ts_ranges, ts_step_ranges):
        print('\n⚡ EFFICIENCY ANALYSIS')
        combinations = {}
        for strat in ['conservative','balanced','aggressive']:
            sl_count = int((sl_ranges[strat]['max'] - sl_ranges[strat]['min']) / sl_ranges[strat]['step']) + 1
            be_count = int((be_ranges[strat]['max'] - be_ranges[strat]['min']) / be_ranges[strat]['step']) + 1
            ts_count = int((ts_ranges[strat]['max'] - ts_ranges[strat]['min']) / ts_ranges[strat]['step']) + 1
            ts_step_count = int((ts_step_ranges[strat]['max'] - ts_step_ranges[strat]['min']) / ts_step_ranges[strat]['step']) + 1
            combinations[strat] = sl_count * be_count * ts_count * ts_step_count
        typical_blind = 20*10*8*6
        total = sum(combinations.values())
        efficiency_gain = typical_blind / total if total>0 else 0
        print(f"   Efficiency gain approx: {efficiency_gain:.1f}x")
        return {'smart_combinations': combinations, 'total_smart': total, 'typical_blind': typical_blind, 'efficiency_gain': efficiency_gain}

    def generate_final_recommendations(self):
        """Generate final recommendations (ENTRY-BASED).

        Note: Ranges here are derived from Entry-based statistics and are suitable
        as input to Optuna/grid search.
        """
        if not self.range_analysis:
            self.analyze_price_movement_patterns()

        rec = self.range_analysis['recommended_ranges']
        tp_levels = self.range_analysis.get('tp_levels', {})
        tp_reach_rates = self.range_analysis.get('tp_reach_rates', {})
        recommended_strategy = 'balanced'
        sl = rec['sl_ranges'][recommended_strategy]
        be = rec['be_ranges'][recommended_strategy]
        ts = rec['ts_ranges'][recommended_strategy]
        ts_step = rec['ts_step_ranges'][recommended_strategy]

        print('\n🏆 FINAL RECOMMENDATIONS (ENTRY-BASED)')
        print(f"Based on {len(self.entry_trades)} entry trades")
        print(f"TP suggestions: TP1={tp_levels.get('TP1')}%, TP2={tp_levels.get('TP2')}%, TP3={tp_levels.get('TP3')}%")
        print(f"TP reach rates: TP1={tp_reach_rates.get('TP1')}%, TP2={tp_reach_rates.get('TP2')}%, TP3={tp_reach_rates.get('TP3')}%")

        if self.validation_issues:
            print('\n⚠️ Data quality notes:')
            for i in self.validation_issues:
                print('  -', i)

        return {
            'recommended_strategy': recommended_strategy,
            'parameter_ranges': {
                'sl': sl, 'be': be, 'ts_trigger': ts, 'ts_step': ts_step
            },
            'tp_levels': tp_levels,
            'tp_reach_rates': tp_reach_rates,
            'data_quality_issues': self.validation_issues,
            'total_trades_analyzed': len(self.entry_trades)
        }

    def export_ranges(self):
        """Return JSON-friendly ranges including TP levels for Optuna/grid loading."""
        if not self.range_analysis:
            self.analyze_price_movement_patterns()
        rec = self.range_analysis['recommended_ranges']
        tp = self.range_analysis.get('tp_levels', {'TP1':None,'TP2':None,'TP3':None})
        # Convert numpy types to native Python floats for JSON friendliness
        def as_py(r):
            return {
                'min': float(r['min']),
                'max': float(r['max']),
                'step': float(r['step'])
            }

        tp_clean = {}
        for k, v in tp.items():
            try:
                tp_clean[k] = float(v) if v is not None else None
            except Exception:
                tp_clean[k] = None

        out = {
            'SL': as_py(rec['sl_ranges']['balanced']),
            'BE': as_py(rec['be_ranges']['balanced']),
            'TS_trigger': as_py(rec['ts_ranges']['balanced']),
            'TS_step': as_py(rec['ts_step_ranges']['balanced']),
            'TP_levels': tp_clean
        }
        return out


if __name__ == '__main__':
    # Minimal demo runner for local testing
    try:
        demo_file = '60-tradelist-LONGSHORT.csv'
        finder = SmartRangeFinder(demo_file)
        analysis = finder.analyze_price_movement_patterns()
        recommendations = finder.generate_final_recommendations()
        print('\nExported ranges:')
        print(finder.export_ranges())
    except Exception as e:
        print(f"Demo run failed: {e}")
