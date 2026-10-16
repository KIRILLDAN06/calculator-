"""Layer B: strategy signal rules on hand-constructed scenarios."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from conftest import make_bars, random_walk_bars
from qtrade.strategies import REGISTRY, make_strategy
from qtrade.strategies.base import empty_signals, validate_signals

NY = "America/New_York"


def _flat_5m(start_et: str, end_et: str, price: float = 102.0, half_range: float = 0.2) -> pd.DataFrame:
    idx = pd.date_range(pd.Timestamp(start_et, tz=NY), pd.Timestamp(end_et, tz=NY), freq="5min",
                        inclusive="left").tz_convert("UTC")
    rows = [(price, price + half_range, price - half_range, price)] * len(idx)
    return make_bars(rows, start=idx[0].isoformat(), tf="5min")


def _set(bars: pd.DataFrame, et: str, o: float, h: float, lo: float, c: float) -> None:
    ts = pd.Timestamp(et, tz=NY).tz_convert("UTC")
    bars.loc[ts, ["open", "high", "low", "close"]] = [o, h, lo, c]


# ----------------------------------------------------------------------------- ORB
@pytest.mark.parametrize("day,utc_open", [("2024-07-10", "13:30"), ("2024-01-10", "14:30")])
def test_orb_long_breakout_dst_aware(day, utc_open):
    bars = _flat_5m(f"{day} 00:00", f"{day} 23:55", price=100.0, half_range=0.1)
    _set(bars, f"{day} 09:30", 100, 101, 99, 100.5)
    _set(bars, f"{day} 09:35", 100.5, 100.8, 99.5, 100.2)
    _set(bars, f"{day} 09:40", 100.2, 100.9, 99.8, 100.1)   # OR: high 101, low 99
    _set(bars, f"{day} 10:00", 100.1, 101.6, 100.0, 101.5)  # first close above OR high
    _set(bars, f"{day} 10:05", 101.5, 101.6, 98.0, 98.5)    # later close below OR low: ignored (1/day)
    sig = make_strategy("orb").generate(bars)
    ents = sig[sig.entry != 0]
    assert len(ents) == 1
    t = ents.index[0]
    assert t.tz_convert(NY).strftime("%H:%M") == "10:00"
    assert (t - pd.Timedelta(minutes=30)).strftime("%H:%M") == utc_open
    row = ents.iloc[0]
    assert row.entry == 1 and row.stop == 99 and np.isnan(row.target)
    exits = sig.index[sig.exit]
    assert [e.tz_convert(NY).strftime("%H:%M") for e in exits] == ["15:55"]  # flat at 16:00 ET


def test_orb_requires_complete_opening_range_and_weekday():
    day = "2024-07-13"  # Saturday
    bars = _flat_5m(f"{day} 00:00", f"{day} 23:55", price=100.0)
    _set(bars, f"{day} 09:30", 100, 101, 99, 100.5)
    _set(bars, f"{day} 10:00", 100.1, 101.6, 100.0, 101.5)
    assert (make_strategy("orb").generate(bars).entry == 0).all()

    day = "2024-07-10"
    bars = _flat_5m(f"{day} 00:00", f"{day} 23:55", price=100.0)
    _set(bars, f"{day} 10:00", 100.1, 101.6, 100.0, 101.5)
    bars = bars.drop(pd.Timestamp(f"{day} 09:35", tz=NY).tz_convert("UTC"))  # OR bar missing
    assert (make_strategy("orb").generate(bars).entry == 0).all()


# ------------------------------------------------------------------------ SweepFVG
def _sweep_day() -> pd.DataFrame:
    bars = _flat_5m("2024-07-08 00:00", "2024-07-10 18:00")
    _set(bars, "2024-07-09 12:00", 102, 110, 101.8, 102)    # previous-day high (PDH) = 110
    _set(bars, "2024-07-09 13:00", 102, 102.2, 95, 102)     # previous-day low (PDL) = 95
    seq = [
        ("09:30", 102.0, 102.5, 101.5, 102.3),
        ("09:35", 102.3, 102.6, 101.2, 101.5),
        ("09:40", 101.5, 101.9, 100.0, 101.6),   # swing low 100 (confirmed at 09:50)
        ("09:45", 101.6, 104.0, 101.4, 103.8),
        ("09:50", 103.8, 106.0, 103.5, 105.8),
        ("09:55", 105.8, 108.0, 105.5, 107.9),
        ("10:00", 107.9, 110.8, 107.5, 109.5),   # sweeps PDH 110, closes back below
        ("10:05", 109.5, 109.6, 106.0, 106.2),
        ("10:10", 106.2, 106.3, 103.0, 103.1),
        ("10:15", 103.1, 103.2, 99.5, 99.8),     # closes below swing low 100 -> MSS; FVG [103.2, 106.0]
    ]
    for hhmm, o, h, lo, c in seq:
        _set(bars, f"2024-07-10 {hhmm}", o, h, lo, c)
    after = bars.index > pd.Timestamp("2024-07-10 10:15", tz=NY)
    bars.loc[after, ["open", "high", "low", "close"]] = [99.8, 99.9, 99.7, 99.8]
    return bars


def test_sweep_fvg_short_setup_hand_constructed():
    s = make_strategy("sweep_fvg")
    sig = s.generate(_sweep_day())
    ents = sig[sig.entry != 0]
    assert len(ents) == 1, s.diagnostics
    t, row = ents.index[0], ents.iloc[0]
    assert t.tz_convert(NY).strftime("%Y-%m-%d %H:%M") == "2024-07-10 10:15"
    assert row.entry == -1
    assert row.limit_price == pytest.approx(103.2)                 # FVG edge nearest price
    assert row.stop == pytest.approx(110.8 * 1.0005)               # sweep extreme + 5 bp
    assert row.target == pytest.approx(103.2 - 2 * (110.8 * 1.0005 - 103.2))
    assert row.expiry_bars == 12
    assert row.max_hold == (16 * 60 - (10 * 60 + 20)) // 5
    assert s.diagnostics["setups"] == 1


def test_sweep_fvg_mid_entry_and_failed_sweep():
    sig = make_strategy("sweep_fvg", {"entry": "mid"}).generate(_sweep_day())
    assert sig[sig.entry != 0].iloc[0].limit_price == pytest.approx((103.2 + 106.0) / 2)

    bars = _sweep_day()
    # Acceptance above the level: closes stay above 110 for > reclaim_bars -> no setup.
    for hhmm in ("10:00", "10:05", "10:10", "10:15"):
        _set(bars, f"2024-07-10 {hhmm}", 110.2, 111.0, 110.1, 110.5)
    assert (make_strategy("sweep_fvg").generate(bars).entry == 0).all()


def test_sweep_fvg_level_already_taken_before_window():
    bars = _sweep_day()
    _set(bars, "2024-07-10 08:00", 102, 110.5, 101.9, 102)   # PDH traded through pre-window
    assert (make_strategy("sweep_fvg").generate(bars).entry == 0).all()


# -------------------------------------------------------------------- other rules
def test_donchian_cross_and_trailing_columns():
    rows = [(100, 101, 99, 100)] * 60 + [(100, 103, 99.5, 102.5)] + [(102.5, 103, 102, 102.7)] * 5
    bars = make_bars(rows, tf="1h")
    sig = make_strategy("donchian_trend", {"entry_n": 48, "exit_n": 24, "atr_n": 24}).generate(bars)
    ents = sig[sig.entry != 0]
    assert list(ents.index) == [bars.index[60]] and ents.iloc[0].entry == 1
    assert sig.trail_long.iloc[61] == pytest.approx(99.0)


def test_bollinger_targets_mean_and_respects_adx_filter():
    bars = random_walk_bars(3000, tf="15min", seed=3)
    s = make_strategy("bollinger_mr", {"adx_max": 100.0})
    sig = s.generate(bars)
    ents = sig[sig.entry != 0]
    assert len(ents) > 5
    mid = bars.close.rolling(20).mean()
    assert np.allclose(ents.target, mid.loc[ents.index])
    strict = make_strategy("bollinger_mr", {"adx_max": 0.0}).generate(bars)
    assert (strict.entry == 0).all()


def test_intraday_momentum_direction_follows_first_half_hour():
    idx = pd.date_range("2024-05-01", periods=48 * 6, freq="30min", tz="UTC")
    rows = []
    for t in idx:
        up = t.day % 2 == 0
        if t.hour == 0 and t.minute == 0:
            rows.append((100, 102, 99.9, 101.5) if up else (100, 100.1, 98, 98.5))
        else:
            rows.append((100, 100.5, 99.5, 100))
    bars = make_bars(rows, start=str(idx[0]), tf="30min")
    sig = make_strategy("intraday_momentum", {"atr_n": 4}).generate(bars)
    ents = sig[sig.entry != 0]
    assert all(t.hour == 23 and t.minute == 0 for t in ents.index)
    assert all((t.day % 2 == 0) == (e == 1) for t, e in zip(ents.index, ents.entry, strict=True))
    assert (ents.max_hold == 1).all()


def test_validate_signals_rejects_bad_frames():
    bars = make_bars([(100, 101, 99, 100)] * 3)
    sig = empty_signals(bars.index)
    sig.iloc[0, sig.columns.get_loc("entry")] = 1
    with pytest.raises(ValueError, match="stop"):
        validate_signals(sig, bars)
    sig.iloc[0, sig.columns.get_loc("stop")] = 101  # above price for a long
    with pytest.raises(ValueError, match="below"):
        validate_signals(sig, bars)
    with pytest.raises(ValueError, match="unknown parameters"):
        make_strategy("orb", {"no_such_param": 1})
    with pytest.raises(KeyError):
        make_strategy("does_not_exist")


@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_every_strategy_handles_tiny_and_empty_input(name):
    strat = make_strategy(name)
    bars = random_walk_bars(5, tf=strat.timeframe)
    out = strat.generate(bars)
    assert len(out) == 5
    out0 = strat.generate(bars.iloc[:0])
    assert len(out0) == 0
