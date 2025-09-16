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

    # Trivial processing: count symbols and echo parameters
    symbols = data.get("parameters", {}).get("symbols", [])
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
