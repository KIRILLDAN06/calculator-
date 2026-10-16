"""Baselines, controls and simple candidate strategies.

Every parameter default here is an EXPERIMENTAL ASSUMPTION chosen before
testing (see research/candidate_specifications.md), not a tuned value.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from qtrade import features as F
from qtrade.strategies.base import Strategy, empty_signals


class NoTrade(Strategy):
    """No-trade baseline: never emits a signal."""

    name = "no_trade"
    timeframe = "1h"
    default_params: dict = {}

    @property
    def warmup_bars(self) -> int:
        return 1

    def _generate(self, bars: pd.DataFrame) -> pd.DataFrame:
        return empty_signals(bars.index)


class RandomEntry(Strategy):
    """Negative control: random entries with ATR stop / R-multiple target / time exit.

    Random draws are taken row-major from a seeded generator, so the draw for
    bar t does not depend on how many bars follow it (prefix-stable, causal).
    """

    name = "random_entry"
    timeframe = "15min"
    default_params = {
        "seed": 0,
        "prob": 0.01,
        "atr_n": 14,
        "stop_atr": 2.0,
        "rr": 2.0,
        "max_hold": 48,
        "allow_short": True,
        "timeframe": None,  # informational: control runs on the tested strategy's bars
    }

    @property
    def warmup_bars(self) -> int:
        return 3 * int(self.params["atr_n"])

    def _generate(self, bars: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        sig = empty_signals(bars.index)
        rng = np.random.default_rng(int(p["seed"]))
        draws = rng.random((len(bars), 2))
        a = F.atr(bars, int(p["atr_n"])).to_numpy()
        close = bars["close"].to_numpy()
        go = (draws[:, 0] < float(p["prob"])) & np.isfinite(a) & (a > 0)
        direction = np.where(draws[:, 1] < 0.5, 1, -1) if p["allow_short"] else np.ones(len(bars), int)
        entry = np.where(go, direction, 0).astype(np.int8)
        risk = float(p["stop_atr"]) * a
        stop = np.where(entry == 1, close - risk, np.where(entry == -1, close + risk, np.nan))
        target = np.where(entry != 0, close + entry * float(p["rr"]) * risk, np.nan)
        sig["entry"] = entry
        sig["stop"] = stop
        sig["target"] = target
        sig["max_hold"] = np.where(entry != 0, float(p["max_hold"]), np.nan)
        return sig


class DonchianTrend(Strategy):
    """Simple trend-following benchmark (Donchian channel breakout).

    Long when the close crosses above the highest high of the previous
    ``entry_n`` bars; short on the mirror image. Initial stop at
    ``stop_atr`` x ATR; the stop then trails the ``exit_n``-bar channel.
    """

    name = "donchian_trend"
    timeframe = "1h"
    default_params = {"entry_n": 48, "exit_n": 24, "atr_n": 24, "stop_atr": 2.0, "allow_short": True}

    @property
    def warmup_bars(self) -> int:
        return 4 * max(int(self.params["entry_n"]), int(self.params["atr_n"]))

    def _generate(self, bars: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        sig = empty_signals(bars.index)
        close = bars["close"]
        hh = F.rolling_high(bars["high"], int(p["entry_n"])).shift(1)
        ll = F.rolling_low(bars["low"], int(p["entry_n"])).shift(1)
        up = (close > hh) & ~(close.shift(1) > hh.shift(1))
        dn = (close < ll) & ~(close.shift(1) < ll.shift(1))
        a = F.atr(bars, int(p["atr_n"]))
        valid = a.notna() & hh.notna() & ll.notna()
        entry = np.where(up & valid, 1, np.where(dn & valid & bool(p["allow_short"]), -1, 0)).astype(np.int8)
        risk = float(p["stop_atr"]) * a.to_numpy()
        c = close.to_numpy()
        sig["entry"] = entry
        sig["stop"] = np.where(entry == 1, c - risk, np.where(entry == -1, c + risk, np.nan))
        sig["trail_long"] = F.rolling_low(bars["low"], int(p["exit_n"])).to_numpy()
        sig["trail_short"] = F.rolling_high(bars["high"], int(p["exit_n"])).to_numpy()
        return sig


class BollingerMeanReversion(Strategy):
    """Bollinger/z-score mean reversion with an ADX range filter.

    Long when the z-score of close vs. SMA(n) crosses below -z_entry while
    ADX < adx_max (weak trend); target = SMA at signal time, stop = stop_atr x
    ATR, time exit after max_hold bars. Short is the mirror image.
    """

    name = "bollinger_mr"
    timeframe = "15min"
    default_params = {
        "n": 20,
        "z_entry": 2.5,
        "adx_n": 14,
        "adx_max": 25.0,
        "atr_n": 14,
        "stop_atr": 2.0,
        "max_hold": 16,
        "allow_short": True,
    }

    @property
    def warmup_bars(self) -> int:
        return 6 * max(int(self.params["n"]), int(self.params["adx_n"]), int(self.params["atr_n"]))

    def _generate(self, bars: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        sig = empty_signals(bars.index)
        close = bars["close"]
        mid = F.sma(close, int(p["n"]))
        z = F.zscore(close, int(p["n"]))
        ze = float(p["z_entry"])
        ranging = F.adx(bars, int(p["adx_n"])) < float(p["adx_max"])
        a = F.atr(bars, int(p["atr_n"]))
        long_e = (z < -ze) & ~(z.shift(1) < -ze) & ranging & a.notna()
        short_e = (z > ze) & ~(z.shift(1) > ze) & ranging & a.notna() & bool(p["allow_short"])
        entry = np.where(long_e, 1, np.where(short_e, -1, 0)).astype(np.int8)
        c = close.to_numpy()
        risk = float(p["stop_atr"]) * a.to_numpy()
        m = mid.to_numpy()
        # Target must lie beyond the entry reference; drop degenerate signals.
        ok = ((entry == 1) & (m > c)) | ((entry == -1) & (m < c))
        entry = np.where(ok, entry, 0).astype(np.int8)
        sig["entry"] = entry
        sig["stop"] = np.where(entry == 1, c - risk, np.where(entry == -1, c + risk, np.nan))
        sig["target"] = np.where(entry != 0, m, np.nan)
        sig["max_hold"] = np.where(entry != 0, float(p["max_hold"]), np.nan)
        return sig


class IntradayMomentum(Strategy):
    """Crypto adaptation of 'market intraday momentum' (first half-hour -> last half-hour).

    Uses 30-minute bars on the UTC day. At the close of the penultimate
    half-hour (23:30 UTC), go in the direction of the day's first half-hour
    return (00:00-00:30 UTC); in mode ``both`` the penultimate half-hour must
    agree. Hold one bar (exit 00:00 UTC). Stop at ``stop_atr`` x ATR.
    """

    name = "intraday_momentum"
    timeframe = "30min"
    default_params = {"mode": "first", "atr_n": 48, "stop_atr": 2.0, "allow_short": True}

    @property
    def warmup_bars(self) -> int:
        return 3 * int(self.params["atr_n"])

    def _generate(self, bars: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        sig = empty_signals(bars.index)
        idx = bars.index
        mod = F.minutes_of_day(idx)
        day = idx.normalize()
        o = bars["open"].to_numpy()
        c = bars["close"].to_numpy()
        bar_ret = c / o - 1.0
        first = pd.Series(np.where(mod == 0, bar_ret, np.nan), index=idx)
        # First half-hour return of the same UTC day, available from 00:30 onward.
        r_first = first.groupby(day).transform("max").to_numpy()
        is_signal_bar = mod == 23 * 60  # bar 23:00-23:30 closes at 23:30
        has_first = pd.Series(mod == 0, index=idx).groupby(day).transform("any").to_numpy()
        direction = np.sign(r_first)
        if p["mode"] == "both":
            direction = np.where(np.sign(bar_ret) == direction, direction, 0)
        elif p["mode"] != "first":
            raise ValueError("mode must be 'first' or 'both'")
        a = F.atr(bars, int(p["atr_n"])).to_numpy()
        go = is_signal_bar & has_first & np.isfinite(a) & (a > 0) & np.isfinite(direction)
        entry = np.where(go, direction, 0)
        if not p["allow_short"]:
            entry = np.where(entry > 0, entry, 0)
        entry = np.nan_to_num(entry).astype(np.int8)
        risk = float(p["stop_atr"]) * a
        sig["entry"] = entry
        sig["stop"] = np.where(entry == 1, c - risk, np.where(entry == -1, c + risk, np.nan))
        sig["max_hold"] = np.where(entry != 0, 1.0, np.nan)
        return sig
