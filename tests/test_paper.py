"""Layers C/F/G: paper trader integration, failure injection and recovery (no network, no real orders)."""

from __future__ import annotations

import pandas as pd
import pytest

from conftest import random_walk_bars
from qtrade.backtest.engine import run_backtest
from qtrade.config import load_config
from qtrade.execution.feeds import ReplayFeed
from qtrade.execution.orders import Order
from qtrade.execution.simulator import SimulatedExchange
from qtrade.paper import Alerter, PaperTrader
from qtrade.strategies import make_strategy

TF = 60


@pytest.fixture
def pcfg():
    return load_config(overrides={
        "mode": "paper",
        "costs": {"taker_fee": 0.004, "maker_fee": 0.002, "slippage_bps": 5.0,
                  "short_open_fee": 0.0002, "short_rollover_per_4h": 0.0002},
        "risk": {"risk_per_trade": 0.01, "max_trades_per_day": 10, "max_daily_loss": 0.5,
                 "max_drawdown": 0.9, "drawdown_halt": False, "max_consecutive_losses": 1000,
                 "cooldown_bars_after_loss_streak": 0},
    })


@pytest.fixture(scope="module")
def bars():
    return random_walk_bars(1400, tf="1h", seed=5, vol=0.006)


def _trader(cfg, bars, tmp_path, faults=None, feed_faults=None, seed=0, name="donchian_trend", **kw):
    ex = SimulatedExchange(cfg, 10_000.0, TF, faults=faults, seed=seed)
    feed = ReplayFeed(bars, TF, faults=feed_faults, seed=seed)
    return PaperTrader(cfg, make_strategy(name), feed, ex, tmp_path / "state.json",
                       Alerter(tmp_path / "alerts.jsonl"), exchange_state_path=tmp_path / "ex.json", **kw)


def _start(bars):
    return bars.index[500]


def test_paper_replay_matches_backtest_trade_for_trade(pcfg, bars, tmp_path):
    strat = make_strategy("donchian_trend")
    bt = run_backtest(bars, strat.generate(bars), pcfg, start=_start(bars), timeframe="1h").trades
    tr = _trader(pcfg, bars, tmp_path)
    tr.run_replay(_start(bars), bars.index[-1] + pd.Timedelta(hours=1))
    pt = pd.DataFrame(tr.state["trades"])
    closed_bt = bt[bt.exit_reason != "end"].reset_index(drop=True)
    assert len(closed_bt) >= 10 and len(pt) == len(closed_bt)
    assert list(pd.to_datetime(pt.entry_time)) == list(closed_bt.entry_time)
    assert list(pd.to_datetime(pt.exit_time)) == list(closed_bt.exit_time)
    assert pt.entry_price.to_numpy() == pytest.approx(closed_bt.entry_price.to_numpy(), rel=1e-12)
    assert pt.exit_price.to_numpy() == pytest.approx(closed_bt.exit_price.to_numpy(), rel=1e-12)
    assert pt.net_pnl.to_numpy() == pytest.approx(closed_bt.net_pnl.to_numpy(), abs=1e-6)
    # internal books == exchange books
    assert tr.ex.position() == pytest.approx(0 if tr.state["position"] is None else
                                             tr.state["position"]["side"] * tr.state["position"]["qty"])
    if tr.state["position"] is None:
        assert tr.ex.equity() == pytest.approx(10_000 + pt.net_pnl.sum(), abs=1e-6)
    assert (pt.fees > 0).all()


def test_restart_resumes_without_duplicates(pcfg, bars, tmp_path):
    end = bars.index[-1] + pd.Timedelta(hours=1)
    mid = bars.index[950]
    ref = _trader(pcfg, bars, tmp_path / "ref")
    ref.run_replay(_start(bars), end)

    a = _trader(pcfg, bars, tmp_path / "run")
    a.run_replay(_start(bars), mid)
    del a                                                   # simulated crash / process exit
    b = _trader(pcfg, bars, tmp_path / "run")               # fresh process, same state files
    assert b.state["last_bar"] is not None
    b.run_replay(mid, end)
    assert b.state["trades"] == ref.state["trades"]
    assert sorted(b.ex.orders) == sorted(ref.ex.orders)     # no duplicate submissions
    # re-running already-processed bars is a no-op
    n_orders = len(b.ex.orders)
    b.run_replay(mid, end)
    assert len(b.ex.orders) == n_orders


def test_emergency_stop_file_flattens_and_halts(pcfg, bars, tmp_path):
    kill = tmp_path / "STOP"
    tr = _trader(pcfg, bars, tmp_path, kill_file=kill)
    tr.run_replay(_start(bars), bars.index[1100])
    # step forward until a position is open, then pull the plug
    i = 1100
    while tr.state["position"] is None and i < len(bars) - 5:
        tr.step(bars.index[i] + pd.Timedelta(hours=1, seconds=5))
        i += 1
    assert tr.state["position"] is not None
    kill.write_text("stop")
    for j in range(i, i + 3):
        tr.step(bars.index[j] + pd.Timedelta(hours=1, seconds=5))
    assert tr.risk.state.halted and tr.ex.position() == 0
    n = len(tr.ex.orders)
    tr.run_replay(bars.index[i + 3], bars.index[-1])
    assert len([o for o in tr.ex.orders.values() if o.tag == "entry"]) == \
        len([o for cid, o in tr.ex.orders.items() if o.tag == "entry" and cid in list(tr.ex.orders)[:n]])
    assert any(a["level"] == "critical" for a in tr.alert.sent)


def test_stale_and_malformed_data_block_entries(pcfg, bars, tmp_path):
    freeze = (str(bars.index[600]), str(bars.index[900]))
    tr = _trader(pcfg, bars, tmp_path, feed_faults={"freeze_between": freeze, "malformed_prob": 0.05,
                                                     "duplicate_prob": 0.05})
    reps = tr.run_replay(_start(bars), bars.index[1000])
    stale_steps = [r for r in reps if any("stale" in a for a in r.alerts)]
    assert len(stale_steps) > 200
    for r in stale_steps:
        assert not any(a.startswith("submitted entry") for a in r.actions)
    assert any("malformed" in a for r in reps for a in r.alerts)
    assert any("duplicate" in a for r in reps for a in r.alerts)
    assert tr._reconcile_position(type(reps[0])(now=reps[-1].now))   # books still consistent


def test_exchange_faults_never_duplicate_or_desync(pcfg, bars, tmp_path):
    faults = {"timeout_prob": 0.15, "timeout_accepts_prob": 0.5, "rate_limit_prob": 0.1,
              "partial_fill_frac": 0.5, "duplicate_fill_prob": 0.2}
    tr = _trader(pcfg, bars, tmp_path, faults=faults, seed=3)
    reps = tr.run_replay(_start(bars), bars.index[-1])
    alerts = [a for r in reps for a in r.alerts]
    assert any("timeout" in a for a in alerts) and any("duplicate fill" in a for a in alerts)
    assert not any("mismatch" in a for a in alerts), "internal position diverged from exchange"
    assert len(tr.state["trades"]) > 0
    ids = [cid for cid in tr.ex.order_seq]
    assert len(ids) == len(set(ids))


def test_unexpected_position_halts_new_entries(pcfg, bars, tmp_path):
    tr = _trader(pcfg, bars, tmp_path)
    tr.run_replay(_start(bars), bars.index[700])
    tr.ex.submit_order(Order(client_id="rogue", side=1, qty=0.01, order_type="market", tag="manual"))
    reps = tr.run_replay(bars.index[700], bars.index[720])
    assert any("mismatch" in a for r in reps for a in r.alerts)
    assert tr.risk.state.halted
    assert any(k in tr.risk.state.halt_reason for k in ("reconciliation", "unexpected fill"))
    assert sum("mismatch" in a["msg"] for a in tr.alert.sent) == 1   # alert once, not every step
    assert all("submitted entry" not in a for r in reps[1:] for a in r.actions)


def test_risk_limit_breach_triggers_kill_switch(pcfg, bars, tmp_path):
    pcfg["risk"].update(max_drawdown=0.005, drawdown_halt=True)
    tr = _trader(pcfg, bars, tmp_path)
    tr.run_replay(_start(bars), bars.index[-1])
    assert tr.risk.state.halted and "drawdown" in tr.risk.state.halt_reason
    assert tr.ex.position() == 0


def test_paper_trader_refuses_live_and_real_exchanges(pcfg, bars, tmp_path):
    live = load_config(overrides={"mode": "live", "live_trading": {"enabled": True}})
    ex = SimulatedExchange(pcfg, 10_000, TF)
    with pytest.raises(RuntimeError, match="refuses live"):
        PaperTrader(live, make_strategy("no_trade"), ReplayFeed(bars, TF), ex, tmp_path / "s.json")
    with pytest.raises(TypeError):
        PaperTrader(pcfg, make_strategy("no_trade"), ReplayFeed(bars, TF), object(), tmp_path / "s.json")


@pytest.mark.parametrize("variant", ["target", "session_close"])
def test_limit_entry_bracket_and_session_exit_match_backtest(pcfg, tmp_path, variant):
    """SweepFVG path: resting limit entry, bracket stop/target, session-close exit."""
    from test_strategies import NY, _set, _sweep_day

    b5 = _sweep_day()
    _set(b5, "2024-07-10 10:20", 99.8, 103.5, 99.7, 103.4)     # retrace trades through 103.2 -> limit fill
    if variant == "target":
        _set(b5, "2024-07-10 10:25", 103.4, 103.5, 95.0, 95.5)
        _set(b5, "2024-07-10 10:30", 95.5, 96.0, 87.0, 87.5)   # through target 87.889 -> exit at target
        after = b5.index > pd.Timestamp("2024-07-10 10:30", tz=NY)
        b5.loc[after, ["open", "high", "low", "close"]] = [87.5, 87.6, 87.4, 87.5]
    else:
        after = b5.index > pd.Timestamp("2024-07-10 10:20", tz=NY)
        b5.loc[after, ["open", "high", "low", "close"]] = [101.0, 101.1, 100.9, 101.0]
    strat = make_strategy("sweep_fvg")
    start = pd.Timestamp("2024-07-10 09:00", tz=NY).tz_convert("UTC")
    bt = run_backtest(b5, strat.generate(b5), pcfg, start=start, timeframe="5min").trades
    assert len(bt) == 1 and bt.iloc[0].entry_type == "limit"
    assert bt.iloc[0].exit_reason == ("target" if variant == "target" else "signal_exit")
    ex = SimulatedExchange(pcfg, 10_000.0, 5)
    tr = PaperTrader(pcfg, make_strategy("sweep_fvg"), ReplayFeed(b5, 5), ex, tmp_path / "s.json")
    tr.run_replay(start, b5.index[-1])
    pt = pd.DataFrame(tr.state["trades"])
    assert len(pt) == 1
    assert pd.Timestamp(pt.entry_time.iloc[0]) == bt.entry_time.iloc[0]
    assert pd.Timestamp(pt.exit_time.iloc[0]) == bt.exit_time.iloc[0]
    assert pt.entry_price.iloc[0] == pytest.approx(103.2)
    assert pt.net_pnl.iloc[0] == pytest.approx(bt.net_pnl.iloc[0], abs=1e-6)


# ------------------------------------------------- audit regressions (2026-10-16)
class _LimitProbe:
    """Strategy stub: a far-away limit entry on every bar (never fills)."""

    name = "limit_probe"
    timeframe = "1h"

    def generate(self, bars):
        from qtrade.strategies.base import empty_signals

        sig = empty_signals(bars.index)
        sig["entry"] = 1
        sig["limit_price"] = (bars["close"] * 0.5).round(1)
        sig["stop"] = bars["close"] * 0.4
        sig["expiry_bars"] = 500
        return sig


def _open_position(tr, bars, start_i=1100):
    i = start_i
    tr.run_replay(_start(bars), bars.index[i])
    while tr.state["position"] is None and i < len(bars) - 10:
        tr.step(bars.index[i] + pd.Timedelta(hours=1, seconds=5))
        i += 1
    assert tr.state["position"] is not None
    return i


def test_emergency_stop_flattens_even_when_already_halted(pcfg, bars, tmp_path):
    kill = tmp_path / "STOP"
    tr = _trader(pcfg, bars, tmp_path, kill_file=kill)
    i = _open_position(tr, bars)
    tr.risk.halt(bars.index[i], "slippage halt (no flatten)")
    kill.write_text("stop")
    for j in range(i, i + 3):
        tr.step(bars.index[j] + pd.Timedelta(hours=1, seconds=5))
    assert tr.ex.position() == 0 and tr.risk.state.flatten_required


def test_flatten_is_retried_after_rejected_exit(pcfg, bars, tmp_path, monkeypatch):
    from qtrade.execution.orders import OrderRejected

    tr = _trader(pcfg, bars, tmp_path)
    i = _open_position(tr, bars)
    real_submit = tr.ex.submit_order
    calls = {"n": 0}

    def flaky(order):
        if order.tag in ("exit", "flatten") and calls["n"] == 0:
            calls["n"] += 1
            raise OrderRejected("simulated reject")
        return real_submit(order)

    monkeypatch.setattr(tr.ex, "submit_order", flaky)
    tr.risk.emergency_stop(bars.index[i], "test kill")
    for j in range(i, i + 4):
        tr.step(bars.index[j] + pd.Timedelta(hours=1, seconds=5))
    assert calls["n"] == 1 and tr.ex.position() == 0


def test_timeout_accepted_entry_never_leads_to_second_entry(pcfg, bars, tmp_path):
    ex = SimulatedExchange(pcfg, 10_000.0, TF, faults={"timeout_prob": 1.0, "timeout_accepts_prob": 1.0})
    tr = PaperTrader(pcfg, _LimitProbe(), ReplayFeed(bars, TF), ex, tmp_path / "s.json")
    for ts in bars.index[600:640]:
        tr.step(ts + pd.Timedelta(hours=1, seconds=5))
        working = [o for o in ex.open_orders() if o.tag == "entry"]
        assert len(working) <= 1, [o.client_id for o in working]
    assert tr.state["pending_entry"] is not None


def test_rogue_position_is_flattened_not_adopted(pcfg, bars, tmp_path):
    kill = tmp_path / "STOP"
    tr = _trader(pcfg, bars, tmp_path, kill_file=kill)
    tr.run_replay(_start(bars), bars.index[700])
    pos_before = tr.state["position"]
    tr.ex.submit_order(Order(client_id="rogue", side=1, qty=0.01, order_type="market", tag="manual"))
    kill.write_text("stop")
    tr.run_replay(bars.index[700], bars.index[706])
    assert tr.ex.position() == 0
    assert tr.state["position"] is None or pos_before is not None
    assert any(cid.startswith("FLATTEN-") or cid.endswith("-K0") for cid in tr.ex.orders)
