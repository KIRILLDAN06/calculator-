"""Layer D: no strategy may use future information.

Two independent checks per strategy:
1. Truncation: the signal row for bar t computed from bars[:t+1] equals row t
   computed from the full history.
2. Perturbation: replacing every bar after t with different data leaves all
   signal rows <= t unchanged.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from conftest import random_walk_bars
from qtrade import features as F
from qtrade.strategies import make_strategy

CASES = [
    ("donchian_trend", {}, "1h", 1500),
    ("bollinger_mr", {}, "15min", 2500),
    ("bollinger_mr", {"adx_max": 100.0, "z_entry": 2.0}, "15min", 2500),
    ("intraday_momentum", {}, "30min", 2000),
    ("orb", {}, "5min", 6000),
    ("orb", {"stop_mode": "atr", "rr": 2.0}, "5min", 6000),
    ("sweep_fvg", {}, "5min", 30000),
    ("sweep_fvg", {"entry": "mid", "window_end": "16:00", "mss_bars": 36}, "5min", 30000),
    ("random_entry", {"prob": 0.05}, "15min", 1500),
]


def _assert_rows_equal(a: pd.Series, b: pd.Series) -> None:
    for col in a.index:
        x, y = a[col], b[col]
        if isinstance(x, float) and np.isnan(x):
            assert isinstance(y, float) and np.isnan(y), col
        else:
            assert x == y, (col, x, y)


@pytest.mark.parametrize("name,params,tf,n", CASES)
def test_truncation_invariance(name, params, tf, n):
    bars = random_walk_bars(n, tf=tf, seed=7, vol=0.004)
    strat = make_strategy(name, params)
    full = strat.generate(bars)
    rng = np.random.default_rng(0)
    entries = np.flatnonzero(full["entry"].to_numpy() != 0)
    probe = set(rng.choice(np.arange(n // 3, n), size=15, replace=False)) | set(entries[-10:])
    assert len(entries) > 0, f"{name}: no signals generated; test would be vacuous"
    for t in sorted(probe):
        part = strat.generate(bars.iloc[: t + 1]).iloc[-1]
        _assert_rows_equal(part, full.iloc[t])


def _reflect_future(bars: pd.DataFrame, t: int) -> pd.DataFrame:
    """Mirror every price after bar t around close[t]: each future move reverses sign."""
    out = bars.copy()
    pivot = float(bars["close"].iloc[t])
    post = bars.iloc[t + 1:]
    out.loc[post.index, "open"] = 2 * pivot - post["open"]
    out.loc[post.index, "close"] = 2 * pivot - post["close"]
    out.loc[post.index, "high"] = 2 * pivot - post["low"]
    out.loc[post.index, "low"] = 2 * pivot - post["high"]
    out.loc[post.index, "volume"] = post["volume"].to_numpy()[::-1]
    return out


@pytest.mark.parametrize("name,params,tf,n", CASES)
def test_future_perturbation_invariance(name, params, tf, n):
    bars = random_walk_bars(n, tf=tf, seed=11, vol=0.004)
    strat = make_strategy(name, params)
    base = strat.generate(bars)
    for t in np.linspace(n * 0.4, n * 0.9, 6).astype(int):
        mixed = _reflect_future(bars, int(t))
        pd.testing.assert_frame_equal(base.iloc[: t + 1], strat.generate(mixed).iloc[: t + 1])


def test_fractal_swings_confirmed_only_after_n_bars():
    high = np.array([1, 2, 5, 2, 1, 1, 1], float)
    low = high - 0.5
    sh, _ = F.confirmed_fractal_swings(high, low, 2)
    assert np.isnan(sh[3])        # peak at bar 2 not yet confirmed at bar 3
    assert sh[4] == 5             # confirmed once bars 3 and 4 have closed


DATA = Path("data/clean/btcusd_5min.parquet")


@pytest.mark.data
@pytest.mark.skipif(not DATA.exists(), reason="historical dataset not downloaded")
@pytest.mark.parametrize("name", ["orb", "sweep_fvg"])
def test_truncation_on_real_data(name):
    bars = pd.read_parquet(DATA)
    bars = bars[(bars.index >= "2023-03-01") & (bars.index < "2023-04-15")]
    strat = make_strategy(name)
    full = strat.generate(bars)
    entries = np.flatnonzero(full["entry"].to_numpy() != 0)
    assert len(entries) > 0
    for t in entries[:8]:
        _assert_rows_equal(strat.generate(bars.iloc[: t + 1]).iloc[-1], full.iloc[t])
