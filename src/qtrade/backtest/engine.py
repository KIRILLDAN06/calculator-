"""Event-driven, bar-by-bar backtest engine (single instrument, no pyramiding).

Execution model (all assumptions are conservative and configurable):

* Signals evaluated at the close of bar t act at bar t+1 or later.
* Market orders fill at the next bar's open, moved adversely by
  ``slippage_bps``; taker fee charged on notional.
* Resting limit orders (entries and take-profits) fill only if price trades
  *through* the limit (strictly beyond it) and fill at the limit price with the
  maker fee and no slippage. A limit entry is invalid once it expires.
* Stops are stop-market orders: when the bar's range touches the stop the
  position exits at ``min(open, stop)`` for longs (``max`` for shorts), i.e.
  gaps are filled at the worse open price, then moved by slippage; taker fee.
* If stop and target are both inside one bar, the stop is assumed to fill first.
  On the bar a limit entry fills, the target is ignored (order unknowable).
* A market entry always fills; if the open gapped beyond its stop the stop
  exits on the same bar at the open (worse price).
* Shorts pay the margin opening fee and pro-rata rollover every bar.
* Bars that are incomplete or had no trades are treated as stale data: no new
  entries are approved from them.
* Any open position is closed at the final bar's close (taker fee + slippage).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from qtrade.data.bars import timeframe_minutes
from qtrade.features import epoch_ns
from qtrade.risk import RiskManager

TRADE_COLUMNS = [
    "entry_time", "exit_time", "side", "qty", "entry_ref", "entry_price", "exit_ref", "exit_price",
    "stop_initial", "target", "entry_type", "exit_reason", "bars_held", "gross_pnl", "fees",
    "financing", "slippage_cost", "net_pnl", "risk_usd", "r_multiple", "equity_at_entry",
]


@dataclass
class BacktestResult:
    equity: pd.Series
    position: pd.Series
    trades: pd.DataFrame
    rejected: pd.DataFrame
    events: list[dict[str, Any]]
    strategy: str
    timeframe: str
    initial_equity: float
    config: dict[str, Any] = field(repr=False, default_factory=dict)


def _round_limit(price: float, side: int, decimals: int) -> float:
    """Round a limit price to exchange precision in the conservative direction."""
    scale = 10**decimals
    return math.floor(price * scale) / scale if side == 1 else math.ceil(price * scale) / scale


def run_backtest(
    bars: pd.DataFrame,
    signals: pd.DataFrame,
    cfg: dict[str, Any],
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
    strategy_name: str = "strategy",
    timeframe: str | None = None,
) -> BacktestResult:
    """Simulate ``signals`` on ``bars`` within [start, end).

    ``bars`` may include history before ``start`` (indicator warm-up); signals
    before ``start`` are ignored.
    """
    if not signals.index.equals(bars.index):
        raise ValueError("signals must be aligned to bars")
    idx = bars.index
    if timeframe is None:
        timeframe = f"{int(np.median(np.diff(epoch_ns(idx))) // 60_000_000_000)}min"
    tf = timeframe
    bar_min = timeframe_minutes(tf)
    i0 = 0 if start is None else int(idx.searchsorted(pd.Timestamp(start, tz="UTC") if isinstance(start, str) else start))
    i1 = len(idx) if end is None else int(idx.searchsorted(pd.Timestamp(end, tz="UTC") if isinstance(end, str) else end))
    if i1 - i0 < 2:
        raise ValueError("backtest window must contain at least 2 bars")

    costs, ex = cfg["costs"], cfg["execution"]
    fee_t, fee_m = float(costs["taker_fee"]), float(costs["maker_fee"])
    slip = float(costs["slippage_bps"]) / 1e4
    short_open = float(costs["short_open_fee"])
    roll_per_bar = float(costs["short_rollover_per_4h"]) * bar_min / 240.0
    px_dec = int(ex["price_decimals"])
    initial = float(cfg["capital"]["initial_equity"])

    risk = RiskManager(cfg["risk"], ex, initial, bar_seconds=bar_min * 60)

    o = bars["open"].to_numpy(float)
    h = bars["high"].to_numpy(float)
    lo = bars["low"].to_numpy(float)
    c = bars["close"].to_numpy(float)
    qv = bars["quote_volume"].to_numpy(float) if "quote_volume" in bars else np.full(len(bars), np.inf)
    fresh = np.ones(len(bars), bool)
    if "complete" in bars:
        fresh &= bars["complete"].to_numpy(bool)
    if "n_active" in bars:
        fresh &= bars["n_active"].to_numpy() > 0
    day_key = epoch_ns(idx) // 86_400_000_000_000

    s_entry = signals["entry"].to_numpy()
    s_stop = signals["stop"].to_numpy(float)
    s_tgt = signals["target"].to_numpy(float)
    s_lim = signals["limit_price"].to_numpy(float)
    s_exp = signals["expiry_bars"].to_numpy()
    s_hold = signals["max_hold"].to_numpy(float)
    s_exit = signals["exit"].to_numpy(bool)
    s_tl = signals["trail_long"].to_numpy(float)
    s_ts = signals["trail_short"].to_numpy(float)

    cash = initial
    pos: dict[str, Any] | None = None
    pend_mkt: dict[str, Any] | None = None
    pend_lim: dict[str, Any] | None = None
    pend_exit: str | None = None
    trades: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    eq_out = np.empty(i1 - i0)
    pos_out = np.empty(i1 - i0)
    bar_td = pd.Timedelta(minutes=bar_min)

    def open_position(i: int, side: int, qty: float, ref: float, fill: float, fee_rate: float,
                      stop: float, target: float, max_hold: float, entry_type: str, equity: float) -> None:
        nonlocal cash, pos
        notional = qty * fill
        fees = notional * fee_rate + (notional * short_open if side == -1 else 0.0)
        cash -= side * qty * fill + fees
        pos = {
            "side": side, "qty": qty, "entry_i": i, "entry_ref": ref, "entry_price": fill,
            "stop": stop, "stop_initial": stop, "target": target, "max_hold": max_hold,
            "fees": fees, "financing": 0.0, "entry_type": entry_type, "equity_at_entry": equity,
            "risk_usd": qty * abs(fill - stop),
        }
        risk.on_entry_filled()
        if fill != ref:
            risk.on_fill(idx[i], abs(fill / ref - 1) * 1e4)

    def close_position(i: int, ref: float, fill: float, fee_rate: float, reason: str) -> None:
        nonlocal cash, pos
        assert pos is not None
        side, qty = pos["side"], pos["qty"]
        exit_fee = qty * fill * fee_rate
        cash += side * qty * fill - exit_fee
        fees = pos["fees"] + exit_fee
        gross = side * qty * (ref - pos["entry_ref"])
        realised = side * qty * (fill - pos["entry_price"])
        net = realised - fees - pos["financing"]
        trades.append({
            "entry_time": idx[pos["entry_i"]], "exit_time": idx[i] if reason != "end" else idx[i] + bar_td,
            "side": side, "qty": qty, "entry_ref": pos["entry_ref"], "entry_price": pos["entry_price"],
            "exit_ref": ref, "exit_price": fill, "stop_initial": pos["stop_initial"], "target": pos["target"],
            "entry_type": pos["entry_type"], "exit_reason": reason, "bars_held": i - pos["entry_i"] + 1,
            "gross_pnl": gross, "fees": fees, "financing": pos["financing"],
            "slippage_cost": gross - realised, "net_pnl": net, "risk_usd": pos["risk_usd"],
            "r_multiple": net / pos["risk_usd"] if pos["risk_usd"] > 0 else np.nan,
            "equity_at_entry": pos["equity_at_entry"],
        })
        risk.on_trade_closed(idx[i], net)
        pos = None

    equity = initial
    for i in range(i0, i1):
        # ---- at the open: exits first, then entries
        if pend_exit is not None and pos is not None:
            side = pos["side"]
            close_position(i, o[i], o[i] * (1 - side * slip), fee_t, pend_exit)
        pend_exit = None

        if pend_mkt is not None and pos is None:
            # A market order fills even if the open gapped beyond the stop; the
            # stop check below then exits at the (worse) open on this same bar.
            side = pend_mkt["side"]
            fill = o[i] * (1 + side * slip)
            open_position(i, side, pend_mkt["qty"], o[i], fill, fee_t, pend_mkt["stop"], pend_mkt["target"],
                          pend_mkt["max_hold"], "market", pend_mkt["equity"])
        pend_mkt = None

        lim_fill_now = False
        if pend_lim is not None and pos is None:
            if i > pend_lim["expires"]:
                pend_lim = None
            else:
                side, L = pend_lim["side"], pend_lim["limit"]
                if (side == 1 and lo[i] < L) or (side == -1 and h[i] > L):
                    open_position(i, side, pend_lim["qty"], L, L, fee_m, pend_lim["stop"], pend_lim["target"],
                                  pend_lim["max_hold"], "limit", pend_lim["equity"])
                    pend_lim = None
                    lim_fill_now = True

        # ---- intrabar: stop first (conservative), then target
        if pos is not None:
            side, stop, tgt = pos["side"], pos["stop"], pos["target"]
            if side == 1 and lo[i] <= stop:
                ref = min(o[i], stop)
                close_position(i, ref, ref * (1 - slip), fee_t, "stop")
            elif side == -1 and h[i] >= stop:
                ref = max(o[i], stop)
                close_position(i, ref, ref * (1 + slip), fee_t, "stop")
            elif not lim_fill_now and not math.isnan(tgt) and (
                (side == 1 and h[i] > tgt) or (side == -1 and lo[i] < tgt)
            ):
                close_position(i, tgt, tgt, fee_m, "target")

        # ---- financing, mark to market
        if pos is not None and pos["side"] == -1:
            fin = roll_per_bar * pos["qty"] * c[i]
            pos["financing"] += fin
            cash -= fin
        qty_signed = 0.0 if pos is None else pos["side"] * pos["qty"]
        equity = cash + qty_signed * c[i]
        eq_out[i - i0] = equity
        pos_out[i - i0] = qty_signed
        if risk.on_bar(idx[i], equity, int(day_key[i])) and pos is not None:
            pend_exit = "kill_switch"
        if risk.state.halted:
            pend_lim = None

        if i == i1 - 1:
            break

        # ---- end-of-bar position maintenance (effective next bar)
        if pos is not None:
            if pos["side"] == 1 and not math.isnan(s_tl[i]):
                pos["stop"] = max(pos["stop"], s_tl[i])
            elif pos["side"] == -1 and not math.isnan(s_ts[i]):
                pos["stop"] = min(pos["stop"], s_ts[i])
            if s_exit[i] and pend_exit is None:
                pend_exit = "signal_exit"
            if not math.isnan(pos["max_hold"]) and i - pos["entry_i"] + 1 >= pos["max_hold"] and pend_exit is None:
                pend_exit = "time"
        if s_exit[i]:
            pend_lim = None

        # ---- new entry intent from bar i
        side = int(s_entry[i])
        if side != 0:
            if pos is not None or pend_lim is not None:
                rejected.append({"ts": idx[i], "side": side, "reason": "position or order already open"})
                continue
            is_lim = not math.isnan(s_lim[i])
            ref = _round_limit(s_lim[i], side, px_dec) if is_lim else c[i]
            dec = risk.check_entry(
                ts=idx[i] + bar_td, side=side, ref_price=ref, stop_price=s_stop[i], equity=equity,
                open_positions=0, bar_quote_volume=qv[i], data_age_s=0.0 if fresh[i] else 1e9,
            )
            if not dec.approved:
                rejected.append({"ts": idx[i], "side": side, "reason": dec.reason})
                continue
            order = {"i": i, "side": side, "qty": dec.qty, "stop": s_stop[i], "target": s_tgt[i],
                     "max_hold": s_hold[i], "equity": equity}
            if is_lim:
                order.update(limit=ref, expires=i + int(s_exp[i]))
                pend_lim = order
            else:
                pend_mkt = order

    if pos is not None:
        side = pos["side"]
        close_position(i1 - 1, c[i1 - 1], c[i1 - 1] * (1 - side * slip), fee_t, "end")
        eq_out[-1] = cash
        pos_out[-1] = 0.0

    win = idx[i0:i1]
    return BacktestResult(
        equity=pd.Series(eq_out, index=win, name="equity"),
        position=pd.Series(pos_out, index=win, name="position"),
        trades=pd.DataFrame(trades, columns=TRADE_COLUMNS),
        rejected=pd.DataFrame(rejected, columns=["ts", "side", "reason"]),
        events=list(risk.state.events),
        strategy=strategy_name,
        timeframe=tf,
        initial_equity=initial,
        config=cfg,
    )


def buy_and_hold(bars: pd.DataFrame, cfg: dict[str, Any], start=None, end=None) -> BacktestResult:
    """Benchmark: buy at the first open (taker fee + slippage), hold, sell at the last close."""
    sub = bars
    if start is not None:
        sub = sub[sub.index >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        sub = sub[sub.index < pd.Timestamp(end, tz="UTC")]
    initial = float(cfg["capital"]["initial_equity"])
    fee = float(cfg["costs"]["taker_fee"])
    slip = float(cfg["costs"]["slippage_bps"]) / 1e4
    entry = float(sub["open"].iloc[0]) * (1 + slip)
    qty = initial / (entry * (1 + fee))
    cash = initial - qty * entry * (1 + fee)
    equity = cash + qty * sub["close"]
    exit_px = float(sub["close"].iloc[-1]) * (1 - slip)
    final = cash + qty * exit_px * (1 - fee)
    equity.iloc[-1] = final
    fees = qty * entry * fee + qty * exit_px * fee
    gross = qty * (float(sub["close"].iloc[-1]) - float(sub["open"].iloc[0]))
    trades = pd.DataFrame([{
        "entry_time": sub.index[0], "exit_time": sub.index[-1], "side": 1, "qty": qty,
        "entry_ref": float(sub["open"].iloc[0]), "entry_price": entry, "exit_ref": float(sub["close"].iloc[-1]),
        "exit_price": exit_px, "stop_initial": np.nan, "target": np.nan, "entry_type": "market",
        "exit_reason": "end", "bars_held": len(sub), "gross_pnl": gross, "fees": fees, "financing": 0.0,
        "slippage_cost": gross - qty * (exit_px - entry), "net_pnl": final - initial, "risk_usd": np.nan,
        "r_multiple": np.nan, "equity_at_entry": initial,
    }], columns=TRADE_COLUMNS)
    return BacktestResult(
        equity=equity.rename("equity"), position=pd.Series(qty, index=sub.index, name="position"),
        trades=trades, rejected=pd.DataFrame(columns=["ts", "side", "reason"]), events=[],
        strategy="buy_and_hold", timeframe=pd.infer_freq(sub.index[:10]) or "", initial_equity=initial,
        config=cfg,
    )
