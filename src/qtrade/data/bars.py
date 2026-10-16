"""Resampling 1-minute candles into complete higher-timeframe bars.

Conventions (used everywhere in qtrade):

* A bar is labelled by its **open time** (UTC) and covers ``[open, open + tf)``.
* A bar is only *known* once its close time ``open + tf`` has passed. Strategies
  evaluate a bar after it closes and any order resulting from it executes no
  earlier than the **next** bar's open.
* ``n_minutes`` counts source minutes present; ``complete`` is True only when
  every minute of the bar is present. A trailing in-progress bar is dropped.
* ``n_active`` counts minutes with non-zero volume (the source fills missing
  minutes with flat zero-volume candles). ``quote_volume`` approximates traded
  notional as ``sum(volume * typical_price)``.
"""

from __future__ import annotations

import pandas as pd


def timeframe_minutes(tf: str) -> int:
    td = pd.Timedelta(tf)
    minutes = td.total_seconds() / 60
    if minutes < 1 or minutes != int(minutes):
        raise ValueError(f"timeframe must be a whole number of minutes: {tf}")
    return int(minutes)


def resample_bars(minutes: pd.DataFrame, tf: str, drop_incomplete_tail: bool = True) -> pd.DataFrame:
    """Aggregate 1-minute OHLCV (UTC-indexed) into ``tf`` bars labelled by open time."""
    if minutes.index.tz is None:
        raise ValueError("minute data must have a tz-aware UTC index")
    n = timeframe_minutes(tf)
    m = minutes.copy()
    m["active"] = (m["volume"] > 0).astype("int64")
    m["qv"] = m["volume"] * (m["high"] + m["low"] + m["close"]) / 3.0
    m["one"] = 1
    g = m.resample(tf, label="left", closed="left")
    bars = pd.DataFrame(
        {
            "open": g["open"].first(),
            "high": g["high"].max(),
            "low": g["low"].min(),
            "close": g["close"].last(),
            "volume": g["volume"].sum(),
            "quote_volume": g["qv"].sum(),
            "n_minutes": g["one"].sum(),
            "n_active": g["active"].sum(),
        }
    )
    bars = bars[bars["n_minutes"] > 0].copy()
    bars["n_minutes"] = bars["n_minutes"].astype("int64")
    bars["n_active"] = bars["n_active"].astype("int64")
    bars["complete"] = bars["n_minutes"] == n
    if drop_incomplete_tail and len(bars) and not bars["complete"].iloc[-1]:
        # The final bar may still be forming: never let a partial bar through.
        bars = bars.iloc[:-1]
    bars.index.name = "ts"
    return bars
