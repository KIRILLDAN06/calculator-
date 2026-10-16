"""Pre-registered experiment runner (see research/backtest_methodology.md).

    python scripts/run_experiments.py --stage dev     # development period + grid sensitivity
    python scripts/run_experiments.py --stage val     # validation period (baselines)
    python scripts/run_experiments.py --stage wf      # walk-forward 2017-2023 (never touches test)
    python scripts/run_experiments.py --stage test    # untouched holdout, once (lock file)

Every run is appended to research/experiment_log.jsonl.
"""

from __future__ import annotations

import copy
import itertools
import json
import math
import subprocess
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from qtrade.backtest.engine import buy_and_hold, run_backtest
from qtrade.backtest.metrics import compute_metrics, daily_returns, period_returns
from qtrade.backtest.stats import bootstrap_sharpe, deflated_sharpe_ratio
from qtrade.config import load_config
from qtrade.data.pipeline import load_bars
from qtrade.strategies import make_strategy

SPLITS = {
    "dev": ("2017-01-01", "2022-01-01"),
    "val": ("2022-01-01", "2024-01-01"),
    "test": ("2024-01-01", "2026-10-16"),
}
COSTS = {
    "baseline": {"maker_fee": 0.0022, "taker_fee": 0.0038, "slippage_bps": 5.0},
    "stress": {"maker_fee": 0.0040, "taker_fee": 0.0080, "slippage_bps": 10.0},
    "optimistic": {"maker_fee": 0.0, "taker_fee": 0.0010, "slippage_bps": 2.0},
    "gross": {"maker_fee": 0.0, "taker_fee": 0.0, "slippage_bps": 0.0, "short_open_fee": 0.0,
              "short_rollover_per_4h": 0.0},
}


@dataclass(frozen=True)
class Candidate:
    cid: str
    strategy: str
    base: dict[str, Any]
    grid: dict[str, list[Any]]
    session: tuple[str, str, str] | None = None   # NY window for the matched random control

    def configs(self) -> list[dict[str, Any]]:
        keys = list(self.grid)
        return [{**self.base, **dict(zip(keys, vals, strict=True))}
                for vals in itertools.product(*(self.grid[k] for k in keys))]


CANDIDATES = [
    Candidate("C1", "donchian_trend", {}, {"entry_n": [24, 48, 96], "stop_atr": [2.0, 3.0]}),
    Candidate("C2", "bollinger_mr", {}, {"z_entry": [2.0, 2.5, 3.0], "adx_max": [20.0, 25.0, 100.0]}),
    Candidate("C3", "intraday_momentum", {}, {"mode": ["first", "both"]}),
    Candidate("C4", "orb", {}, {"or_minutes": [15, 30], "stop_mode": ["opposite", "atr"], "rr": [None, 2.0]},
              session=("09:30", "15:00", "16:00")),
    Candidate("C5", "sweep_fvg", {}, {"entry": ["edge", "mid"], "rr": [2.0, 3.0],
                                       "window_end": ["11:00", "11:30"]},
              session=("09:30", "11:30", "16:00")),
]
N_TRIALS = sum(len(c.configs()) for c in CANDIDATES)  # 33

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs" / "experiments"
LOG = ROOT / "research" / "experiment_log.jsonl"

_BARS: dict[str, pd.DataFrame] = {}
_SIGS: dict[str, pd.DataFrame] = {}


def research_cfg(cost: str = "baseline") -> dict[str, Any]:
    cfg = load_config(ROOT / "configs" / "backtest.yaml")
    cfg["costs"].update(COSTS[cost])
    return cfg


def bars_for(tf: str) -> pd.DataFrame:
    if tf not in _BARS:
        _BARS[tf] = load_bars(tf, ROOT / "data" / "clean", start="2016-01-01", end=SPLITS["test"][1])
    return _BARS[tf]


def _key(strategy: str, params: dict[str, Any]) -> str:
    return strategy + json.dumps(params, sort_keys=True, default=str)


def signals_for(strategy: str, params: dict[str, Any]) -> pd.DataFrame:
    k = _key(strategy, params)
    if k not in _SIGS:
        strat = make_strategy(strategy, params)
        _SIGS[k] = strat.generate(bars_for(strat.timeframe))
    return _SIGS[k]


def run_config(strategy: str, params: dict[str, Any], start: str, end: str, cost: str = "baseline"):
    strat = make_strategy(strategy, params)
    res = run_backtest(bars_for(strat.timeframe), signals_for(strategy, params), research_cfg(cost),
                       start=start, end=end, strategy_name=strat.describe(), timeframe=strat.timeframe)
    return res, compute_metrics(res)


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True).stdout.strip()
    except OSError:
        return "unknown"


def _data_hash() -> str:
    rep = ROOT / "data" / "clean" / "validation_report.json"
    if not rep.exists():
        return "missing"
    r = json.loads(rep.read_text())
    return ",".join(f"{tf}:{v['sha256'][:10]}" for tf, v in r["bars"].items())


def _code_hash() -> str:
    import hashlib

    h = hashlib.sha256()
    for f in sorted((ROOT / "src" / "qtrade").rglob("*.py")):
        h.update(f.relative_to(ROOT).as_posix().encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def log_experiment(record: dict[str, Any]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    rec = {"logged_at": datetime.now(UTC).isoformat(timespec="seconds"), "git": _git_commit(),
           "data": _data_hash(), **record}
    with LOG.open("a") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")


KEY_METRICS = ["n_trades", "net_return", "gross_return", "total_costs", "sharpe", "sortino", "max_drawdown",
               "max_drawdown_days", "win_rate", "profit_factor", "expectancy_usd", "expectancy_r", "exposure",
               "avg_hold_hours", "turnover_per_year", "trades_per_year", "long_trades", "short_trades",
               "long_net_pnl", "short_net_pnl", "cagr", "fees", "financing", "slippage_cost"]


def _slim(m: dict[str, Any]) -> dict[str, Any]:
    return {k: m[k] for k in KEY_METRICS if k in m}


# ----------------------------------------------------------------- controls
def _control_job(args: tuple) -> float:
    tf, params, start, end, seed = args
    strat = make_strategy("random_entry", {**params, "seed": seed})
    bars = bars_for(tf)
    res = run_backtest(bars, strat.generate(bars), research_cfg("baseline"), start=start, end=end,
                       timeframe=tf)
    return float(res.equity.iloc[-1] / res.initial_equity - 1)


def random_controls(cand: Candidate, start: str, end: str, n_seeds: int = 200, workers: int = 4,
                    match: str = "signals") -> dict:
    """Random-entry control. ``match='signals'`` (pre-registered): entry rate from the candidate's
    signal count; ``match='trades'`` (supplementary): from its executed trade count."""
    strat = make_strategy(cand.strategy, cand.base)
    tf = strat.timeframe
    bars = bars_for(tf)
    sig = signals_for(cand.strategy, cand.base)
    win = (bars.index >= pd.Timestamp(start, tz="UTC")) & (bars.index < pd.Timestamp(end, tz="UTC"))
    n_sig = int((sig.loc[win, "entry"] != 0).sum())
    res, _ = run_config(cand.strategy, cand.base, start, end)
    if match == "trades":
        n_sig = len(res.trades)
    hold = int(np.median(res.trades["bars_held"])) if len(res.trades) else 16
    params: dict[str, Any] = {"max_hold": max(hold, 1), "stop_atr": 2.0, "rr": 2.0, "atr_n": 14}
    if cand.session:
        from qtrade import features as F

        local = F.local_time(bars.index[win])
        mod = F.minutes_of_day(local)
        s0, s1 = F.parse_hhmm(cand.session[0]), F.parse_hhmm(cand.session[1])
        eligible = int(((mod >= s0) & (mod < s1) & (local.dayofweek.to_numpy() < 5)).sum())
        params.update(ny_start=cand.session[0], ny_end=cand.session[1], ny_close=cand.session[2])
    else:
        eligible = int(win.sum())
    params["prob"] = min(n_sig / max(eligible, 1), 1.0)
    jobs = [(tf, params, start, end, seed) for seed in range(n_seeds)]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rets = list(pool.map(_control_job, jobs, chunksize=4))
    arr = np.array(rets)
    return {"n_seeds": n_seeds, "match": match, "params": params, "candidate_signals": n_sig,
            "mean": float(arr.mean()), "p05": float(np.quantile(arr, 0.05)),
            "p50": float(np.median(arr)), "p95": float(np.quantile(arr, 0.95)), "returns": arr.tolist()}


# ------------------------------------------------------------------- stages
def _benchmarks(start: str, end: str) -> dict[str, Any]:
    bh = buy_and_hold(bars_for("1h"), research_cfg("baseline"), start=start, end=end)
    return {"buy_and_hold": _slim(compute_metrics(bh)), "no_trade": {"net_return": 0.0, "sharpe": float("nan")}}


def stage_period(stage: str, with_grid: bool) -> dict[str, Any]:
    start, end = SPLITS[stage]
    out: dict[str, Any] = {"stage": stage, "start": start, "end": end, "benchmarks": _benchmarks(start, end),
                           "candidates": {}}
    for cand in CANDIDATES:
        entry: dict[str, Any] = {"strategy": cand.strategy, "baseline": {}}
        for cost in ("baseline", "stress", "optimistic", "gross"):
            res, m = run_config(cand.strategy, cand.base, start, end, cost)
            entry["baseline"][cost] = _slim(m)
            log_experiment({"stage": stage, "candidate": cand.cid, "strategy": cand.strategy,
                            "params": cand.base, "period": [start, end], "costs": cost, "metrics": _slim(m)})
            if cost == "baseline":
                dr = daily_returns(res.equity, res.initial_equity).to_numpy()
                entry["bootstrap"] = bootstrap_sharpe(dr, n_boot=2000, mean_block=10.0, alpha=0.10, seed=0)
                entry["yearly"] = {str(k.year): float(v) for k, v in period_returns(res, "YE").items()}
                entry["exit_reasons"] = res.trades["exit_reason"].value_counts().to_dict()
        if with_grid:
            grid = []
            for params in cand.configs():
                res, m = run_config(cand.strategy, params, start, end)
                dr = daily_returns(res.equity, res.initial_equity).to_numpy()
                sr_d = float(dr.mean() / dr.std(ddof=1)) if dr.std(ddof=1) > 0 else float("nan")
                grid.append({"params": params, "sharpe_daily": sr_d, **_slim(m)})
                log_experiment({"stage": stage, "candidate": cand.cid, "strategy": cand.strategy, "params": params,
                                "period": [start, end], "costs": "baseline", "grid": True, "metrics": _slim(m)})
            entry["grid"] = grid
        out["candidates"][cand.cid] = entry
        print(f"[{stage}] {cand.cid} {cand.strategy}: n={entry['baseline']['baseline']['n_trades']} "
              f"net={entry['baseline']['baseline']['net_return']:+.3f} "
              f"gross={entry['baseline']['gross']['net_return']:+.3f} "
              f"sharpe={entry['baseline']['baseline']['sharpe']:.2f}", flush=True)
    return out


def _add_months(ts: pd.Timestamp, months: int) -> pd.Timestamp:
    return ts + pd.DateOffset(months=months)


def stage_walk_forward() -> dict[str, Any]:
    first = pd.Timestamp("2017-01-01")
    limit = pd.Timestamp(SPLITS["val"][1])
    out: dict[str, Any] = {"stage": "wf", "windows": [], "candidates": {}}
    windows = []
    s = first
    while _add_months(s, 30) <= limit:
        windows.append((s, _add_months(s, 24), _add_months(s, 30)))
        s = _add_months(s, 6)
    out["windows"] = [[str(a.date()), str(b.date()), str(c.date())] for a, b, c in windows]
    for cand in CANDIDATES:
        segs, picks = [], []
        for tr0, te0, te1 in windows:
            best, best_sr = cand.base, -math.inf
            for params in cand.configs():
                res, m = run_config(cand.strategy, params, str(tr0.date()), str(te0.date()))
                if m["n_trades"] >= 20 and np.isfinite(m["sharpe"]) and m["sharpe"] > best_sr:
                    best, best_sr = params, m["sharpe"]
            res, m = run_config(cand.strategy, best, str(te0.date()), str(te1.date()))
            segs.append(daily_returns(res.equity, res.initial_equity))
            picks.append({"train": [str(tr0.date()), str(te0.date())], "test": [str(te0.date()), str(te1.date())],
                          "params": best, "train_sharpe": best_sr, "oos": _slim(m)})
            log_experiment({"stage": "wf", "candidate": cand.cid, "strategy": cand.strategy, "params": best,
                            "period": [str(te0.date()), str(te1.date())], "costs": "baseline", "metrics": _slim(m)})
        dr = pd.concat(segs)
        eq = (1 + dr).cumprod()
        from qtrade.backtest.metrics import sharpe as _sh

        out["candidates"][cand.cid] = {
            "strategy": cand.strategy, "picks": picks,
            "oos_net_return": float(eq.iloc[-1] - 1), "oos_sharpe": _sh(dr.to_numpy()),
            "oos_max_drawdown": float((eq / eq.cummax() - 1).min()),
            "oos_trades": int(sum(p["oos"]["n_trades"] for p in picks)),
            "bootstrap": bootstrap_sharpe(dr.to_numpy(), n_boot=2000, seed=0),
        }
        print(f"[wf] {cand.cid}: oos net {out['candidates'][cand.cid]['oos_net_return']:+.3f} "
              f"sharpe {out['candidates'][cand.cid]['oos_sharpe']:.2f}", flush=True)
    return out


def _lock_payload() -> dict[str, Any]:
    return {"candidates": {c.cid: {"strategy": c.strategy, "params": c.base} for c in CANDIDATES},
            "split": SPLITS["test"], "costs": COSTS, "code_sha256": _code_hash(), "data": _data_hash()}


def stage_test(allow_rerun: bool = False, n_seeds: int = 200) -> dict[str, Any]:
    lock = OUT / "test_lock.json"
    payload = _lock_payload()
    if lock.exists():
        prev = json.loads(lock.read_text())
        if prev["payload"] != json.loads(json.dumps(payload, default=str)) and not allow_rerun:
            raise SystemExit("test stage already run with different configuration, code or data; refusing "
                             "(see methodology). Use --allow-rerun only for a logged deviation.")
        if not allow_rerun:
            print("test stage already run with this exact configuration; re-running for reproducibility only")
    lock.parent.mkdir(parents=True, exist_ok=True)
    history = json.loads(lock.read_text()).get("history", []) if lock.exists() else []
    if lock.exists():
        prev = json.loads(lock.read_text())
        history.append({k: prev.get(k) for k in ("locked_at", "git", "payload")})
    lock.write_text(json.dumps({"locked_at": datetime.now(UTC).isoformat(timespec="seconds"),
                                "git": _git_commit(), "payload": payload, "history": history},
                               indent=2, default=str))
    out = stage_period("test", with_grid=False)
    start, end = SPLITS["test"]
    val = json.loads((OUT / "val" / "summary.json").read_text()) if (OUT / "val" / "summary.json").exists() else None
    var_sr = None
    if val is not None:
        srs = [g["sharpe_daily"] for c in val["candidates"].values() for g in c.get("grid", [])
               if np.isfinite(g["sharpe_daily"])]
        var_sr = float(np.var(srs, ddof=1)) if len(srs) > 2 else None
    for cand in CANDIDATES:
        e = out["candidates"][cand.cid]
        res, _ = run_config(cand.strategy, cand.base, start, end)
        dr = daily_returns(res.equity, res.initial_equity).to_numpy()
        e["dsr"] = deflated_sharpe_ratio(dr, N_TRIALS, var_sr)
        e["dsr"]["n_trials"] = N_TRIALS
        e["dsr"]["var_sr_trials"] = var_sr
        # Supplementary (post-audit, not a decision input): null variance 1/(n-1).
        e["dsr_null_variance"] = deflated_sharpe_ratio(dr, N_TRIALS, None)
        ctrl = random_controls(cand, start, end, n_seeds=n_seeds)
        net = e["baseline"]["baseline"]["net_return"]
        e["control"] = {k: v for k, v in ctrl.items() if k != "returns"}
        e["control"]["percentile_of_candidate"] = float((np.array(ctrl["returns"]) < net).mean())
        # Supplementary (post-audit, not a decision input): control matched to executed trades.
        ctrl_t = random_controls(cand, start, end, n_seeds=max(n_seeds // 2, 20), match="trades")
        e["control_trade_matched"] = {k: v for k, v in ctrl_t.items() if k != "returns"}
        e["control_trade_matched"]["percentile_of_candidate"] = float((np.array(ctrl_t["returns"]) < net).mean())
        e["by_direction"] = {"long_trades": e["baseline"]["baseline"]["long_trades"],
                             "short_trades": e["baseline"]["baseline"]["short_trades"]}
        e["monthly"] = {str(k.date()): float(v) for k, v in period_returns(res, "ME").items()}
        mb = e["baseline"]["baseline"]
        val_sr = val["candidates"][cand.cid]["baseline"]["baseline"]["sharpe"] if val else float("nan")
        crit = {
            "1_min_30_trades": mb["n_trades"] >= 30,
            "2_net_positive_and_sharpe_ge_0.5": mb["net_return"] > 0 and mb["sharpe"] >= 0.5,
            "3_bootstrap_ci_lower_gt_0": e["bootstrap"]["lo"] > 0,
            "4_dsr_ge_0.90": bool(e["dsr"]["dsr"] >= 0.90),
            "5_beats_95pct_random_controls": e["control"]["percentile_of_candidate"] > 0.95,
            "6_stress_sharpe_gt_0": e["baseline"]["stress"]["sharpe"] > 0,
            "7_validation_sharpe_gt_0": bool(val_sr > 0),
            "8_profit_factor_ge_1.10": bool(mb["profit_factor"] >= 1.10),
        }
        e["criteria"] = crit
        e["verdict"] = "CANDIDATE FOR FURTHER EVALUATION" if all(crit.values()) else (
            "INSUFFICIENT EVIDENCE (too few trades)" if not crit["1_min_30_trades"] else "FAILED")
        log_experiment({"stage": "test", "candidate": cand.cid, "strategy": cand.strategy, "params": cand.base,
                        "period": [start, end], "criteria": crit, "verdict": e["verdict"],
                        "dsr": e["dsr"], "control": e["control"]})
        print(f"[test] {cand.cid} {cand.strategy}: {e['verdict']} {crit}", flush=True)
    return out


def save(stage: str, out: dict[str, Any]) -> Path:
    d = OUT / stage
    d.mkdir(parents=True, exist_ok=True)
    p = d / "summary.json"
    p.write_text(json.dumps(out, indent=2, default=lambda o: None if isinstance(o, float) and math.isnan(o) else str(o)))
    return p


def run_stage(stage: str, allow_rerun: bool = False, seeds: int = 200) -> Path:
    if stage == "dev":
        out = stage_period("dev", with_grid=True)
    elif stage == "val":
        out = stage_period("val", with_grid=True)
    elif stage == "wf":
        out = stage_walk_forward()
    elif stage == "test":
        out = stage_test(allow_rerun, seeds)
    else:
        raise ValueError(stage)
    return save(stage, copy.deepcopy(out))
