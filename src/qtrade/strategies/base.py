"""Strategy interface shared by the backtester and the paper trader.

A strategy is a pure function of *completed* bars. ``generate(bars)`` returns a
signal frame aligned to ``bars.index`` whose row t may only depend on bars
0..t (enforced by tests/test_lookahead.py). Row t expresses intent evaluated at
the close of bar t; the engine acts no earlier than the open of bar t+1.

Signals are position-agnostic: the strategy does not know whether the risk
manager approved earlier entries, which keeps strategy logic independent of
execution and identical between backtest and paper trading.

Signal columns
--------------
entry        int8  +1 long / -1 short / 0 none
stop         float protective stop price for the new position (required with entry)
target       float take-profit price (NaN = none)
limit_price  float NaN = market order at next open; else resting limit order
expiry_bars  int   bars a limit order stays active (>= 1)
max_hold     float bars after which an open position is closed at next open (NaN = none)
exit         bool  close any open position at the next open
trail_long   float tighten-only stop update for an open long  (NaN = none)
trail_short  float tighten-only stop update for an open short (NaN = none)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

import numpy as np
import pandas as pd

SIGNAL_COLUMNS = ["entry", "stop", "target", "limit_price", "expiry_bars", "max_hold", "exit",
                  "trail_long", "trail_short"]


def empty_signals(index: pd.DatetimeIndex) -> pd.DataFrame:
    n = len(index)
    return pd.DataFrame(
        {
            "entry": np.zeros(n, dtype=np.int8),
            "stop": np.full(n, np.nan),
            "target": np.full(n, np.nan),
            "limit_price": np.full(n, np.nan),
            "expiry_bars": np.ones(n, dtype=np.int64),
            "max_hold": np.full(n, np.nan),
            "exit": np.zeros(n, dtype=bool),
            "trail_long": np.full(n, np.nan),
            "trail_short": np.full(n, np.nan),
        },
        index=index,
    )


def validate_signals(sig: pd.DataFrame, bars: pd.DataFrame) -> None:
    """Raise ValueError if a signal frame violates the contract."""
    missing = [c for c in SIGNAL_COLUMNS if c not in sig.columns]
    if missing:
        raise ValueError(f"signal frame missing columns {missing}")
    if not sig.index.equals(bars.index):
        raise ValueError("signal index must equal bar index")
    entry = sig["entry"].to_numpy()
    if not np.isin(entry, (-1, 0, 1)).all():
        raise ValueError("entry must be in {-1, 0, 1}")
    has = entry != 0
    stop = sig["stop"].to_numpy()
    if np.isnan(stop[has]).any():
        raise ValueError("every entry needs a stop price")
    ref = np.where(np.isnan(sig["limit_price"].to_numpy()), bars["close"].to_numpy(),
                   sig["limit_price"].to_numpy())
    long_bad = (entry == 1) & ~(stop < ref)
    short_bad = (entry == -1) & ~(stop > ref)
    if long_bad.any() or short_bad.any():
        raise ValueError("stop must be below the reference price for longs and above for shorts")
    tgt = sig["target"].to_numpy()
    with np.errstate(invalid="ignore"):
        if ((entry == 1) & ~np.isnan(tgt) & (tgt <= ref)).any() or (
            (entry == -1) & ~np.isnan(tgt) & (tgt >= ref)
        ).any():
            raise ValueError("target must be beyond the reference price in the trade direction")
    if (sig["expiry_bars"].to_numpy() < 1).any():
        raise ValueError("expiry_bars must be >= 1")


class Strategy(ABC):
    """Base class. Subclasses set ``name``/``timeframe`` and implement ``_generate``."""

    name: ClassVar[str] = "base"
    timeframe: ClassVar[str] = "15min"
    default_params: ClassVar[dict[str, Any]] = {}

    def __init__(self, **params: Any) -> None:
        unknown = set(params) - set(self.default_params)
        if unknown:
            raise ValueError(f"{self.name}: unknown parameters {sorted(unknown)}")
        self.params = {**self.default_params, **params}

    @property
    def warmup_bars(self) -> int:
        """Bars of history needed before signals are meaningful (paper-trading window)."""
        return 500

    def generate(self, bars: pd.DataFrame) -> pd.DataFrame:
        sig = self._generate(bars)
        validate_signals(sig, bars)
        return sig

    @abstractmethod
    def _generate(self, bars: pd.DataFrame) -> pd.DataFrame: ...

    def describe(self) -> str:
        return f"{self.name}({', '.join(f'{k}={v}' for k, v in sorted(self.params.items()))})"
