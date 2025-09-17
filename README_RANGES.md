SmartRangeFinder & export_ranges() usage

This document explains the `export_ranges()` JSON-friendly output and how to use it with grid search or Optuna.

export_ranges() returns a dict with this structure:

{
  "SL": {"min": x, "max": y, "step": z},
  "BE": {"min": x, "max": y, "step": z},
  "TS_trigger": {"min": x, "max": y, "step": z},
  "TS_step": {"min": x, "max": y, "step": z},
  "TP_levels": {"TP1": value1, "TP2": value2, "TP3": value3}
}

Notes:
- All numeric values are standard Python floats (safe to JSON-serialize).
- `TP_levels` contains suggested profit-target percentages derived from run-up percentiles:
  - TP1 ≈ p50 (median)
  - TP2 ≈ p75
  - TP3 ≈ p90
- The `SL/BE/TS` ranges are suggested for three strategies (conservative/balanced/aggressive) inside the finder, but `export_ranges()` returns the balanced strategy ranges by default for direct use with Optuna/grid.

Quick usage example (Python):

from smart_range_finder import SmartRangeFinder
finder = SmartRangeFinder('tradelist.csv')
finder.analyze_price_movement_patterns()
ranges = finder.export_ranges()
# ranges is JSON-serializable; pass to Optuna or grid generation

API:
- The web endpoint `/suggest_parameters` now includes a top-level `tp_levels` field and `finder_recommendations` in the JSON response.

