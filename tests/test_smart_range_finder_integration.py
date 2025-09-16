import json
from pathlib import Path

import pytest

from smart_range_finder import SmartRangeFinder


def test_smart_range_finder_runs_and_returns_expected_keys():
    repo_root = Path(__file__).resolve().parents[1]
    sample = repo_root / 'sample_tradelist.csv'
    assert sample.exists(), f"Sample tradelist missing: {sample}"

    srf = SmartRangeFinder(str(sample))
    analysis = srf.analyze_price_movement_patterns()

    # Basic shape assertions
    assert isinstance(analysis, dict)
    assert 'recommended_ranges' in analysis
    assert 'tp_levels' in analysis

    tp = analysis['tp_levels']
    assert all(k in tp for k in ('TP1', 'TP2', 'TP3'))
    assert float(tp['TP1']) > 0
    assert float(tp['TP2']) >= float(tp['TP1'])
    assert float(tp['TP3']) >= float(tp['TP2'])

    # Export to temp json to mimic ver_final_AI behavior
    out = repo_root / 'tests' / 'tmp_range_analysis.json'
    out.write_text(json.dumps(analysis, indent=2))
    assert out.exists()
