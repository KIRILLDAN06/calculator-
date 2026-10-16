from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qtrade.config import load_config


def make_bars(rows: list[tuple[float, float, float, float]], start: str = "2024-01-02 00:00",
              tf: str = "1h", volume: float = 100.0) -> pd.DataFrame:
    """Bars from explicit (open, high, low, close) tuples; huge liquidity, all complete."""
    idx = pd.date_range(start, periods=len(rows), freq=tf, tz="UTC", name="ts")
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx, dtype=float)
    df["volume"] = volume
    df["quote_volume"] = 1e12
    df["n_minutes"] = int(pd.Timedelta(tf).total_seconds() // 60)
    df["n_active"] = df["n_minutes"]
    df["complete"] = True
    return df


def random_walk_bars(n: int, tf: str = "5min", seed: int = 0, start: str = "2024-03-04 00:00",
                     vol: float = 0.002, price: float = 50_000.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.standard_t(4, size=n) * vol / np.sqrt(2)
    close = price * np.exp(np.cumsum(rets))
    open_ = np.concatenate(([price], close[:-1]))
    span = np.abs(rng.normal(0, vol, size=n)) * close
    high = np.maximum(open_, close) + span * rng.random(n)
    low = np.minimum(open_, close) - span * rng.random(n)
    rows = list(zip(open_, high, low, close, strict=True))
    bars = make_bars(rows, start=start, tf=tf)
    bars["volume"] = rng.uniform(1, 50, size=n)
    bars["quote_volume"] = bars["volume"] * bars["close"]
    return bars


def signal_frame(bars: pd.DataFrame) -> pd.DataFrame:
    from qtrade.strategies.base import empty_signals

    return empty_signals(bars.index)


@pytest.fixture
def cfg():
    """Research-like config with zero costs (tests add costs explicitly)."""
    return load_config(overrides={
        "costs": {"taker_fee": 0.0, "maker_fee": 0.0, "slippage_bps": 0.0,
                  "short_open_fee": 0.0, "short_rollover_per_4h": 0.0},
        "risk": {"risk_per_trade": 0.01, "max_trades_per_day": 50, "max_daily_loss": 0.5,
                 "max_drawdown": 0.9, "drawdown_halt": False, "max_consecutive_losses": 1000,
                 "cooldown_bars_after_loss_streak": 0},
    })


@pytest.fixture
def cost_cfg():
    """Config with realistic non-zero costs for accounting tests."""
    return load_config(overrides={
        "costs": {"taker_fee": 0.004, "maker_fee": 0.002, "slippage_bps": 10.0,
                  "short_open_fee": 0.0002, "short_rollover_per_4h": 0.0002},
        "risk": {"risk_per_trade": 0.01, "max_trades_per_day": 50, "max_daily_loss": 0.5,
                 "max_drawdown": 0.9, "drawdown_halt": False, "max_consecutive_losses": 1000,
                 "cooldown_bars_after_loss_streak": 0},
    })
