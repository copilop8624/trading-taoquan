#!/usr/bin/env python3
"""Minimal demo runner for CI testing.

This script accepts `--input` and `--output` arguments, reads the JSON input,
performs a trivial analysis (counts symbols), and writes a small result and
log files into the output directory so the workflow can upload them.
"""
import argparse
import json
from pathlib import Path
from datetime import datetime
import traceback

# Try to import SmartRangeFinder module from the codebase; use it if available
try:
    import smart_range_finder as _smart_range_module
    HAS_SMART_RANGE = True
except Exception:
    _smart_range_module = None
    HAS_SMART_RANGE = False


def main():
    parser = argparse.ArgumentParser(description="Demo runner for ver_final_AI")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output directory")
    args = parser.parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.utcnow().isoformat() + "Z"

    # Read input
    data = {}
    try:
        data = json.loads(in_path.read_text())
    except Exception as e:
        (out_dir / "error.log").write_text(f"{now} ERROR reading input: {e}\n")
        raise

    # If a tradelist path was provided and SmartRangeFinder is available, use it
    params = data.get("parameters", {})
    tradelist_path = params.get("tradelist_path") or params.get("tradelist")

    if tradelist_path and _smart_range_module is not None:
        try:
            tl_path = Path(tradelist_path)
            if not tl_path.exists():
                # Try relative to repo root
                tl_path = Path.cwd() / tradelist_path

            if not tl_path.exists():
                msg = f"Tradelist file not found: {tradelist_path}"
                (out_dir / "error.log").write_text(f"{now} ERROR {msg}\n")
                raise FileNotFoundError(msg)

            # Run SmartRangeFinder analysis
            (out_dir / "run.log").write_text(f"{now} INFO Running SmartRangeFinder on {tl_path}\n")
            srf = _smart_range_module.SmartRangeFinder(str(tl_path))
            analysis = srf.analyze_price_movement_patterns()

            # Persist analysis
            (out_dir / "range_analysis.json").write_text(json.dumps(analysis, indent=2))
            (out_dir / "run.log").write_text((out_dir / "run.log").read_text() + f"{now} INFO Analysis complete\n")
            print("SmartRangeFinder analysis complete. Wrote range_analysis.json and run.log")
        except Exception as e:
            tb = traceback.format_exc()
            (out_dir / "error.log").write_text(f"{now} ERROR {e}\n{tb}\n")
            print("Analysis failed; see output/error.log for details")
            raise
    else:
        # Fallback: Trivial processing: count symbols and echo parameters
        symbols = params.get("symbols", [])
        result = {
            "timestamp": now,
            "task": data.get("task"),
            "symbols_count": len(symbols),
            "symbols": symbols,
        }

        # Write a small JSON result
        (out_dir / "result.json").write_text(json.dumps(result, indent=2))

        # Write a simple CSV derived from symbols
        csv_lines = ["symbol,processed_at"]
        for s in symbols:
            csv_lines.append(f"{s},{now}")
        (out_dir / "processed_symbols.csv").write_text("\n".join(csv_lines))

        # Write a log
        log = [f"{now} INFO Starting demo run", f"{now} INFO Processed {len(symbols)} symbols"]
        (out_dir / "run.log").write_text("\n".join(log) + "\n")

        print("Demo run complete. Wrote:")
        for p in out_dir.iterdir():
            print(" -", p.name)


if __name__ == "__main__":
    main()
