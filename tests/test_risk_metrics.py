"""Layer B: risk controls (independently of any strategy) and performance statistics."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from qtrade.backtest.engine import BacktestResult
from qtrade.backtest.metrics import (
    compute_metrics,
    daily_returns,
    max_drawdown_duration_days,
    sharpe,
    sortino,
)
from qtrade.backtest.stats import (
    bootstrap_sharpe,
    deflated_sharpe_ratio,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
    stationary_bootstrap_indices,
)
from qtrade.config import load_config
from qtrade.risk import RiskManager

T0 = pd.Timestamp("2024-01-01 00:00", tz="UTC")


def rm(**risk):
    cfg = load_config(overrides={"risk": risk})
    return RiskManager(cfg["risk"], cfg["execution"], 10_000.0, bar_seconds=3600)


def check(r, **kw):
    args = dict(ts=T0, side=1, ref_price=100.0, stop_price=95.0, equity=10_000.0, open_positions=0,
                bar_quote_volume=1e12, data_age_s=0.0)
    args.update(kw)
    return r.check_entry(**args)


def test_position_sizing_and_rounding():
    d = check(rm(risk_per_trade=0.01))
    assert d.approved and d.qty == pytest.approx(20.0)        # 100 USD risk / 5 USD per unit
    d = check(rm(risk_per_trade=0.01), stop_price=99.999)
    assert d.qty == pytest.approx(100.0)                     # leverage 1.0 cap
    d = check(rm(risk_per_trade=0.01), ref_price=33.333, stop_price=30.0)
    assert d.qty == math.floor(d.qty * 1e8) / 1e8            # 8-decimal lot floor


@pytest.mark.parametrize("kw,reason", [
    ({"ref_price": 2e6, "stop_price": 1e6, "equity": 100.0}, "minimum"),
    ({"side": 1, "stop_price": 105.0}, "wrong side"),
    ({"side": 0}, "invalid side"),
    ({"open_positions": 1}, "max open positions"),
    ({"data_age_s": 999.0}, "stale"),
    ({"spread_bps": 80.0}, "spread"),
    ({"ref_price": float("nan")}, "invalid"),
    ({"equity": -5.0}, "invalid"),
])
def test_entry_rejections(kw, reason):
    d = check(rm(), **kw)
    assert not d.approved and reason in d.reason


def test_shorting_disabled_and_illiquid():
    assert "shorting" in check(rm(allow_short=False), side=-1, stop_price=105).reason
    assert "illiquid" in check(rm(min_bar_quote_volume=1e6), bar_quote_volume=10.0).reason


def test_daily_loss_blocks_until_next_day():
    r = rm(max_daily_loss=0.02)
    r.on_bar(T0, 10_000)
    r.on_bar(T0 + pd.Timedelta(hours=1), 9_790)       # -2.1% intraday (incl. unrealised)
    assert "daily loss" in check(r).reason
    r.on_bar(T0 + pd.Timedelta(days=1), 9_790)        # new UTC day resets
    assert check(r).approved


def test_drawdown_kill_switch_flattens_and_is_permanent():
    r = rm(max_drawdown=0.10)
    assert r.on_bar(T0, 10_000) == []
    r.on_bar(T0 + pd.Timedelta(hours=1), 11_000)
    assert r.on_bar(T0 + pd.Timedelta(hours=2), 9_850) == ["flatten"]   # -10.45% from peak
    assert r.on_bar(T0 + pd.Timedelta(hours=3), 9_900) == ["flatten"]   # keeps requiring flat
    assert r.state.halted
    r.on_bar(T0 + pd.Timedelta(days=3), 12_000)
    assert "halted" in check(r).reason                 # stays halted until manual reset
    assert any(e["kind"] == "HALT" for e in r.state.events)


def test_drawdown_halt_can_be_disabled_for_research():
    r = rm(max_drawdown=0.10, drawdown_halt=False)
    r.on_bar(T0, 10_000)
    assert r.on_bar(T0 + pd.Timedelta(hours=1), 5_000) == []
    assert not r.state.halted
    r.on_bar(T0 + pd.Timedelta(days=1), 5_000)   # next day: daily-loss block resets
    assert check(r).approved


def test_consecutive_losses_cooldown_and_reset():
    r = rm(max_consecutive_losses=3, cooldown_bars_after_loss_streak=10)
    for _ in range(3):
        r.on_trade_closed(T0, -10.0)
    assert "cooldown" in check(r, ts=T0 + pd.Timedelta(hours=5)).reason
    assert check(r, ts=T0 + pd.Timedelta(hours=10)).approved
    r.on_trade_closed(T0, -1.0)
    r.on_trade_closed(T0, +1.0)
    assert r.state.consecutive_losses == 0


def test_trades_per_day_and_slippage_halt_and_emergency_stop():
    r = rm(max_trades_per_day=2)
    r.on_bar(T0, 10_000)
    r.on_entry_filled()
    r.on_entry_filled()
    assert "trades per day" in check(r).reason
    assert check(r, ts=T0 + pd.Timedelta(days=1)).approved   # fill on the next UTC day: new quota
    r2 = rm(max_slippage_bps=20)
    r2.on_fill(T0, 35.0)
    assert r2.state.halted and "slippage" in r2.state.halt_reason
    r3 = rm()
    r3.emergency_stop(T0, "operator")
    assert "operator" in check(r3).reason
    assert r3.on_bar(T0, 10_000) == ["flatten"] and r3.on_bar(T0 + pd.Timedelta(hours=1), 10_000) == ["flatten"]


def test_risk_state_persistence_roundtrip():
    r = rm(max_consecutive_losses=2, cooldown_bars_after_loss_streak=5)
    r.on_bar(T0, 10_000)
    r.on_trade_closed(T0, -1)
    r.on_trade_closed(T0, -1)
    r2 = rm(max_consecutive_losses=2, cooldown_bars_after_loss_streak=5)
    r2.load_dict(r.to_dict())
    assert r2.state.cooldown_until == r.state.cooldown_until
    assert "cooldown" in check(r2).reason


# -------------------------------------------------------------------- metrics


def _result(equity: list[float], trades: list[dict] | None = None, freq="1D") -> BacktestResult:
    idx = pd.date_range("2024-01-01", periods=len(equity), freq=freq, tz="UTC")
    cols = ["side", "qty", "entry_price", "exit_price", "net_pnl", "fees", "financing", "slippage_cost",
            "r_multiple", "bars_held"]
    tr = pd.DataFrame(trades or [], columns=cols)
    return BacktestResult(equity=pd.Series(equity, index=idx), position=pd.Series(0.0, index=idx),
                          trades=tr, rejected=pd.DataFrame(columns=["ts", "side", "reason"]), events=[],
                          strategy="t", timeframe=freq, initial_equity=equity[0])


def test_drawdown_sharpe_sortino_known_values():
    res = _result([100, 120, 90, 130, 125])
    m = compute_metrics(res)
    assert m["max_drawdown"] == pytest.approx(90 / 120 - 1)
    assert max_drawdown_duration_days(res.equity) == pytest.approx(2.0)   # 01-02 peak -> recovered 01-04
    r = np.array([0.01, -0.005, 0.02, -0.01, 0.003])
    assert sharpe(r) == pytest.approx(r.mean() / r.std(ddof=1) * math.sqrt(365))
    assert sortino(r) == pytest.approx(r.mean() / math.sqrt(np.mean(np.minimum(r, 0) ** 2)) * math.sqrt(365))
    assert math.isnan(sharpe(np.zeros(10)))
    dr = daily_returns(res.equity, 100)
    assert dr.iloc[1] == pytest.approx(0.2)


def test_trade_statistics_profit_factor_expectancy():
    trades = [
        {"side": 1, "qty": 1, "entry_price": 100, "exit_price": 110, "net_pnl": 10, "fees": 1, "financing": 0,
         "slippage_cost": 0.5, "r_multiple": 2.0, "bars_held": 2},
        {"side": -1, "qty": 1, "entry_price": 100, "exit_price": 105, "net_pnl": -5, "fees": 1, "financing": 0.2,
         "slippage_cost": 0.5, "r_multiple": -1.0, "bars_held": 4},
        {"side": 1, "qty": 1, "entry_price": 100, "exit_price": 102, "net_pnl": 2, "fees": 1, "financing": 0,
         "slippage_cost": 0, "r_multiple": 0.4, "bars_held": 1},
    ]
    m = compute_metrics(_result([100, 101, 107], trades))
    assert m["win_rate"] == pytest.approx(2 / 3)
    assert m["profit_factor"] == pytest.approx(12 / 5)
    assert m["expectancy_usd"] == pytest.approx(7 / 3)
    assert m["expectancy_r"] == pytest.approx(1.4 / 3)
    assert m["total_costs"] == pytest.approx(3 + 0.2 + 1.0)
    assert m["gross_return"] == pytest.approx((107 - 100 + 4.2) / 100)
    assert m["long_trades"] == 2 and m["short_trades"] == 1
    assert m["avg_win_loss_ratio"] == pytest.approx(6 / 5)


def test_psr_dsr_properties():
    assert probabilistic_sharpe_ratio(0.1, 500, 0.0, 3.0, 0.1) == pytest.approx(0.5)
    assert probabilistic_sharpe_ratio(0.2, 500, 0.0, 3.0, 0.0) > 0.99
    assert expected_max_sharpe(1, 0.01) == 0.0
    assert expected_max_sharpe(100, 0.01) > expected_max_sharpe(10, 0.01) > 0
    rng = np.random.default_rng(1)
    good = rng.normal(0.003, 0.01, 1000)
    d1 = deflated_sharpe_ratio(good, n_trials=1)
    d33 = deflated_sharpe_ratio(good, n_trials=33)
    assert d1["dsr"] == pytest.approx(d1["psr"]) and d33["dsr"] < d1["dsr"]


def test_bootstrap_ci_and_pvalue():
    rng = np.random.default_rng(2)
    strong = rng.normal(0.004, 0.01, 800)
    b1 = bootstrap_sharpe(strong, n_boot=500, seed=0)
    b2 = bootstrap_sharpe(strong, n_boot=500, seed=0)
    assert b1 == b2                                 # reproducible
    assert b1["lo"] < b1["sr"] < b1["hi"] and b1["lo"] > 0 and b1["p_value"] < 0.01
    noise = rng.normal(0.0, 0.01, 800)
    assert bootstrap_sharpe(noise, n_boot=500, seed=0)["p_value"] > 0.05
    assert math.isnan(bootstrap_sharpe(np.ones(10))["sr"])


def test_stationary_bootstrap_indices_shape_and_blocks():
    ix = stationary_bootstrap_indices(1000, 10.0, np.random.default_rng(0), n_boot=50)
    assert ix.shape == (50, 1000) and ix.min() >= 0 and ix.max() < 1000
    breaks = (np.diff(ix, axis=1) != 1) & (np.diff(ix, axis=1) != -999)
    mean_block = ix.size / (breaks.sum() + ix.shape[0])
    assert 7 < mean_block < 13
