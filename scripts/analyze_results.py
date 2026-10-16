#!/usr/bin/env python
"""Descriptive analysis of the experiment outputs -> research/results_tables.md.

Nothing here feeds back into strategy selection (pre-registered criteria decide):
* summary tables per stage and cost scenario,
* break-even round-trip cost per candidate (gross expectancy / traded notional),
* regime breakdown of test-period daily returns (BTC trend and volatility regimes,
  each day classified with information available at the previous day's close).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qtrade.backtest.metrics import daily_returns  # noqa: E402
from qtrade.experiments import CANDIDATES, SPLITS, bars_for, run_config  # noqa: E402

EXP = ROOT / "runs" / "experiments"


def fmt(x, pct=False, nd=2):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "n/a"
    return f"{x:+.1%}" if pct else f"{x:.{nd}f}"


def stage_table(stage: str) -> list[str]:
    p = EXP / stage / "summary.json"
    if not p.exists():
        return [f"_{stage}: not run_"]
    d = json.loads(p.read_text())
    bh = d["benchmarks"]["buy_and_hold"]
    lines = [f"**{stage} ({d['start']} → {d['end']})** — buy-and-hold: net {fmt(bh['net_return'], True)}, "
             f"Sharpe {fmt(bh['sharpe'])}, max DD {fmt(bh['max_drawdown'], True)}", "",
             "| Cand. | Strategy | Trades | Net (baseline) | Sharpe | Max DD | Win % | PF | Exp. R | Net (stress) | "
             "Net (optimistic) | Net (zero cost) | Sharpe (zero cost) | Bootstrap 90% CI (Sharpe) |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for cid, c in d["candidates"].items():
        b, s, o, g = (c["baseline"][k] for k in ("baseline", "stress", "optimistic", "gross"))
        bs = c["bootstrap"]
        lines.append(
            f"| {cid} | {c['strategy']} | {b['n_trades']} | {fmt(b['net_return'], True)} | {fmt(b['sharpe'])} | "
            f"{fmt(b['max_drawdown'], True)} | {fmt(b['win_rate'] * 100 if b['win_rate'] == b['win_rate'] else None, nd=0)} | "
            f"{fmt(b['profit_factor'])} | {fmt(b['expectancy_r'])} | {fmt(s['net_return'], True)} | "
            f"{fmt(o['net_return'], True)} | {fmt(g['net_return'], True)} | {fmt(g['sharpe'])} | "
            f"[{fmt(bs['lo'])}, {fmt(bs['hi'])}] |")
    return lines


def breakeven_table() -> list[str]:
    lines = ["| Cand. | Period | Trades (zero cost) | Gross expectancy per trade (bp of notional) | "
             "95% CI (bp) | Modelled baseline round trip (bp) |", "|---|---|---|---|---|---|"]
    for cand in CANDIDATES:
        for stage in ("dev", "val", "test"):
            if not (EXP / stage / "summary.json").exists():
                continue
            start, end = SPLITS[stage]
            res, _ = run_config(cand.strategy, cand.base, start, end, "gross")
            t = res.trades
            if len(t) == 0:
                continue
            bp = (t["gross_pnl"] / (t["qty"] * t["entry_ref"]) * 1e4).to_numpy()
            se = bp.std(ddof=1) / math.sqrt(len(bp)) if len(bp) > 1 else float("nan")
            lines.append(f"| {cand.cid} | {stage} | {len(bp)} | {bp.mean():.1f} | "
                         f"[{bp.mean() - 1.96 * se:.1f}, {bp.mean() + 1.96 * se:.1f}] | ~86 (taker) |")
    return lines


def regime_table() -> list[str]:
    if not (EXP / "test" / "summary.json").exists():
        return ["_test stage not run_"]
    start, end = SPLITS["test"]
    daily = bars_for("1D")
    close = daily["close"]
    sma200 = close.rolling(200).mean()
    vol20 = np.log(close).diff().rolling(20).std()
    dev_med = vol20[(vol20.index >= SPLITS["dev"][0]) & (vol20.index < SPLITS["dev"][1])].median()
    trend = (close > sma200).shift(1)              # known at the previous close
    hivol = (vol20 > dev_med).shift(1)
    lines = ["| Cand. | Cost | Uptrend days: mean daily ret (bp) | Downtrend days | High-vol days | Low-vol days |",
             "|---|---|---|---|---|---|"]
    for cand in CANDIDATES:
        for cost in ("baseline", "gross"):
            res, _ = run_config(cand.strategy, cand.base, start, end, cost)
            dr = daily_returns(res.equity, res.initial_equity)
            dr.index = dr.index.normalize()
            df = pd.DataFrame({"r": dr, "up": trend.reindex(dr.index), "hv": hivol.reindex(dr.index)}).dropna()
            cells = [f"{df.loc[df.up.astype(bool), 'r'].mean() * 1e4:.1f}",
                     f"{df.loc[~df.up.astype(bool), 'r'].mean() * 1e4:.1f}",
                     f"{df.loc[df.hv.astype(bool), 'r'].mean() * 1e4:.1f}",
                     f"{df.loc[~df.hv.astype(bool), 'r'].mean() * 1e4:.1f}"]
            lines.append(f"| {cand.cid} | {cost} | " + " | ".join(cells) + " |")
    return lines


def wf_table() -> list[str]:
    p = EXP / "wf" / "summary.json"
    if not p.exists():
        return ["_walk-forward not run_"]
    d = json.loads(p.read_text())
    lines = ["| Cand. | OOS trades | OOS net (baseline costs) | OOS Sharpe | OOS max DD | Bootstrap 90% CI | Params chosen per window |",
             "|---|---|---|---|---|---|---|"]
    for cid, c in d["candidates"].items():
        picks = "; ".join(",".join(f"{k}={v}" for k, v in p["params"].items()) or "base" for p in c["picks"])
        bs = c["bootstrap"]
        lines.append(f"| {cid} | {c['oos_trades']} | {fmt(c['oos_net_return'], True)} | {fmt(c['oos_sharpe'])} | "
                     f"{fmt(c['oos_max_drawdown'], True)} | [{fmt(bs['lo'])}, {fmt(bs['hi'])}] | {picks} |")
    return lines


def test_criteria_table() -> list[str]:
    p = EXP / "test" / "summary.json"
    if not p.exists():
        return ["_test stage not run_"]
    d = json.loads(p.read_text())
    keys = list(next(iter(d["candidates"].values()))["criteria"])
    lines = ["| Cand. | " + " | ".join(k.split("_", 1)[1] for k in keys) + " | DSR | Control pct. | Verdict |",
             "|---" * (len(keys) + 4) + "|"]
    for cid, c in d["candidates"].items():
        marks = " | ".join("✅" if c["criteria"][k] else "❌" for k in keys)
        lines.append(f"| {cid} | {marks} | {fmt(c['dsr']['dsr'])} | {fmt(c['control']['percentile_of_candidate'], True)} | "
                     f"**{c['verdict']}** |")
    return lines


def main() -> int:
    out = ["# Results tables (generated by scripts/analyze_results.py)", ""]
    for stage in ("dev", "val", "test"):
        out += [f"## {stage}", ""] + stage_table(stage) + [""]
    out += ["## Walk-forward (2019-H1 … 2023-H2 OOS windows)", ""] + wf_table() + [""]
    out += ["## Test-period acceptance criteria", ""] + test_criteria_table() + [""]
    out += ["## Break-even cost analysis (zero-cost runs)", ""] + breakeven_table() + [""]
    out += ["## Test-period regime breakdown", ""] + regime_table() + [""]
    (ROOT / "research" / "results_tables.md").write_text("\n".join(out) + "\n")
    print("wrote research/results_tables.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
