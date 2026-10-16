"""Strategy registry."""

from __future__ import annotations

from typing import Any

from qtrade.strategies.base import Strategy
from qtrade.strategies.basic import (
    BollingerMeanReversion,
    DonchianTrend,
    IntradayMomentum,
    NoTrade,
    RandomEntry,
)
from qtrade.strategies.session import OpeningRangeBreakout, SweepFVG

REGISTRY: dict[str, type[Strategy]] = {
    cls.name: cls
    for cls in (NoTrade, RandomEntry, DonchianTrend, BollingerMeanReversion, IntradayMomentum,
                OpeningRangeBreakout, SweepFVG)
}


def make_strategy(name: str, params: dict[str, Any] | None = None) -> Strategy:
    if name not in REGISTRY:
        raise KeyError(f"unknown strategy {name!r}; available: {sorted(REGISTRY)}")
    return REGISTRY[name](**(params or {}))


__all__ = ["REGISTRY", "Strategy", "make_strategy"]
