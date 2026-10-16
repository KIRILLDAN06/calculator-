"""Performance metrics. Every metric is defined in research/backtest_methodology.md.

Return frequency for Sharpe/Sortino: daily (UTC calendar day) returns of
mark-to-market equity, annualised with sqrt(365) because crypto trades every
day. Expectancy and win rate are computed from realised trade outcomes after
all costs.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from qtrade.backtest.engine import BacktestResult

DAYS_PER_YEAR = 365.0


def daily_returns(equity: pd.Series, initial: float) -> pd.Series:
    """Daily simple returns from bar-close equity (first day measured vs initial equity)."""
    daily = equity.resample("1D").last().ffill()
    prev = daily.shift(1)
    prev.iloc[0] = initial
    return (daily / prev - 1.0).rename("ret")


def drawdown(equity: pd.Series) -> pd.Series:
    return equity / equity.cummax() - 1.0


def max_drawdown_duration_days(equity: pd.Series) -> float:
    """Longest span (days) between a peak and the recovery to that peak (or the end)."""
    peak = equity.cummax()
    under = equity < peak
    if not under.any():
        return 0.0
    ts = equity.index
    longest = pd.Timedelta(0)
    start = None
    for t, u in zip(ts, under.to_numpy(), strict=True):
        if u and start is None:
            start = t
        elif not u and start is not None:
            longest = max(longest, t - start)
            start = None
    if start is not None:
        longest = max(longest, ts[-1] - start)
    return longest.total_seconds() / 86400.0


def sharpe(returns: pd.Series | np.ndarray, periods_per_year: float = DAYS_PER_YEAR) -> float:
    r = np.asarray(returns, float)
    r = r[np.isfinite(r)]
    if r.size < 2 or r.std(ddof=1) == 0:
        return float("nan")
    return float(r.mean() / r.std(ddof=1) * math.sqrt(periods_per_year))


def sortino(returns: pd.Series | np.ndarray, periods_per_year: float = DAYS_PER_YEAR) -> float:
    r = np.asarray(returns, float)
    r = r[np.isfinite(r)]
    if r.size < 2:
        return float("nan")
    downside = math.sqrt(np.mean(np.minimum(r, 0.0) ** 2))
    if downside == 0:
        return float("nan")
    return float(r.mean() / downside * math.sqrt(periods_per_year))


def _safe_div(a: float, b: float) -> float:
    return float(a / b) if b not in (0, 0.0) and np.isfinite(b) else float("nan")


def compute_metrics(res: BacktestResult) -> dict[str, Any]:
    eq = res.equity
    initial = res.initial_equity
    final = float(eq.iloc[-1])
    tr = res.trades
    days = max((eq.index[-1] - eq.index[0]).total_seconds() / 86400.0, 1e-9)
    years = days / DAYS_PER_YEAR
    dr = daily_returns(eq, initial)

    costs_fees = float(tr["fees"].sum()) if len(tr) else 0.0
    costs_fin = float(tr["financing"].sum()) if len(tr) else 0.0
    costs_slip = float(tr["slippage_cost"].sum()) if len(tr) else 0.0
    total_costs = costs_fees + costs_fin + costs_slip

    wins = tr.loc[tr["net_pnl"] > 0, "net_pnl"] if len(tr) else pd.Series(dtype=float)
    losses = tr.loc[tr["net_pnl"] <= 0, "net_pnl"] if len(tr) else pd.Series(dtype=float)
    bar_min = (eq.index[1] - eq.index[0]).total_seconds() / 60.0 if len(eq) > 1 else float("nan")
    traded_notional = float((tr["qty"] * (tr["entry_price"] + tr["exit_price"])).sum()) if len(tr) else 0.0

    m: dict[str, Any] = {
        "strategy": res.strategy,
        "start": eq.index[0].isoformat(),
        "end": eq.index[-1].isoformat(),
        "days": round(days, 2),
        "initial_equity": initial,
        "final_equity": final,
        "net_return": final / initial - 1.0,
        "gross_return": (final - initial + total_costs) / initial,
        "cagr": (final / initial) ** (1.0 / years) - 1.0 if final > 0 and years > 0 else float("nan"),
        "total_costs": total_costs,
        "fees": costs_fees,
        "financing": costs_fin,
        "slippage_cost": costs_slip,
        "n_trades": len(tr),
        "trades_per_year": len(tr) / years if years > 0 else float("nan"),
        "win_rate": _safe_div(len(wins), len(tr)),
        "avg_win": float(wins.mean()) if len(wins) else float("nan"),
        "avg_loss": float(losses.mean()) if len(losses) else float("nan"),
        "avg_win_loss_ratio": _safe_div(float(wins.mean()) if len(wins) else float("nan"),
                                        abs(float(losses.mean())) if len(losses) else float("nan")),
        "profit_factor": _safe_div(float(wins.sum()), abs(float(losses.sum()))) if len(losses) else float("nan"),
        "expectancy_usd": float(tr["net_pnl"].mean()) if len(tr) else float("nan"),
        "expectancy_r": float(tr["r_multiple"].mean()) if len(tr) else float("nan"),
        "max_drawdown": float(drawdown(eq).min()),
        "max_drawdown_days": max_drawdown_duration_days(eq),
        "sharpe": sharpe(dr),
        "sortino": sortino(dr),
        "daily_vol_ann": float(dr.std(ddof=1) * math.sqrt(DAYS_PER_YEAR)) if len(dr) > 1 else float("nan"),
        "exposure": float((res.position != 0).mean()),
        "turnover_per_year": _safe_div(traded_notional, float(eq.mean()) * years),
        "avg_hold_hours": float(tr["bars_held"].mean() * bar_min / 60.0) if len(tr) else float("nan"),
        "n_rejected_signals": len(res.rejected),
        "risk_events": len(res.events),
        "halted": any(e["kind"] == "HALT" for e in res.events),
    }
    for side, label in ((1, "long"), (-1, "short")):
        sub = tr[tr["side"] == side] if len(tr) else tr
        m[f"{label}_trades"] = len(sub)
        m[f"{label}_net_pnl"] = float(sub["net_pnl"].sum()) if len(sub) else 0.0
        m[f"{label}_win_rate"] = _safe_div(int((sub["net_pnl"] > 0).sum()), len(sub)) if len(sub) else float("nan")
    return m


def period_returns(res: BacktestResult, freq: str = "ME") -> pd.Series:
    """Compounded returns per period (e.g. 'ME' monthly, 'YE' yearly)."""
    dr = daily_returns(res.equity, res.initial_equity)
    return (1 + dr).resample(freq).prod() - 1.0
