"""Simulated (paper) exchange with fault injection.

Fills follow exactly the rules of :mod:`qtrade.backtest.engine` so that paper
trading on replayed data can be checked trade-for-trade against a backtest:

* market orders fill at the next processed bar's open +/- slippage (taker);
* limit orders fill at their price only when the bar trades *through* it (maker);
* stop orders fill at min(open, stop) (sells) / max(open, stop) (buys) +/- slippage;
* entry orders may carry a bracket (``meta['stop']``/``meta['target']``): on fill,
  reduce-only stop and target child orders are created and evaluated on the same
  bar -- stop first; the target is skipped on the bar a *limit* entry fills;
* shorts pay the margin opening fee and pro-rata rollover each bar.

Fault injection (all seeded, default off): request timeouts (order may or may
not be accepted), rejections, rate limits, partial fills, duplicate fill events.
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from qtrade.execution.orders import (
    TERMINAL,
    ExchangeTimeout,
    Fill,
    Order,
    OrderRejected,
    OrderStatus,
    RateLimited,
    validate_order,
)

DEFAULT_FAULTS: dict[str, Any] = {
    "timeout_prob": 0.0,
    "timeout_accepts_prob": 0.5,
    "reject_prob": 0.0,
    "rate_limit_prob": 0.0,
    "partial_fill_frac": None,   # e.g. 0.5 -> market/limit orders fill half per bar
    "duplicate_fill_prob": 0.0,
}


class SimulatedExchange:
    def __init__(self, cfg: dict[str, Any], initial_usd: float, bar_minutes: int,
                 faults: dict[str, Any] | None = None, seed: int = 0) -> None:
        self.cfg = cfg
        self.costs = cfg["costs"]
        self.exec_cfg = cfg["execution"]
        self.bar_minutes = int(bar_minutes)
        self.usd = float(initial_usd)
        self.btc = 0.0
        self.orders: dict[str, Order] = {}
        self.order_seq: list[str] = []
        self.fills: list[Fill] = []
        self.financing_total = 0.0
        self.financing_ledger: list[tuple[str, float]] = []  # (bar ts, amount)
        self.last_close: float | None = None
        self.last_bar_ts: str | None = None
        self.faults = {**DEFAULT_FAULTS, **(faults or {})}
        self.rng = np.random.default_rng(seed)
        self._fill_seq = 0

    # --------------------------------------------------------------- client API
    def _maybe(self, key: str) -> bool:
        p = float(self.faults.get(key) or 0.0)
        return p > 0 and self.rng.random() < p

    def submit_order(self, order: Order) -> Order:
        if self._maybe("rate_limit_prob"):
            raise RateLimited("rate limit exceeded (simulated)")
        if order.client_id in self.orders:  # idempotent on client id: never duplicate
            return copy.deepcopy(self.orders[order.client_id])
        errors = validate_order(order, self.exec_cfg)
        if errors or self._maybe("reject_prob"):
            reason = "; ".join(errors) or "rejected (simulated)"
            raise OrderRejected(reason)
        if order.reduce_only and self._would_increase(order):
            raise OrderRejected("reduce-only order would increase position")
        accepted = copy.deepcopy(order)
        accepted.status = OrderStatus.OPEN
        accepted.created_ts = accepted.created_ts or self.last_bar_ts
        if self._maybe("timeout_prob"):
            if self.rng.random() < float(self.faults["timeout_accepts_prob"]):
                self._store(accepted)
            raise ExchangeTimeout("submit timed out (simulated); outcome unknown")
        self._store(accepted)
        return copy.deepcopy(accepted)

    def _store(self, order: Order) -> None:
        self.orders[order.client_id] = order
        self.order_seq.append(order.client_id)

    def cancel_order(self, client_id: str) -> bool:
        o = self.orders.get(client_id)
        if o is None or o.status in TERMINAL:
            return False
        o.status = OrderStatus.CANCELED
        return True

    def amend_price(self, client_id: str, price: float) -> bool:
        o = self.orders.get(client_id)
        if o is None or o.status in TERMINAL:
            return False
        o.price = float(price)
        return True

    def get_order(self, client_id: str) -> Order | None:
        o = self.orders.get(client_id)
        return copy.deepcopy(o) if o is not None else None

    def open_orders(self) -> list[Order]:
        return [copy.deepcopy(self.orders[c]) for c in self.order_seq
                if self.orders[c].status not in TERMINAL]

    def position(self) -> float:
        return self.btc

    def equity(self, price: float | None = None) -> float:
        px = self.last_close if price is None else price
        return self.usd + self.btc * (px or 0.0)

    def financing_between(self, start_ts: str, end_ts: str) -> float:
        """Financing charged on bars with start_ts <= bar ts < end_ts."""
        a, b = pd.Timestamp(start_ts), pd.Timestamp(end_ts)
        return sum(amt for ts, amt in self.financing_ledger if a <= pd.Timestamp(ts) < b)

    def fills_since(self, cursor: int) -> tuple[list[Fill], int]:
        new = list(self.fills[cursor:])
        if new and self._maybe("duplicate_fill_prob"):
            new.append(copy.deepcopy(new[-1]))  # duplicate event delivery
        return new, len(self.fills)

    # ------------------------------------------------------------ market data
    def _would_increase(self, order: Order) -> bool:
        return self.btc == 0 or (order.side > 0) == (self.btc > 0)

    def _fill(self, o: Order, ts: str, qty: float, price: float, liquidity: str, ref: float) -> Fill:
        fee_rate = float(self.costs["taker_fee"] if liquidity == "taker" else self.costs["maker_fee"])
        if o.reduce_only:
            qty = min(qty, abs(self.btc))
        notional = qty * price
        fee = notional * fee_rate
        opening_short = o.side < 0 and self.btc <= 0
        if opening_short:
            fee += notional * float(self.costs["short_open_fee"])
        self.usd -= o.side * notional + fee
        self.btc += o.side * qty
        if abs(self.btc) < 1e-12:
            self.btc = 0.0
        prev = o.filled_qty
        o.filled_qty = prev + qty
        o.avg_fill_price = (o.avg_fill_price * prev + price * qty) / o.filled_qty
        o.fees += fee
        o.status = OrderStatus.FILLED if o.remaining <= 1e-12 else OrderStatus.PARTIALLY_FILLED
        self._fill_seq += 1
        f = Fill(fill_id=f"F{self._fill_seq:08d}", client_id=o.client_id, ts=ts, side=o.side, qty=qty,
                 price=price, fee=fee, liquidity=liquidity, ref_price=ref)
        self.fills.append(f)
        return f

    def _fill_qty(self, o: Order) -> float:
        frac = self.faults.get("partial_fill_frac")
        if frac:
            lot = int(self.exec_cfg["lot_decimals"])
            part = math.floor(o.remaining * float(frac) * 10**lot) / 10**lot
            if part >= float(self.exec_cfg["min_order_qty"]):
                return part
        return o.remaining

    def _spawn_bracket(self, parent: Order) -> None:
        stop, target = parent.meta.get("stop"), parent.meta.get("target")
        side = -parent.side
        if stop is not None and math.isfinite(stop):
            self._store(Order(client_id=f"{parent.client_id}-SL", side=side, qty=parent.filled_qty,
                              order_type="stop", price=float(stop), reduce_only=True, tag="stop",
                              status=OrderStatus.OPEN, created_ts=self.last_bar_ts,
                              meta={"parent": parent.client_id, "oco": f"{parent.client_id}-TP"}))
        if target is not None and math.isfinite(target):
            self._store(Order(client_id=f"{parent.client_id}-TP", side=side, qty=parent.filled_qty,
                              order_type="limit", price=float(target), reduce_only=True, tag="target",
                              status=OrderStatus.OPEN, created_ts=self.last_bar_ts,
                              meta={"parent": parent.client_id, "oco": f"{parent.client_id}-SL"}))

    def process_bar(self, ts: pd.Timestamp, o: float, h: float, lo: float, c: float) -> list[Fill]:
        """Advance the exchange by one completed bar; returns fills generated."""
        ts_iso = ts.isoformat()
        start = len(self.fills)
        slip = float(self.costs["slippage_bps"]) / 1e4
        limit_filled_now: set[str] = set()

        # 1. market orders, in submission order
        for cid in list(self.order_seq):
            od = self.orders[cid]
            if od.status in TERMINAL or od.order_type != "market":
                continue
            if od.reduce_only and self.btc == 0:
                od.status = OrderStatus.CANCELED
                continue
            self._fill(od, ts_iso, self._fill_qty(od), o * (1 + od.side * slip), "taker", o)
            if od.status == OrderStatus.FILLED and od.tag == "entry":
                self._spawn_bracket(od)

        # 2. resting entry limits (expiry first)
        for cid in list(self.order_seq):
            od = self.orders[cid]
            if od.status in TERMINAL or od.order_type != "limit" or od.reduce_only:
                continue
            if od.expire_ts is not None and ts >= pd.Timestamp(od.expire_ts):
                od.status = OrderStatus.EXPIRED
                if od.tag == "entry" and od.filled_qty > 0:
                    self._spawn_bracket(od)  # protect a partially filled entry
                continue
            if (od.side == 1 and lo < od.price) or (od.side == -1 and h > od.price):
                self._fill(od, ts_iso, self._fill_qty(od), float(od.price), "maker", float(od.price))
                if od.status == OrderStatus.FILLED and od.tag == "entry":
                    self._spawn_bracket(od)
                    limit_filled_now.add(od.client_id)

        # 3. protective stops, then targets (stop first if both are touched)
        stopped: set[str] = set()
        for cid in list(self.order_seq):
            od = self.orders[cid]
            if od.status in TERMINAL or od.order_type != "stop":
                continue
            if self.btc == 0:
                od.status = OrderStatus.CANCELED
                continue
            if od.side == -1 and lo <= od.price:
                ref = min(o, float(od.price))
                self._fill(od, ts_iso, od.remaining, ref * (1 - slip), "taker", ref)
            elif od.side == 1 and h >= od.price:
                ref = max(o, float(od.price))
                self._fill(od, ts_iso, od.remaining, ref * (1 + slip), "taker", ref)
            else:
                continue
            stopped.add(cid)
            oco = od.meta.get("oco")
            if oco and oco in self.orders and self.orders[oco].status not in TERMINAL:
                self.orders[oco].status = OrderStatus.CANCELED
        for cid in list(self.order_seq):
            od = self.orders[cid]
            if od.status in TERMINAL or od.order_type != "limit" or not od.reduce_only:
                continue
            if self.btc == 0:
                od.status = OrderStatus.CANCELED
                continue
            if od.meta.get("parent") in limit_filled_now:
                continue  # order of events inside the fill bar is unknowable
            if (od.side == -1 and h > od.price) or (od.side == 1 and lo < od.price):
                self._fill(od, ts_iso, od.remaining, float(od.price), "maker", float(od.price))
                oco = od.meta.get("oco")
                if oco and oco in self.orders and self.orders[oco].status not in TERMINAL:
                    self.orders[oco].status = OrderStatus.CANCELED

        # 4. short financing, mark
        if self.btc < 0:
            fin = float(self.costs["short_rollover_per_4h"]) * self.bar_minutes / 240.0 * abs(self.btc) * c
            self.usd -= fin
            self.financing_total += fin
            self.financing_ledger.append((ts_iso, fin))
        self.last_close = c
        self.last_bar_ts = ts_iso
        return self.fills[start:]

    # ------------------------------------------------------------ persistence
    def to_dict(self) -> dict[str, Any]:
        return {
            "usd": self.usd, "btc": self.btc, "financing_total": self.financing_total,
            "financing_ledger": self.financing_ledger[-20000:],
            "last_close": self.last_close, "last_bar_ts": self.last_bar_ts, "fill_seq": self._fill_seq,
            "orders": [self.orders[c].to_dict() for c in self.order_seq],
            "fills": [f.to_dict() for f in self.fills],
        }

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_dict()))
        tmp.replace(p)

    def load(self, path: str | Path) -> bool:
        p = Path(path)
        if not p.exists():
            return False
        d = json.loads(p.read_text())
        self.usd, self.btc = d["usd"], d["btc"]
        self.financing_total = d["financing_total"]
        self.financing_ledger = [tuple(x) for x in d.get("financing_ledger", [])]
        self.last_close, self.last_bar_ts = d["last_close"], d["last_bar_ts"]
        self._fill_seq = d["fill_seq"]
        self.orders, self.order_seq = {}, []
        for od in d["orders"]:
            self._store(Order.from_dict(od))
        self.fills = [Fill(**f) for f in d["fills"]]
        return True
