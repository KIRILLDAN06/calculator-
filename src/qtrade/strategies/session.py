"""Session-based intraday strategies (New York session clock, DST-aware).

Every default parameter is an EXPERIMENTAL ASSUMPTION documented in
research/candidate_specifications.md; none is a proven-profitable setting.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from qtrade import features as F
from qtrade.strategies.base import Strategy, empty_signals


def _bar_minutes(index: pd.DatetimeIndex) -> int:
    if len(index) < 2:
        return 5
    return max(1, int(np.median(np.diff(F.epoch_ns(index))) // 60_000_000_000))


def _ny_calendar(index: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(minute-of-day, day key yyyymmdd, weekday) on the New York clock."""
    local = F.local_time(index)
    mod = F.minutes_of_day(local)
    key = (local.year * 10000 + local.month * 100 + local.day).to_numpy()
    return mod, key, local.dayofweek.to_numpy()


def _session_exit(sig: pd.DataFrame, mod: np.ndarray, weekday: np.ndarray, close_min: int, tf: int,
                  weekdays_only: bool) -> None:
    """Flag the bar that ends at the session close so positions exit at that time."""
    ends_at_close = (mod + tf) == close_min
    if weekdays_only:
        ends_at_close &= weekday < 5
    sig["exit"] = ends_at_close


class OpeningRangeBreakout(Strategy):
    """Opening-range breakout on the US equity session clock.

    * Opening range (OR): high/low of bars in [session_open, session_open + or_minutes) ET,
      required to be fully present.
    * Signal: the first bar of the day, after the OR is complete and ending no
      later than ``last_entry``, that *closes* above the OR high (long) or below
      the OR low (short). One signal per day; market entry at the next open.
    * Stop: opposite side of the OR (``stop_mode='opposite'``) or stop_atr x ATR.
    * Target: none (exit at session close) unless ``rr`` is set.
    """

    name = "orb"
    timeframe = "5min"
    default_params = {
        "session_open": "09:30",
        "or_minutes": 15,
        "session_close": "16:00",
        "last_entry": "15:00",
        "stop_mode": "opposite",
        "stop_atr": 1.0,
        "atr_n": 14,
        "rr": None,
        "weekdays_only": True,
        "allow_short": True,
    }

    @property
    def warmup_bars(self) -> int:
        return 600

    def _generate(self, bars: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        sig = empty_signals(bars.index)
        if len(bars) == 0:
            return sig
        tf = _bar_minutes(bars.index)
        mod, key, weekday = _ny_calendar(bars.index)
        open_m = F.parse_hhmm(p["session_open"])
        or_end = open_m + int(p["or_minutes"])
        close_m = F.parse_hhmm(p["session_close"])
        last_m = F.parse_hhmm(p["last_entry"])
        n_or = int(p["or_minutes"]) // tf

        high = bars["high"].to_numpy()
        low = bars["low"].to_numpy()
        close = bars["close"].to_numpy()
        in_or = (mod >= open_m) & (mod < or_end)
        keys = pd.Series(key, index=bars.index)
        or_high = pd.Series(np.where(in_or, high, np.nan), index=bars.index).groupby(keys).transform("max")
        or_low = pd.Series(np.where(in_or, low, np.nan), index=bars.index).groupby(keys).transform("min")
        or_count = pd.Series(in_or.astype(int), index=bars.index).groupby(keys).transform("sum")
        or_high = or_high.to_numpy()
        or_low = or_low.to_numpy()

        eligible = (mod >= or_end) & (mod + tf <= last_m) & (or_count.to_numpy() == n_or)
        if p["weekdays_only"]:
            eligible &= weekday < 5
        long_b = eligible & (close > or_high)
        short_b = eligible & (close < or_low) & bool(p["allow_short"])
        event = long_b | short_b
        first = event & (pd.Series(event.astype(int), index=bars.index).groupby(keys).cumsum().to_numpy() == 1)
        entry = np.where(first & long_b, 1, np.where(first & short_b, -1, 0)).astype(np.int8)

        if p["stop_mode"] == "opposite":
            stop = np.where(entry == 1, or_low, np.where(entry == -1, or_high, np.nan))
        elif p["stop_mode"] == "atr":
            risk = float(p["stop_atr"]) * F.atr(bars, int(p["atr_n"])).to_numpy()
            stop = np.where(entry == 1, close - risk, np.where(entry == -1, close + risk, np.nan))
        else:
            raise ValueError("stop_mode must be 'opposite' or 'atr'")
        ok = ((entry == 1) & (stop < close)) | ((entry == -1) & (stop > close))
        entry = np.where(ok, entry, 0).astype(np.int8)
        sig["entry"] = entry
        sig["stop"] = np.where(entry != 0, stop, np.nan)
        if p["rr"] is not None:
            sig["target"] = np.where(entry != 0, close + entry * float(p["rr"]) * np.abs(close - stop), np.nan)
        # Backstop time exit in case the session-close bar is missing from the data.
        sig["max_hold"] = np.where(entry != 0, np.maximum((close_m - (mod + tf)) // tf, 1), np.nan)
        _session_exit(sig, mod, weekday, close_m, tf, bool(p["weekdays_only"]))
        return sig


class SweepFVG(Strategy):
    """Liquidity sweep -> market-structure shift -> fair-value-gap retracement (SMC / TJR-style).

    This is an operational interpretation of publicly described concepts, not
    any educator's complete or endorsed system. State machine per NY day
    (bearish side shown; bullish is the mirror image):

    1. Liquidity levels known before the window: previous NY-day high (PDH),
       Asia-session high (20:00-24:00 ET prior evening) and London-session high
       (02:00-05:00 ET). A level is *untaken* if price has not traded above it
       between its formation and ``window_start``.
    2. SWEEP: a bar starting inside [window_start, window_end) trades above an
       untaken level; it is *confirmed* if a bar closes back below the level
       within ``reclaim_bars`` bars (else the sweep failed: acceptance).
    3. MSS: within ``mss_bars`` bars after confirmation, a bar closes below the
       most recent confirmed fractal swing low (``swing_n``) that existed when
       the sweep began. Aborts if a bar closes back above the swept level.
    4. FVG: the most recent bearish three-bar gap (low[k-2] > high[k]) formed
       between the sweep bar and the MSS bar. Sell limit at the gap's lower
       edge (``entry='edge'``) or midpoint (``'mid'``), active ``expiry_bars``.
    5. Stop: sweep extreme + ``stop_buffer_bps``; target: ``rr`` x risk;
       flat at session close. At most one setup per day.
    """

    name = "sweep_fvg"
    timeframe = "5min"
    default_params = {
        "asia_start": "20:00",
        "london_start": "02:00",
        "london_end": "05:00",
        "levels": ("pdhl", "asia", "london"),
        "window_start": "09:30",
        "window_end": "11:30",
        "reclaim_bars": 3,
        "mss_bars": 12,
        "swing_n": 2,
        "entry": "edge",
        "expiry_bars": 12,
        "stop_buffer_bps": 5.0,
        "min_risk_bps": 10.0,
        "rr": 2.0,
        "session_close": "16:00",
        "weekdays_only": True,
        "allow_short": True,
    }

    @property
    def warmup_bars(self) -> int:
        return 3 * 288 + 10

    # ---- level computation (vectorised, causal: every level is complete before window_start)
    def _levels(self, bars: pd.DataFrame, mod: np.ndarray, key: np.ndarray) -> pd.DataFrame:
        p = self.params
        high = bars["high"].to_numpy()
        low = bars["low"].to_numpy()
        local_dates = pd.to_datetime(key.astype(str), format="%Y%m%d")
        asia_s = F.parse_hhmm(p["asia_start"])
        lon_s, lon_e = F.parse_hhmm(p["london_start"]), F.parse_hhmm(p["london_end"])
        win_s = F.parse_hhmm(p["window_start"])

        frame = pd.DataFrame({"key": key, "high": high, "low": low, "mod": mod})
        daily = frame.groupby("key").agg(dh=("high", "max"), dl=("low", "min"))
        out = pd.DataFrame(index=daily.index)
        out["pdh"] = daily["dh"].shift(1)
        out["pdl"] = daily["dl"].shift(1)

        # Asia session belongs to the *next* NY date.
        next_key = (local_dates + pd.Timedelta(days=1)).strftime("%Y%m%d").astype(int).to_numpy()
        asia = frame[mod >= asia_s].assign(k=next_key[mod >= asia_s]).groupby("k")
        out["asia_h"] = asia["high"].max()
        out["asia_l"] = asia["low"].min()

        lon = frame[(mod >= lon_s) & (mod < lon_e)].groupby("key")
        out["lon_h"] = lon["high"].max()
        out["lon_l"] = lon["low"].min()

        pre = frame[mod < win_s].groupby("key")  # 00:00 -> window start
        out["pre_h"] = pre["high"].max()
        out["pre_l"] = pre["low"].min()
        post_lon = frame[(mod >= lon_e) & (mod < win_s)].groupby("key")
        out["postlon_h"] = post_lon["high"].max()
        out["postlon_l"] = post_lon["low"].min()
        return out

    def _generate(self, bars: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        sig = empty_signals(bars.index)
        if len(bars) == 0:
            return sig
        tf = _bar_minutes(bars.index)
        mod, key, weekday = _ny_calendar(bars.index)
        lv = self._levels(bars, mod, key)
        high = bars["high"].to_numpy()
        low = bars["low"].to_numpy()
        close = bars["close"].to_numpy()
        sh, sl = F.confirmed_fractal_swings(high, low, int(p["swing_n"]))

        win_s, win_e = F.parse_hhmm(p["window_start"]), F.parse_hhmm(p["window_end"])
        close_m = F.parse_hhmm(p["session_close"])
        use = set(p["levels"])
        reclaim_n, mss_n = int(p["reclaim_bars"]), int(p["mss_bars"])
        buf = float(p["stop_buffer_bps"]) / 1e4
        min_risk = float(p["min_risk_bps"]) / 1e4
        rr = float(p["rr"])
        mid_entry = p["entry"] == "mid"
        if p["entry"] not in ("edge", "mid"):
            raise ValueError("entry must be 'edge' or 'mid'")

        entry = sig["entry"].to_numpy().copy()
        stop_a = sig["stop"].to_numpy().copy()
        tgt_a = sig["target"].to_numpy().copy()
        lim_a = sig["limit_price"].to_numpy().copy()
        exp_a = sig["expiry_bars"].to_numpy().copy()
        hold_a = sig["max_hold"].to_numpy().copy()

        lv_rows = lv.to_dict("index")
        diag = {"days": 0, "days_with_levels": 0, "levels_high": 0, "levels_low": 0, "sweeps": 0,
                "sweeps_confirmed": 0, "mss": 0, "fvg_found": 0, "setups": 0}
        cur_key = None
        highs: list[float] = []
        lows: list[float] = []
        done = True
        bear: dict | None = None
        bull: dict | None = None

        def untaken(row: dict, side: str) -> list[float]:
            out: list[float] = []
            def ok(x: float) -> bool:
                return x is not None and np.isfinite(x)
            if side == "high":
                if "pdhl" in use and ok(row["pdh"]) and ok(row["pre_h"]) and row["pre_h"] < row["pdh"]:
                    out.append(row["pdh"])
                if "asia" in use and ok(row["asia_h"]) and ok(row["pre_h"]) and row["pre_h"] < row["asia_h"]:
                    out.append(row["asia_h"])
                if "london" in use and ok(row["lon_h"]) and ok(row["postlon_h"]) and row["postlon_h"] < row["lon_h"]:
                    out.append(row["lon_h"])
            else:
                if "pdhl" in use and ok(row["pdl"]) and ok(row["pre_l"]) and row["pre_l"] > row["pdl"]:
                    out.append(row["pdl"])
                if "asia" in use and ok(row["asia_l"]) and ok(row["pre_l"]) and row["pre_l"] > row["asia_l"]:
                    out.append(row["asia_l"])
                if "london" in use and ok(row["lon_l"]) and ok(row["postlon_l"]) and row["postlon_l"] > row["lon_l"]:
                    out.append(row["lon_l"])
            return out

        for t in range(len(bars)):
            m = mod[t]
            if key[t] != cur_key:
                cur_key = key[t]
                row = lv_rows.get(cur_key)
                done = row is None or (bool(p["weekdays_only"]) and weekday[t] >= 5)
                highs = untaken(row, "high") if not done else []
                lows = untaken(row, "low") if not done else []
                bear = bull = None
                if not done:
                    diag["days"] += 1
                    diag["days_with_levels"] += bool(highs or lows)
                    diag["levels_high"] += len(highs)
                    diag["levels_low"] += len(lows)
            if done or m < win_s or m + tf >= close_m:
                continue
            in_window = m < win_e

            # ---------------- bearish side: sweep of highs ----------------
            if bool(p["allow_short"]):
                if bear is None and in_window:
                    swept = [lvl for lvl in highs if high[t] > lvl]
                    if swept:
                        highs = [lvl for lvl in highs if lvl not in swept]
                        bear = {"level": max(swept), "start": t, "ext": high[t], "phase": "sweep",
                                "swing": sl[t - 1] if t > 0 else np.nan}
                        diag["sweeps"] += 1
                if bear is not None:
                    bear["ext"] = max(bear["ext"], high[t])
                    if bear["phase"] == "sweep":
                        if close[t] < bear["level"]:
                            bear["phase"], bear["deadline"] = "mss", t + mss_n
                            diag["sweeps_confirmed"] += 1
                            if not np.isfinite(bear["swing"]) or bear["swing"] >= bear["level"]:
                                bear = None
                        elif t - bear["start"] >= reclaim_n:
                            bear = None
                    elif bear["phase"] == "mss":
                        if close[t] > bear["level"] or t > bear["deadline"]:
                            bear = None
                        elif close[t] < bear["swing"]:
                            diag["mss"] += 1
                            setup = self._bear_fvg(high, low, bear["start"], t)
                            if setup is not None:
                                diag["fvg_found"] += 1
                                zl, zh = setup
                                limit = (zl + zh) / 2 if mid_entry else zl
                                stop = bear["ext"] * (1 + buf)
                                if close[t] < limit < stop and (stop - limit) / limit >= min_risk:
                                    entry[t] = -1
                                    lim_a[t], stop_a[t] = limit, stop
                                    tgt_a[t] = limit - rr * (stop - limit)
                                    exp_a[t] = int(p["expiry_bars"])
                                    hold_a[t] = max((close_m - (m + tf)) // tf, 1)
                                    done = True
                                    diag["setups"] += 1
                            bear = None
            if done:
                continue

            # ---------------- bullish side: sweep of lows ----------------
            if bull is None and in_window:
                swept = [lvl for lvl in lows if low[t] < lvl]
                if swept:
                    lows = [lvl for lvl in lows if lvl not in swept]
                    bull = {"level": min(swept), "start": t, "ext": low[t], "phase": "sweep",
                            "swing": sh[t - 1] if t > 0 else np.nan}
                    diag["sweeps"] += 1
            if bull is not None:
                bull["ext"] = min(bull["ext"], low[t])
                if bull["phase"] == "sweep":
                    if close[t] > bull["level"]:
                        bull["phase"], bull["deadline"] = "mss", t + mss_n
                        diag["sweeps_confirmed"] += 1
                        if not np.isfinite(bull["swing"]) or bull["swing"] <= bull["level"]:
                            bull = None
                    elif t - bull["start"] >= reclaim_n:
                        bull = None
                elif bull["phase"] == "mss":
                    if close[t] < bull["level"] or t > bull["deadline"]:
                        bull = None
                    elif close[t] > bull["swing"]:
                        diag["mss"] += 1
                        setup = self._bull_fvg(high, low, bull["start"], t)
                        if setup is not None:
                            diag["fvg_found"] += 1
                            zl, zh = setup
                            limit = (zl + zh) / 2 if mid_entry else zh
                            stop = bull["ext"] * (1 - buf)
                            if close[t] > limit > stop and (limit - stop) / limit >= min_risk:
                                entry[t] = 1
                                lim_a[t], stop_a[t] = limit, stop
                                tgt_a[t] = limit + rr * (limit - stop)
                                exp_a[t] = int(p["expiry_bars"])
                                hold_a[t] = max((close_m - (m + tf)) // tf, 1)
                                done = True
                                diag["setups"] += 1
                        bull = None

        self.diagnostics = diag
        sig["entry"] = entry
        sig["stop"] = stop_a
        sig["target"] = tgt_a
        sig["limit_price"] = lim_a
        sig["expiry_bars"] = exp_a
        sig["max_hold"] = hold_a
        _session_exit(sig, mod, weekday, close_m, tf, bool(p["weekdays_only"]))
        return sig

    @staticmethod
    def _bear_fvg(high: np.ndarray, low: np.ndarray, start: int, t: int) -> tuple[float, float] | None:
        """Most recent bearish FVG (zone_low, zone_high) with all three bars in [start, t]."""
        for k in range(t, start + 1, -1):
            if low[k - 2] > high[k]:
                return high[k], low[k - 2]
        return None

    @staticmethod
    def _bull_fvg(high: np.ndarray, low: np.ndarray, start: int, t: int) -> tuple[float, float] | None:
        """Most recent bullish FVG (zone_low, zone_high) with all three bars in [start, t]."""
        for k in range(t, start + 1, -1):
            if high[k - 2] < low[k]:
                return high[k - 2], low[k]
        return None
