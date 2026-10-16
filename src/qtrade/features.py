"""Causal indicator and feature calculations.

Every function here is causal: the value at row t depends only on rows <= t.
Callers that need "previous N bars, excluding the current bar" must shift
explicitly (e.g. ``rolling_high(high, n).shift(1)``). Causality is enforced by
tests/test_features.py and the truncation tests in tests/test_lookahead.py.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

NY_TZ = "America/New_York"


def sma(x: pd.Series, n: int) -> pd.Series:
    return x.rolling(n, min_periods=n).mean()


def ema(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(span=n, adjust=False, min_periods=n).mean()


def rolling_std(x: pd.Series, n: int) -> pd.Series:
    return x.rolling(n, min_periods=n).std(ddof=0)


def zscore(x: pd.Series, n: int) -> pd.Series:
    sd = rolling_std(x, n)
    return (x - sma(x, n)) / sd.replace(0.0, np.nan)


def true_range(bars: pd.DataFrame) -> pd.Series:
    prev_close = bars["close"].shift(1)
    tr = pd.concat(
        [bars["high"] - bars["low"], (bars["high"] - prev_close).abs(), (bars["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    tr.iloc[0] = bars["high"].iloc[0] - bars["low"].iloc[0]
    return tr


def atr(bars: pd.DataFrame, n: int) -> pd.Series:
    """Wilder's ATR (RMA of true range)."""
    return true_range(bars).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def adx(bars: pd.DataFrame, n: int = 14) -> pd.Series:
    """Wilder's ADX."""
    up = bars["high"].diff()
    down = -bars["low"].diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=bars.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=bars.index)
    tr_rma = true_range(bars).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean() / tr_rma
    minus_di = 100 * minus_dm.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean() / tr_rma
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    return dx.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def rolling_high(x: pd.Series, n: int) -> pd.Series:
    return x.rolling(n, min_periods=n).max()


def rolling_low(x: pd.Series, n: int) -> pd.Series:
    return x.rolling(n, min_periods=n).min()


def local_time(index: pd.DatetimeIndex, tz: str = NY_TZ) -> pd.DatetimeIndex:
    return index.tz_convert(tz)


def minutes_of_day(index: pd.DatetimeIndex) -> np.ndarray:
    return (index.hour * 60 + index.minute).to_numpy()


def parse_hhmm(s: str) -> int:
    hh, mm = s.split(":")
    return int(hh) * 60 + int(mm)


def confirmed_fractal_swings(high: np.ndarray, low: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Most recent *confirmed* fractal swing high/low as of each bar.

    A swing high at bar j is a high strictly greater than the ``n`` highs on
    each side. It is only confirmed at bar j + n (when the right-hand bars have
    closed), so the returned arrays at bar t contain the latest swing whose
    confirmation bar is <= t. This avoids the classic look-ahead in fractal
    indicators.
    """
    size = len(high)
    last_sh = np.full(size, np.nan)
    last_sl = np.full(size, np.nan)
    cur_sh = np.nan
    cur_sl = np.nan
    for t in range(size):
        j = t - n
        if j - n >= 0:
            hj = high[j]
            if hj > high[j - n:j].max() and hj > high[j + 1:t + 1].max():
                cur_sh = hj
            lj = low[j]
            if lj < low[j - n:j].min() and lj < low[j + 1:t + 1].min():
                cur_sl = lj
        last_sh[t] = cur_sh
        last_sl[t] = cur_sl
    return last_sh, last_sl
