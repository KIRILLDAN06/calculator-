#!/usr/bin/env python
"""Run the pre-registered experiments. See research/backtest_methodology.md.

    python scripts/run_experiments.py --stage dev
    python scripts/run_experiments.py --stage val
    python scripts/run_experiments.py --stage wf
    python scripts/run_experiments.py --stage test        # holdout, locked
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qtrade.experiments import run_stage  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", required=True, choices=["dev", "val", "wf", "test"])
    ap.add_argument("--allow-rerun", action="store_true")
    ap.add_argument("--seeds", type=int, default=200)
    args = ap.parse_args()
    t = time.time()
    path = run_stage(args.stage, args.allow_rerun, args.seeds)
    print(f"wrote {path} in {time.time() - t:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
