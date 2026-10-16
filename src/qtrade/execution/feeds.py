"""Market-data feeds for the paper trader.

* :class:`ReplayFeed` replays historical bars as if they were arriving live,
  with optional seeded fault injection (timeouts, frozen/stale feed, malformed
  rows, duplicate rows, dropped bars).
* :class:`KrakenOHLCFeed` polls Kraken's public OHLC endpoint and merges the
  returned (<= 720) closed candles with locally cached history so strategies
  get their full warm-up window.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from qtrade.execution.kraken import KrakenPublicClient


class FeedError(RuntimeError):
    """Market data could not be retrieved."""


def clean_feed_bars(bars: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Drop malformed/duplicate rows and sort; return (clean bars, problems found)."""
    problems: list[str] = []
    if bars.empty:
        return bars, problems
    b = bars
    if not b.index.is_monotonic_increasing:
        problems.append("unsorted bars")
        b = b.sort_index(kind="mergesort")
    dup = b.index.duplicated(keep="last")
    if dup.any():
        problems.append(f"{int(dup.sum())} duplicate bars")
        b = b[~dup]
    px = b[["open", "high", "low", "close"]]
    bad = ~np.isfinite(px.to_numpy(float)).all(axis=1) | (px <= 0).any(axis=1).to_numpy()
    bad |= (b["high"] < b[["open", "close"]].max(axis=1)).to_numpy()
    bad |= (b["low"] > b[["open", "close"]].min(axis=1)).to_numpy()
    if bad.any():
        problems.append(f"{int(bad.sum())} malformed bars")
        b = b[~bad]
    return b, problems


class ReplayFeed:
    def __init__(self, bars: pd.DataFrame, bar_minutes: int, faults: dict[str, Any] | None = None,
                 seed: int = 0) -> None:
        self.bars = bars
        self.td = pd.Timedelta(minutes=bar_minutes)
        self.faults = faults or {}
        self.rng = np.random.default_rng(seed)
        self._close_times = bars.index + self.td

    def fetch(self, now: pd.Timestamp) -> pd.DataFrame:
        f = self.faults
        if f.get("timeout_prob") and self.rng.random() < f["timeout_prob"]:
            raise FeedError("feed timeout (simulated)")
        freeze = f.get("freeze_between")
        if freeze and pd.Timestamp(freeze[0]) <= now < pd.Timestamp(freeze[1]):
            now = pd.Timestamp(freeze[0])  # feed stops updating: stale data
        n = int(self._close_times.searchsorted(now, side="right"))
        out = self.bars.iloc[:n]
        if f.get("drop_prob") and len(out) > 1 and self.rng.random() < f["drop_prob"]:
            out = out.drop(out.index[-1])
        if f.get("malformed_prob") and len(out) and self.rng.random() < f["malformed_prob"]:
            out = out.copy()
            out.iloc[-1, out.columns.get_loc("high")] = np.nan
        if f.get("duplicate_prob") and len(out) and self.rng.random() < f["duplicate_prob"]:
            out = pd.concat([out, out.iloc[[-1]]])
        return out


class KrakenOHLCFeed:
    def __init__(self, client: KrakenPublicClient, interval_min: int, pair: str = "XBTUSD",
                 history: pd.DataFrame | None = None) -> None:
        self.client = client
        self.interval = interval_min
        self.pair = pair
        self.cache = history if history is not None else pd.DataFrame()

    def fetch(self, now: pd.Timestamp) -> pd.DataFrame:
        try:
            recent = self.client.ohlc(self.pair, self.interval)
        except Exception as exc:  # network/exchange failure -> caller treats as stale
            raise FeedError(str(exc)) from exc
        merged = pd.concat([self.cache, recent]) if len(self.cache) else recent
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
        self.cache = merged
        return merged
