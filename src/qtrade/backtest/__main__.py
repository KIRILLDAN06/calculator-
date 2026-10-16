"""Run one backtest from a config file.

    python -m qtrade.backtest --config configs/backtest.yaml [--strategy orb] [--start ...] [--end ...]

Writes metrics.json, trades.csv and equity.csv to ``--out`` (default runs/<strategy>/).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from qtrade.backtest.engine import run_backtest
from qtrade.backtest.metrics import compute_metrics
from qtrade.config import ConfigError, load_config
from qtrade.data.bars import timeframe_minutes
from qtrade.data.pipeline import load_bars
from qtrade.strategies import make_strategy


def run_from_config(cfg: dict, strategy_name: str | None = None, start: str | None = None,
                    end: str | None = None):
    name = strategy_name or cfg["strategy"]["name"]
    params = cfg["strategy"].get("params", {}) if name == cfg["strategy"]["name"] else {}
    strat = make_strategy(name, params)
    bt = cfg.get("backtest", {})
    start = start or bt.get("start")
    end = end or bt.get("end")
    warm = pd.Timedelta(minutes=timeframe_minutes(strat.timeframe) * strat.warmup_bars)
    load_start = None if start is None else (pd.Timestamp(start, tz="UTC") - warm).isoformat()
    bars = load_bars(strat.timeframe, cfg["data"]["clean_dir"], start=load_start, end=end)
    sig = strat.generate(bars)
    res = run_backtest(bars, sig, cfg, start=start, end=end, strategy_name=strat.describe(),
                       timeframe=strat.timeframe)
    return res, compute_metrics(res)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--strategy")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2
    res, m = run_from_config(cfg, args.strategy, args.start, args.end)
    out = Path(args.out or f"runs/{args.strategy or cfg['strategy']['name']}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(m, indent=2, default=str) + "\n")
    res.trades.to_csv(out / "trades.csv", index=False)
    res.equity.to_csv(out / "equity.csv")
    keys = ["strategy", "start", "end", "n_trades", "net_return", "gross_return", "total_costs", "sharpe",
            "max_drawdown", "win_rate", "profit_factor", "expectancy_r"]
    for k in keys:
        v = m[k]
        print(f"{k:>16}: {v:.4f}" if isinstance(v, float) else f"{k:>16}: {v}")
    print(f"outputs written to {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
