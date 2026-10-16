"""Paper trader: runs a strategy on a (live or replayed) feed against a simulated exchange.

Safety properties (each covered by tests/test_paper.py and tests/test_failures.py):

* Never submits real-money orders: it only talks to :class:`SimulatedExchange`.
* Strategy logic is identical to backtesting (same ``Strategy.generate``) and
  every entry passes the same :class:`RiskManager`.
* Deterministic client order ids (strategy + signal bar + side) plus an
  idempotent exchange make resubmission after a timeout or restart safe.
* State is persisted atomically after every step; on restart the trader
  reloads it and reconciles position and open orders with the exchange
  before doing anything else. A mismatch halts new entries and raises an alert.
* Stale, missing or malformed market data -> no new entries (exchange-side
  protective stops keep working).
* An emergency-stop file flattens and halts permanently.

Usage::

    python -m qtrade.paper_trade --config configs/paper.yaml --replay-days 30
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from qtrade.data.bars import timeframe_minutes
from qtrade.execution.feeds import FeedError, clean_feed_bars
from qtrade.execution.orders import (
    TERMINAL,
    ExchangeError,
    ExchangeTimeout,
    Order,
    OrderRejected,
    OrderStatus,
    RateLimited,
)
from qtrade.execution.simulator import SimulatedExchange
from qtrade.risk import RiskManager
from qtrade.strategies.base import Strategy

log = logging.getLogger("qtrade.paper")


class Feed(Protocol):
    def fetch(self, now: pd.Timestamp) -> pd.DataFrame: ...


class Alerter:
    """Writes alerts as JSON lines (and to the log). Hook point for chat/webhook delivery."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self.sent: list[dict[str, Any]] = []

    def __call__(self, level: str, msg: str, ts: pd.Timestamp | None = None, **extra: Any) -> None:
        rec = {"ts": (ts or pd.Timestamp.now(tz="UTC")).isoformat(), "level": level, "msg": msg, **extra}
        self.sent.append(rec)
        getattr(log, "warning" if level != "info" else "info")("ALERT %s: %s", level, msg)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as fh:
                fh.write(json.dumps(rec) + "\n")


@dataclass
class StepReport:
    now: str
    new_bars: int = 0
    actions: list[str] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)


class PaperTrader:
    def __init__(
        self,
        cfg: dict[str, Any],
        strategy: Strategy,
        feed: Feed,
        exchange: SimulatedExchange,
        state_path: str | Path,
        alerter: Alerter | None = None,
        window_bars: int | None = None,
        kill_file: str | Path | None = None,
        exchange_state_path: str | Path | None = None,
    ) -> None:
        if cfg.get("mode") == "live" or cfg.get("live_trading", {}).get("enabled"):
            raise RuntimeError("PaperTrader refuses live configuration; it never trades real money")
        if not isinstance(exchange, SimulatedExchange):
            raise TypeError("PaperTrader only accepts a SimulatedExchange")
        self.cfg = cfg
        self.strategy = strategy
        self.feed = feed
        self.ex = exchange
        self.tf_min = timeframe_minutes(strategy.timeframe)
        self.td = pd.Timedelta(minutes=self.tf_min)
        self.state_path = Path(state_path)
        self.ex_state_path = Path(exchange_state_path) if exchange_state_path else None
        self.alert = alerter or Alerter()
        self.window_bars = window_bars
        self.kill_file = Path(kill_file) if kill_file else None
        self.risk = RiskManager(cfg["risk"], cfg["execution"], float(cfg["capital"]["initial_equity"]),
                                bar_seconds=self.tf_min * 60)
        self.state: dict[str, Any] = {
            "last_bar": None, "fill_cursor": 0, "seen_fills": [], "orders": {}, "position": None,
            "trades": [], "pending_entry": None, "reconcile_ok": True,
        }
        self._load()

    # ---------------------------------------------------------------- state
    def _load(self) -> None:
        if self.state_path.exists():
            saved = json.loads(self.state_path.read_text())
            self.state.update(saved["trader"])
            self.risk.load_dict(saved["risk"])
            log.info("restored paper state from %s (last bar %s)", self.state_path, self.state["last_bar"])
        if self.ex_state_path is not None:
            self.ex.load(self.ex_state_path)

    def save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"trader": self.state, "risk": self.risk.to_dict()}, default=str))
        tmp.replace(self.state_path)
        if self.ex_state_path is not None:
            self.ex.save(self.ex_state_path)

    # -------------------------------------------------------------- helpers
    def _submit(self, order: Order, rep: StepReport) -> Order | None:
        """Submit with idempotent client id; on timeout mark UNKNOWN for reconciliation."""
        self.state["orders"][order.client_id] = order.to_dict()
        try:
            ack = self.ex.submit_order(order)
        except ExchangeTimeout:
            self.state["orders"][order.client_id]["status"] = str(OrderStatus.UNKNOWN)
            rep.alerts.append(f"submit timeout {order.client_id}")
            self.alert("warning", f"order submit timed out, state unknown: {order.client_id}")
            return None
        except RateLimited:
            del self.state["orders"][order.client_id]
            rep.alerts.append(f"rate limited {order.client_id}")
            self.alert("warning", f"rate limited; will retry: {order.client_id}")
            return None
        except OrderRejected as exc:
            self.state["orders"][order.client_id]["status"] = str(OrderStatus.REJECTED)
            rep.alerts.append(f"rejected {order.client_id}: {exc}")
            self.alert("warning", f"order rejected {order.client_id}: {exc}")
            return None
        self.state["orders"][order.client_id] = ack.to_dict()
        rep.actions.append(f"submitted {order.tag} {order.client_id}")
        return ack

    def _reconcile_unknown(self, rep: StepReport) -> None:
        """Resolve orders whose submission outcome is unknown, before sending anything new."""
        for cid, od in list(self.state["orders"].items()):
            if od["status"] != str(OrderStatus.UNKNOWN):
                continue
            remote = self.ex.get_order(cid)
            if remote is not None:
                self.state["orders"][cid] = remote.to_dict()
                rep.actions.append(f"reconciled {cid}: exists ({remote.status})")
            else:
                self.state["orders"][cid]["status"] = str(OrderStatus.REJECTED)
                self.state["orders"][cid]["reason"] = "not found after timeout"
                rep.actions.append(f"reconciled {cid}: not on exchange")
                if od.get("tag") == "exit" and self.state["position"] is not None:
                    self._submit_exit("retry_exit", rep, suffix="R")

    def _ingest_fills(self, rep: StepReport) -> None:
        fills, cursor = self.ex.fills_since(int(self.state["fill_cursor"]))
        seen = set(self.state["seen_fills"])
        for f in fills:
            if f.fill_id in seen:
                rep.alerts.append(f"duplicate fill event {f.fill_id} ignored")
                continue
            seen.add(f.fill_id)
            self._apply_fill(f, rep)
        self.state["fill_cursor"] = cursor
        self.state["seen_fills"] = sorted(seen)[-5000:]
        for o in self.ex.open_orders():
            self.state["orders"][o.client_id] = o.to_dict()
        terminal = {str(s) for s in TERMINAL}
        for cid, od in list(self.state["orders"].items()):
            if od["status"] in terminal or od["status"] == str(OrderStatus.UNKNOWN):
                continue
            remote = self.ex.get_order(cid)
            if remote is not None:
                self.state["orders"][cid] = remote.to_dict()

    def _apply_fill(self, f: Any, rep: StepReport) -> None:
        pos = self.state["position"]
        ts = pd.Timestamp(f.ts)
        if f.liquidity == "taker" and f.ref_price and math.isfinite(f.ref_price) and f.ref_price > 0:
            self.risk.on_fill(ts, abs(f.price / f.ref_price - 1) * 1e4)
        if pos is None or pos["qty"] == 0:
            parent = self.state["orders"].get(f.client_id, {})
            meta = parent.get("meta", {})
            self.state["position"] = {
                "side": f.side, "qty": f.qty, "entry_price": f.price, "entry_ts": f.ts,
                "entry_ref": f.ref_price, "fees": f.fee, "entry_id": f.client_id,
                "stop": meta.get("stop"), "stop_initial": meta.get("stop"), "target": meta.get("target"),
                "max_hold": meta.get("max_hold"), "entry_type": parent.get("order_type", "?"),
                "exit_qty": 0.0, "exit_value": 0.0, "exit_ref_value": 0.0,
            }
            self.risk.on_entry_filled()
            self.state["pending_entry"] = None
            rep.actions.append(f"entry fill {f.side:+d} {f.qty} @ {f.price:.2f}")
            return
        if f.side == pos["side"]:  # further fills of the entry order
            tot = pos["qty"] + f.qty
            pos["entry_price"] = (pos["entry_price"] * pos["qty"] + f.price * f.qty) / tot
            pos["qty"] = tot
            pos["fees"] += f.fee
            return
        pos["exit_qty"] += f.qty
        pos["exit_value"] += f.qty * f.price
        pos["exit_ref_value"] += f.qty * f.ref_price
        pos["fees"] += f.fee
        pos["last_exit_id"] = f.client_id
        if pos["exit_qty"] + 1e-12 >= pos["qty"]:
            exit_px = pos["exit_value"] / pos["exit_qty"]
            fin = self.ex.financing_between(pos["entry_ts"], f.ts)
            net = pos["side"] * pos["qty"] * (exit_px - pos["entry_price"]) - pos["fees"] - fin
            risk_usd = pos["qty"] * abs(pos["entry_price"] - pos["stop_initial"]) if pos["stop_initial"] else math.nan
            reason = {"-SL": "stop", "-TP": "target"}.get(f.client_id[-3:], pos.get("exit_reason", "exit"))
            self.state["trades"].append({
                "entry_time": pos["entry_ts"], "exit_time": f.ts, "side": pos["side"], "qty": pos["qty"],
                "entry_price": pos["entry_price"], "exit_price": exit_px, "exit_reason": reason,
                "fees": pos["fees"], "financing": fin, "net_pnl": net,
                "r_multiple": net / risk_usd if risk_usd else math.nan,
            })
            self.risk.on_trade_closed(ts, net)
            self.state["position"] = None
            for cid, od in self.state["orders"].items():  # cancel leftover bracket orders
                if od.get("reduce_only") and od["status"] not in {str(s) for s in TERMINAL}:
                    self.ex.cancel_order(cid)
            rep.actions.append(f"position closed ({reason}) net {net:.2f}")

    def _reconcile_position(self, rep: StepReport) -> bool:
        pos = self.state["position"]
        internal = 0.0 if pos is None else pos["side"] * (pos["qty"] - pos["exit_qty"])
        remote = self.ex.position()
        ok = abs(internal - remote) <= 1e-8
        if not ok:
            self.state["reconcile_ok"] = False
            msg = f"position mismatch: internal {internal} vs exchange {remote}"
            rep.alerts.append(msg)
            self.alert("critical", msg)
            self.risk.halt(pd.Timestamp.now(tz="UTC"), "reconciliation mismatch (unexpected position)")
        return ok

    def _submit_exit(self, reason: str, rep: StepReport, suffix: str = "X") -> None:
        pos = self.state["position"]
        if pos is None:
            return
        cid = f"{pos['entry_id']}-{suffix}"
        existing = self.state["orders"].get(cid)
        if existing and existing["status"] not in {str(OrderStatus.REJECTED)}:
            return  # exit already working (idempotent)
        for sfx in ("-SL", "-TP"):
            self.ex.cancel_order(pos["entry_id"] + sfx)
        pos["exit_reason"] = reason
        remaining = round(pos["qty"] - pos["exit_qty"], int(self.cfg["execution"]["lot_decimals"]))
        if remaining <= 0:
            return
        self._submit(Order(client_id=cid, side=-pos["side"], qty=remaining, order_type="market",
                           reduce_only=True, tag="exit"), rep)

    # ------------------------------------------------------------------ step
    def step(self, now: pd.Timestamp) -> StepReport:
        rep = StepReport(now=now.isoformat())
        cfg_r = self.cfg["risk"]

        if self.kill_file is not None and self.kill_file.exists() and not self.risk.state.halted:
            self.risk.emergency_stop(now, f"emergency stop file {self.kill_file}")
            self.alert("critical", "emergency stop triggered: flattening and halting", now)
            self._submit_exit("emergency_stop", rep)

        try:
            raw = self.feed.fetch(now)
        except FeedError as exc:
            rep.alerts.append(f"feed error: {exc}")
            self.alert("warning", f"market data unavailable: {exc}", now)
            self.save()
            return rep
        bars, problems = clean_feed_bars(raw)
        for p in problems:
            rep.alerts.append(f"data: {p}")
            self.alert("warning", f"market data problem: {p}", now)
        bars = bars[bars.index + self.td <= now]  # completed bars only
        if bars.empty:
            self.save()
            return rep
        last = self.state["last_bar"]
        new = bars if last is None else bars[bars.index > pd.Timestamp(last)]
        rep.new_bars = len(new)

        # 1. exchange processes new bars (paper exchange driven by market data)
        for ts, row in new.iterrows():
            self.ex.process_bar(ts, row["open"], row["high"], row["low"], row["close"])
        self._reconcile_unknown(rep)
        self._ingest_fills(rep)
        recon_ok = self._reconcile_position(rep)

        latest_ts = bars.index[-1]
        age_s = (now - (latest_ts + self.td)).total_seconds()
        stale = age_s > float(cfg_r["max_data_staleness_s"])
        if stale:
            rep.alerts.append(f"stale data: last bar closed {age_s:.0f}s ago")
            self.alert("warning", f"stale market data ({age_s:.0f}s); no new entries", now)

        if rep.new_bars == 0:
            self.save()
            return rep
        latest = new.iloc[-1]
        equity = self.ex.equity(float(latest["close"]))
        if self.risk.on_bar(latest_ts, equity) and self.state["position"] is not None:
            self.alert("critical", f"kill switch: {self.risk.state.halt_reason}", now)
            self._submit_exit("kill_switch", rep)

        # 2. strategy on completed bars (same code path as the backtest)
        window = bars if self.window_bars is None else bars.iloc[-self.window_bars:]
        sig = self.strategy.generate(window).iloc[-1]
        pos = self.state["position"]
        if rep.new_bars > 1:
            rep.alerts.append(f"caught up {rep.new_bars} bars; only the latest bar may trigger entries")

        if pos is not None:
            sl_id = pos["entry_id"] + "-SL"
            trail = sig["trail_long"] if pos["side"] == 1 else sig["trail_short"]
            if not math.isnan(trail) and pos["stop"] is not None:
                new_stop = max(pos["stop"], trail) if pos["side"] == 1 else min(pos["stop"], trail)
                if new_stop != pos["stop"] and self.ex.amend_price(sl_id, new_stop):
                    pos["stop"] = new_stop
            held = int((latest_ts - pd.Timestamp(pos["entry_ts"])) / self.td) + 1
            if bool(sig["exit"]):
                self._submit_exit("signal_exit", rep)
            elif pos.get("max_hold") is not None and not math.isnan(pos["max_hold"]) and held >= pos["max_hold"]:
                self._submit_exit("time", rep)
        if bool(sig["exit"]) and self.state["pending_entry"]:
            self.ex.cancel_order(self.state["pending_entry"])
            self.state["pending_entry"] = None

        side = int(sig["entry"])
        pending = self.state["pending_entry"]
        if pending is not None:
            o = self.ex.get_order(pending)
            if o is None or o.status in TERMINAL:
                self.state["pending_entry"] = None
        if side != 0:
            if stale or not recon_ok:
                rep.actions.append("entry skipped: stale data or reconciliation failure")
            elif self.state["position"] is not None or self.state["pending_entry"] is not None:
                rep.actions.append("entry skipped: position or order already open")
            else:
                self._enter(side, sig, latest_ts, latest, equity, age_s, rep)
        self.state["last_bar"] = latest_ts.isoformat()
        self.save()
        return rep

    def _enter(self, side: int, sig: pd.Series, ts: pd.Timestamp, bar: pd.Series, equity: float,
               age_s: float, rep: StepReport) -> None:
        is_lim = not math.isnan(sig["limit_price"])
        dec_p = int(self.cfg["execution"]["price_decimals"])
        if is_lim:
            scale = 10**dec_p
            ref = (math.floor(sig["limit_price"] * scale) if side == 1 else math.ceil(sig["limit_price"] * scale)) / scale
        else:
            ref = float(bar["close"])
        qv = float(bar["quote_volume"]) if "quote_volume" in bar else None
        fresh = bool(bar.get("complete", True)) and int(bar.get("n_active", 1)) > 0
        d = self.risk.check_entry(ts=ts + self.td, side=side, ref_price=ref, stop_price=float(sig["stop"]),
                                  equity=equity, open_positions=0, bar_quote_volume=qv,
                                  data_age_s=max(age_s, 0.0) if fresh else 1e9)
        if not d.approved:
            rep.actions.append(f"entry rejected by risk: {d.reason}")
            return
        cid = f"{self.strategy.name}-{ts:%Y%m%dT%H%M}-{'L' if side == 1 else 'S'}"
        if cid in self.state["orders"]:
            rep.actions.append(f"entry {cid} already submitted (idempotent)")
            return
        meta = {"stop": float(sig["stop"]),
                "target": None if math.isnan(sig["target"]) else float(sig["target"]),
                "max_hold": None if math.isnan(sig["max_hold"]) else float(sig["max_hold"])}
        order = Order(client_id=cid, side=side, qty=d.qty, order_type="limit" if is_lim else "market",
                      price=ref if is_lim else None, tag="entry", meta=meta,
                      expire_ts=(ts + self.td * (int(sig["expiry_bars"]) + 1)).isoformat() if is_lim else None)
        if self._submit(order, rep) is not None:
            self.state["pending_entry"] = cid

    # ------------------------------------------------------------------- run
    def run_replay(self, start: pd.Timestamp, end: pd.Timestamp, latency_s: float = 5.0,
                   bar_index: pd.DatetimeIndex | None = None) -> list[StepReport]:
        """Drive the trader with a simulated clock: one step shortly after each bar close."""
        reports = []
        idx = bar_index if bar_index is not None else self.feed.bars.index  # type: ignore[attr-defined]
        for ts in idx[(idx >= start) & (idx < end)]:
            try:
                reports.append(self.step(ts + self.td + pd.Timedelta(seconds=latency_s)))
            except ExchangeError as exc:  # never crash the loop on exchange trouble
                self.alert("warning", f"exchange error: {exc}")
        return reports
