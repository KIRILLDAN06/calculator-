"""Independent risk controls that can override any strategy.

The same :class:`RiskManager` is used by the backtest engine and the paper
trader. Behaviour of each control (documented in research/risk_management.md):

==========================  ==================================================
control                     behaviour when breached
==========================  ==================================================
risk_per_trade              position size = risk budget / stop distance
max_leverage                notional capped at max_leverage x equity
max_order_notional          notional capped
max_participation           notional capped at share of prior bar's volume
min_order_qty               order rejected if size rounds below minimum
max_open_positions          new entry rejected
max_trades_per_day          new entry rejected until next UTC day
max_daily_loss              (equity incl. unrealised) -> no new entries until next UTC day
max_drawdown                kill switch: flatten (retried until flat) + permanent halt
max_consecutive_losses      cooldown: no entries for N bars
max_data_staleness_s        stale market data -> entry rejected
max_spread_bps              entry rejected when quoted spread too wide
max_slippage_bps            realised fill slippage too large -> halt new entries
min_bar_quote_volume        entry rejected on illiquid bars
emergency stop              flatten + permanent halt
==========================  ==================================================
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

NS_PER_DAY = 86_400_000_000_000


def utc_day(ts: pd.Timestamp) -> int:
    """UTC day number (``Timestamp.value`` is always nanoseconds)."""
    return int(ts.value // NS_PER_DAY)


@dataclass
class Decision:
    approved: bool
    qty: float = 0.0
    reason: str = ""


@dataclass
class RiskState:
    day: int | None = None
    day_start_equity: float = 0.0
    peak_equity: float = 0.0
    trades_today: int = 0
    consecutive_losses: int = 0
    cooldown_until: str | None = None  # ISO timestamp
    day_halted: bool = False
    halted: bool = False
    halt_reason: str = ""
    flatten_required: bool = False  # kill switch / emergency stop: keep flattening until flat
    events: list[dict[str, Any]] = field(default_factory=list)


class RiskManager:
    def __init__(self, risk_cfg: dict[str, Any], exec_cfg: dict[str, Any], initial_equity: float,
                 bar_seconds: int) -> None:
        self.cfg = dict(risk_cfg)
        self.exec = dict(exec_cfg)
        self.bar_seconds = int(bar_seconds)
        self.state = RiskState(day_start_equity=initial_equity, peak_equity=initial_equity)
        self.drawdown_halt = bool(self.cfg.get("drawdown_halt", True))

    # ------------------------------------------------------------------ events
    def _event(self, ts: pd.Timestamp, kind: str, detail: str) -> None:
        self.state.events.append({"ts": ts.isoformat(), "kind": kind, "detail": detail})

    def halt(self, ts: pd.Timestamp, reason: str, flatten: bool = False) -> None:
        """Stop opening positions (permanent until manual reset).

        ``flatten=True`` additionally requires the caller to flatten; the requirement persists
        (and ``on_bar`` keeps returning ``"flatten"``) until it is cleared manually, so a failed
        flattening order is retried rather than forgotten.
        """
        if not self.state.halted:
            self.state.halted = True
            self.state.halt_reason = reason
            self._event(ts, "HALT", reason)
        if flatten and not self.state.flatten_required:
            self.state.flatten_required = True
            self._event(ts, "FLATTEN", reason)

    def emergency_stop(self, ts: pd.Timestamp, reason: str = "emergency stop") -> None:
        self.halt(ts, reason, flatten=True)

    def start_day(self, day: int, equity: float) -> None:
        """Roll the UTC day *before* any fill of its first bar (equity = previous close)."""
        st = self.state
        if day != st.day:
            st.day = day
            st.day_start_equity = equity
            st.trades_today = 0
            st.day_halted = False

    def on_bar(self, ts: pd.Timestamp, equity: float, day_key: int | None = None) -> list[str]:
        """Update peak/daily-loss bookkeeping with mark-to-market equity at a bar close.

        ``day_key`` is the bar's UTC day number (computed from ``ts`` when omitted; callers
        should already have called :meth:`start_day` at the bar's open). Returns
        ``["flatten"]`` for as long as a kill switch or emergency stop requires flattening.
        """
        st = self.state
        self.start_day(utc_day(ts) if day_key is None else day_key, equity)
        st.peak_equity = max(st.peak_equity, equity)
        dd = 1.0 - equity / st.peak_equity if st.peak_equity > 0 else 0.0
        if dd >= float(self.cfg["max_drawdown"]) and self.drawdown_halt and not st.flatten_required:
            self.halt(ts, f"max drawdown {dd:.2%} >= {float(self.cfg['max_drawdown']):.2%}", flatten=True)
        if st.day_start_equity > 0 and not st.day_halted:
            day_loss = 1.0 - equity / st.day_start_equity
            if day_loss >= float(self.cfg["max_daily_loss"]):
                st.day_halted = True
                self._event(ts, "DAY_HALT", f"daily loss {day_loss:.2%}")
        if equity <= 0 and not st.flatten_required:
            self.halt(ts, "equity <= 0", flatten=True)
        return ["flatten"] if st.flatten_required else []

    def on_trade_closed(self, ts: pd.Timestamp, net_pnl: float) -> None:
        st = self.state
        if net_pnl < 0:
            st.consecutive_losses += 1
            if st.consecutive_losses >= int(self.cfg["max_consecutive_losses"]):
                until = ts + pd.Timedelta(seconds=self.bar_seconds * int(self.cfg["cooldown_bars_after_loss_streak"]))
                st.cooldown_until = until.isoformat()
                st.consecutive_losses = 0
                self._event(ts, "COOLDOWN", f"loss streak; no entries until {st.cooldown_until}")
        else:
            st.consecutive_losses = 0

    def on_fill(self, ts: pd.Timestamp, slippage_bps: float) -> None:
        if slippage_bps > float(self.cfg["max_slippage_bps"]):
            self.halt(ts, f"slippage {slippage_bps:.1f}bps > {float(self.cfg['max_slippage_bps'])}bps")

    def on_entry_filled(self) -> None:
        self.state.trades_today += 1

    # ----------------------------------------------------------- entry checks
    def check_entry(
        self,
        *,
        ts: pd.Timestamp,
        side: int,
        ref_price: float,
        stop_price: float,
        equity: float,
        open_positions: int,
        bar_quote_volume: float | None,
        data_age_s: float = 0.0,
        spread_bps: float | None = None,
    ) -> Decision:
        """Approve and size a new entry, or reject it with a reason. Pure w.r.t. state."""
        c, st = self.cfg, self.state
        # Limits apply to the UTC day in which the order would fill (ts = fill time).
        same_day = utc_day(ts) == st.day
        if st.halted:
            return Decision(False, reason=f"halted: {st.halt_reason}")
        if st.day_halted and same_day:
            return Decision(False, reason="daily loss limit reached")
        if st.cooldown_until is not None and ts < pd.Timestamp(st.cooldown_until):
            return Decision(False, reason="loss-streak cooldown")
        if side not in (1, -1):
            return Decision(False, reason="invalid side")
        if side == -1 and not c.get("allow_short", True):
            return Decision(False, reason="shorting disabled")
        if open_positions >= int(c["max_open_positions"]):
            return Decision(False, reason="max open positions")
        if same_day and st.trades_today >= int(c["max_trades_per_day"]):
            return Decision(False, reason="max trades per day")
        if data_age_s > float(c["max_data_staleness_s"]):
            return Decision(False, reason=f"stale data ({data_age_s:.0f}s)")
        if spread_bps is not None and spread_bps > float(c["max_spread_bps"]):
            return Decision(False, reason=f"spread {spread_bps:.1f}bps too wide")
        if not (math.isfinite(ref_price) and math.isfinite(stop_price)) or ref_price <= 0 or equity <= 0:
            return Decision(False, reason="invalid price/equity")
        if bar_quote_volume is not None and bar_quote_volume < float(c.get("min_bar_quote_volume", 0.0)):
            return Decision(False, reason="illiquid bar")
        per_unit_risk = (ref_price - stop_price) * side
        if per_unit_risk <= 0:
            return Decision(False, reason="stop on wrong side of entry")

        qty = float(c["risk_per_trade"]) * equity / per_unit_risk
        caps = [float(c["max_leverage"]) * equity / ref_price, float(c["max_order_notional"]) / ref_price]
        if bar_quote_volume is not None:
            caps.append(float(self.exec["max_participation"]) * bar_quote_volume / ref_price)
        qty = min([qty, *caps])
        lot = int(self.exec["lot_decimals"])
        qty = math.floor(qty * 10**lot) / 10**lot
        if qty < float(self.exec["min_order_qty"]):
            return Decision(False, reason="size below exchange minimum")
        return Decision(True, qty=qty, reason="ok")

    # ------------------------------------------------------------ persistence
    def to_dict(self) -> dict[str, Any]:
        st = self.state
        return {k: getattr(st, k) for k in st.__dataclass_fields__ if k != "events"} | {
            "events": st.events[-200:]
        }

    def load_dict(self, d: dict[str, Any]) -> None:
        for k, v in d.items():
            if hasattr(self.state, k):
                setattr(self.state, k, v)
