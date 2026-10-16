"""Layer B/D: backtest engine against hand-calculated examples.

Each expected value below was worked out by hand (shown in comments) and is
an independent check of the engine's fills, costs and accounting.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from conftest import make_bars, random_walk_bars, signal_frame
from qtrade.backtest.engine import buy_and_hold, run_backtest


def _long(sig, i, stop, target=np.nan, limit=np.nan, expiry=1, max_hold=np.nan):
    sig.iloc[i, sig.columns.get_loc("entry")] = 1
    sig.iloc[i, sig.columns.get_loc("stop")] = stop
    sig.iloc[i, sig.columns.get_loc("target")] = target
    sig.iloc[i, sig.columns.get_loc("limit_price")] = limit
    sig.iloc[i, sig.columns.get_loc("expiry_bars")] = expiry
    sig.iloc[i, sig.columns.get_loc("max_hold")] = max_hold


def _short(sig, i, stop, target=np.nan, max_hold=np.nan):
    _long(sig, i, stop, target, max_hold=max_hold)
    sig.iloc[i, sig.columns.get_loc("entry")] = -1


def test_market_entry_next_open_and_target_zero_cost(cfg):
    bars = make_bars([(100, 101, 99, 100), (101, 105, 99, 104), (104, 111, 103, 108), (108, 109, 107, 108)])
    sig = signal_frame(bars)
    _long(sig, 0, stop=95, target=110)
    res = run_backtest(bars, sig, cfg, timeframe="1h")
    t = res.trades.iloc[0]
    # qty = 1% * 10_000 / (close0 100 - stop 95) = 20; fills at bar-1 OPEN (101), not bar-0 close
    assert t.qty == pytest.approx(20)
    assert t.entry_price == pytest.approx(101)
    assert t.entry_time == bars.index[1]
    assert t.exit_reason == "target" and t.exit_price == pytest.approx(110)
    assert t.net_pnl == pytest.approx(20 * (110 - 101))  # 180
    assert res.equity.iloc[-1] == pytest.approx(10_180)


def test_costs_hand_calculated(cost_cfg):
    bars = make_bars([(100, 101, 99, 100), (100, 105, 99, 104), (104, 111, 103, 108), (108, 109, 107, 108)])
    sig = signal_frame(bars)
    _long(sig, 0, stop=95, target=110)
    t = run_backtest(bars, sig, cost_cfg, timeframe="1h").trades.iloc[0]
    # entry: 100 * (1 + 10bp) = 100.1, taker 0.4% -> 20*100.1*0.004 = 8.008
    # exit at target: limit, maker 0.2%, no slippage -> 20*110*0.002 = 4.4
    assert t.entry_price == pytest.approx(100.1)
    assert t.fees == pytest.approx(8.008 + 4.4)
    assert t.gross_pnl == pytest.approx(200.0)
    assert t.slippage_cost == pytest.approx(2.0)
    assert t.net_pnl == pytest.approx(20 * (110 - 100.1) - 12.408)  # 185.592


def test_stop_gap_fills_at_worse_open(cfg):
    bars = make_bars([(100, 101, 99, 100), (100, 102, 98, 101), (90, 92, 88, 91), (91, 92, 90, 91)])
    sig = signal_frame(bars)
    _long(sig, 0, stop=95)
    t = run_backtest(bars, sig, cfg, timeframe="1h").trades.iloc[0]
    assert t.exit_reason == "stop"
    assert t.exit_price == pytest.approx(90)          # open below stop -> filled at open
    assert t.net_pnl == pytest.approx(20 * (90 - 100))
    assert t.r_multiple == pytest.approx(-2.0)


def test_stop_and_target_same_bar_assumes_stop(cfg):
    bars = make_bars([(100, 101, 99, 100), (100, 112, 94, 105), (105, 106, 104, 105)])
    sig = signal_frame(bars)
    _long(sig, 0, stop=95, target=110)
    t = run_backtest(bars, sig, cfg, timeframe="1h").trades.iloc[0]
    assert t.exit_reason == "stop" and t.net_pnl == pytest.approx(-100)


def test_limit_entry_requires_trade_through_and_ignores_target_on_fill_bar(cfg):
    bars = make_bars([
        (100, 101, 99, 100),
        (100, 101, 98, 100),     # touches 98 only -> no fill
        (100, 105, 97.5, 104),   # trades through 98 -> fill; high 105 > target but ignored on fill bar
        (104, 106, 103, 105),    # target 104 hit
        (105, 106, 104, 105),
    ])
    sig = signal_frame(bars)
    _long(sig, 0, stop=95, target=104, limit=98, expiry=2)
    t = run_backtest(bars, sig, cfg, timeframe="1h").trades.iloc[0]
    assert t.entry_type == "limit" and t.entry_time == bars.index[2] and t.entry_price == pytest.approx(98)
    assert t.exit_time == bars.index[3] and t.exit_reason == "target"
    qty = np.floor(100 / 3 * 1e8) / 1e8
    assert t.qty == pytest.approx(qty)
    assert t.net_pnl == pytest.approx(qty * 6)


def test_limit_entry_expires(cfg):
    bars = make_bars([(100, 101, 99, 100), (100, 101, 98.5, 100), (100, 101, 98.5, 100), (99, 100, 97, 98)])
    sig = signal_frame(bars)
    _long(sig, 0, stop=95, limit=98, expiry=2)  # active on bars 1-2 only
    res = run_backtest(bars, sig, cfg, timeframe="1h")
    assert res.trades.empty


def test_short_financing_and_time_exit_hand_calculated(cost_cfg):
    bars = make_bars([(100, 101, 99, 100)] * 5)
    sig = signal_frame(bars)
    _short(sig, 0, stop=105, max_hold=2)
    t = run_backtest(bars, sig, cost_cfg, timeframe="1h").trades.iloc[0]
    # qty 20; entry 100*(1-0.001)=99.9; fees 20*99.9*(0.004+0.0002)=8.3916
    # financing: 0.0002/4h * 1h = 0.00005 * 20 * 100 = 0.1 per bar, bars 1 and 2 -> 0.2
    # time exit after 2 bars at bar-3 open 100*(1+0.001)=100.1; fee 20*100.1*0.004 = 8.008
    assert t.exit_reason == "time" and t.exit_time == bars.index[3]
    assert t.financing == pytest.approx(0.2)
    assert t.fees == pytest.approx(8.3916 + 8.008)
    assert t.net_pnl == pytest.approx(-20 * (100.1 - 99.9) - 16.3996 - 0.2)


def test_exit_signal_and_tighten_only_trailing_stop(cfg):
    bars = make_bars([(100, 101, 99, 100), (100, 103, 99, 102), (102, 104, 101, 103), (103, 104, 102, 103),
                      (103, 104, 102, 103)])
    sig = signal_frame(bars)
    _long(sig, 0, stop=95)
    sig.iloc[1, sig.columns.get_loc("trail_long")] = 99.5   # tightens 95 -> 99.5
    sig.iloc[2, sig.columns.get_loc("trail_long")] = 90.0   # looser: ignored
    sig.iloc[2, sig.columns.get_loc("exit")] = True
    res = run_backtest(bars, sig, cfg, timeframe="1h")
    t = res.trades.iloc[0]
    assert t.exit_reason == "signal_exit" and t.exit_time == bars.index[3] and t.exit_price == pytest.approx(103)

    bars2 = bars.copy()
    bars2.iloc[2] = [102, 104, 99.4, 103, 100, 1e12, 60, 60, True]
    sig2 = signal_frame(bars2)
    _long(sig2, 0, stop=95)
    sig2.iloc[1, sig2.columns.get_loc("trail_long")] = 99.5
    t2 = run_backtest(bars2, sig2, cfg, timeframe="1h").trades.iloc[0]
    assert t2.exit_reason == "stop" and t2.exit_price == pytest.approx(99.5)


def test_sizing_caps_leverage_and_participation(cfg):
    bars = make_bars([(100, 101, 99, 100), (100, 101, 99.95, 100), (100, 101, 99, 100)])
    sig = signal_frame(bars)
    _long(sig, 0, stop=99.9)  # risk sizing would give 1000 BTC
    t = run_backtest(bars, sig, cfg, timeframe="1h").trades.iloc[0]
    assert t.qty == pytest.approx(100)  # leverage 1.0 -> 10_000 / 100

    bars.loc[bars.index[0], "quote_volume"] = 50_000.0
    t = run_backtest(bars, sig, cfg, timeframe="1h").trades.iloc[0]
    assert t.qty == pytest.approx(25)   # 5% of 50,000 USD traded / 100


def test_stale_bar_cannot_trigger_entry(cfg):
    bars = make_bars([(100, 101, 99, 100), (100, 101, 99, 100), (100, 101, 99, 100)])
    bars.loc[bars.index[0], "complete"] = False
    sig = signal_frame(bars)
    _long(sig, 0, stop=95)
    res = run_backtest(bars, sig, cfg, timeframe="1h")
    assert res.trades.empty
    assert "stale" in res.rejected.iloc[0].reason


def test_max_trades_per_day(cfg):
    cfg["risk"]["max_trades_per_day"] = 2
    bars = make_bars([(100, 101, 99, 100)] * 24, tf="1h")
    sig = signal_frame(bars)
    for i in range(0, 22, 2):
        _long(sig, i, stop=95, max_hold=1)
    res = run_backtest(bars, sig, cfg, timeframe="1h")
    assert len(res.trades) == 2
    assert (res.rejected.reason == "max trades per day").any()


def test_no_trading_outside_window_and_flat_at_end(cfg):
    bars = random_walk_bars(400, tf="1h", seed=1)
    sig = signal_frame(bars)
    _long(sig, 10, stop=bars.close.iloc[10] * 0.5)        # before window: ignored
    _long(sig, 300, stop=bars.close.iloc[300] * 0.5)      # inside, never stopped
    res = run_backtest(bars, sig, cfg, start=bars.index[100], timeframe="1h")
    assert len(res.trades) == 1 and res.trades.iloc[0].exit_reason == "end"
    assert res.position.iloc[-1] == 0
    assert res.equity.index[0] == bars.index[100]


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_accounting_identity_and_reproducibility(cost_cfg, seed):
    bars = random_walk_bars(3000, tf="15min", seed=seed)
    rng = np.random.default_rng(seed)
    sig = signal_frame(bars)
    for i in np.flatnonzero(rng.random(len(bars)) < 0.03):
        c = bars.close.iloc[i]
        if rng.random() < 0.5:
            _long(sig, i, stop=c * 0.99, target=c * 1.02, max_hold=20)
        else:
            _short(sig, i, stop=c * 1.01, target=c * 0.98, max_hold=20)
    r1 = run_backtest(bars, sig, cost_cfg, timeframe="15min")
    r2 = run_backtest(bars, sig, cost_cfg, timeframe="15min")
    pd.testing.assert_frame_equal(r1.trades, r2.trades)
    pd.testing.assert_series_equal(r1.equity, r2.equity)
    assert len(r1.trades) > 20
    # final equity = initial + sum of trade net P&L (all positions closed at end)
    assert r1.equity.iloc[-1] == pytest.approx(10_000 + r1.trades.net_pnl.sum(), abs=1e-6)
    # costs are always non-negative and included
    assert (r1.trades.fees > 0).all() and (r1.trades.slippage_cost >= -1e-9).all()
    # position never exceeds leverage cap at entry
    assert (r1.trades.qty * r1.trades.entry_price <= r1.trades.equity_at_entry * 1.0 * 1.002 + 1e-6).all()


def test_buy_and_hold_benchmark(cfg, cost_cfg):
    bars = make_bars([(100, 101, 99, 100), (100, 120, 99, 110), (110, 130, 105, 125)])
    r = buy_and_hold(bars, cfg)
    assert r.equity.iloc[-1] == pytest.approx(10_000 * 125 / 100)
    rc = buy_and_hold(bars, cost_cfg)
    qty = 10_000 / (100.1 * 1.004)
    assert rc.equity.iloc[-1] == pytest.approx(qty * 125 * 0.999 * 0.996)
