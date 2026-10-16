"""Order and fill data model plus pre-submission validation."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class OrderStatus(StrEnum):
    PENDING_SUBMIT = "pending_submit"  # created locally, not yet acknowledged
    UNKNOWN = "unknown"                # submit outcome uncertain (e.g. timeout) -> must reconcile
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REJECTED = "rejected"


TERMINAL = {OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.EXPIRED, OrderStatus.REJECTED}


class ExchangeError(RuntimeError):
    """Base class for exchange-side failures."""


class ExchangeTimeout(ExchangeError):
    """Request timed out: the order may or may not have been accepted."""


class RateLimited(ExchangeError):
    """Exchange rate limit hit; back off and retry later."""


class OrderRejected(ExchangeError):
    """Exchange rejected the order (validation, funds, etc.)."""


@dataclass
class Order:
    client_id: str
    side: int                     # +1 buy, -1 sell
    qty: float
    order_type: str               # market | limit | stop
    price: float | None = None    # limit price, or stop trigger for stop orders
    reduce_only: bool = False
    expire_ts: str | None = None  # ISO time after which a resting order expires
    status: OrderStatus = OrderStatus.PENDING_SUBMIT
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    fees: float = 0.0
    created_ts: str | None = None
    tag: str = ""                 # entry | exit | stop | target
    reason: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def remaining(self) -> float:
        return max(self.qty - self.filled_qty, 0.0)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = str(self.status)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Order:
        d = dict(d)
        d["status"] = OrderStatus(d["status"])
        return cls(**d)


@dataclass
class Fill:
    fill_id: str
    client_id: str
    ts: str
    side: int
    qty: float
    price: float
    fee: float
    liquidity: str  # maker | taker
    ref_price: float = float("nan")  # pre-slippage reference (bar open / stop / limit)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_order(order: Order, exec_cfg: dict[str, Any]) -> list[str]:
    """Return a list of validation errors (empty if the order is acceptable)."""
    errors: list[str] = []
    if order.side not in (1, -1):
        errors.append("side must be +1 or -1")
    if order.order_type not in ("market", "limit", "stop"):
        errors.append(f"unsupported order type {order.order_type!r}")
    if not isinstance(order.qty, (int, float)) or not math.isfinite(order.qty) or order.qty <= 0:
        errors.append("quantity must be a positive finite number")
    else:
        if order.qty < float(exec_cfg["min_order_qty"]):
            errors.append(f"quantity {order.qty} below minimum {exec_cfg['min_order_qty']}")
        lot = int(exec_cfg["lot_decimals"])
        if abs(round(order.qty, lot) - order.qty) > 10 ** -(lot + 3):
            errors.append(f"quantity has more than {lot} decimals")
    if order.order_type in ("limit", "stop"):
        if order.price is None or not math.isfinite(order.price) or order.price <= 0:
            errors.append("limit/stop orders need a positive finite price")
        else:
            dec = int(exec_cfg["price_decimals"])
            if abs(round(order.price, dec) - order.price) > 10 ** -(dec + 3):
                errors.append(f"price has more than {dec} decimals")
    if not order.client_id or len(order.client_id) > 64:
        errors.append("client_id required (<= 64 chars)")
    return errors
