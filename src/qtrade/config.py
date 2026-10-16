"""Configuration loading and validation.

Configuration lives in YAML files under ``configs/``. Secrets never live in
config files: exchange credentials are read only from environment variables
(``QTRADE_KRAKEN_API_KEY`` / ``QTRADE_KRAKEN_API_SECRET``) and only by the live
adapter, which is gated by :func:`assert_live_trading_allowed`.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml

LIVE_APPROVAL_ENV = "QTRADE_LIVE_TRADING_APPROVED"
LIVE_APPROVAL_PHRASE = "I-ACCEPT-REAL-MONEY-RISK"

VALID_MODES = {"backtest", "paper", "live"}

DEFAULTS: dict[str, Any] = {
    "mode": "backtest",
    "symbol": "BTC/USD",
    "data": {
        "clean_dir": "data/clean",
        "timeframe": "15min",
    },
    "capital": {"initial_equity": 10_000.0, "quote_ccy": "USD"},
    "costs": {
        # Kraken Pro spot, lowest-volume tier (verify against research/data_sources.md).
        "taker_fee": 0.0040,
        "maker_fee": 0.0025,
        # Adverse price move applied to every market/stop fill, per side.
        "slippage_bps": 5.0,
        # Margin financing for shorts (Kraken margin: open fee + rollover per 4h).
        "short_open_fee": 0.0002,
        "short_rollover_per_4h": 0.0002,
    },
    "execution": {
        "lot_decimals": 8,
        "min_order_qty": 0.0001,
        "price_decimals": 1,
        "max_participation": 0.05,  # max fraction of previous bar's traded volume
        "same_bar_stop_target": "stop_first",  # conservative intrabar assumption
    },
    "risk": {
        "risk_per_trade": 0.005,
        "max_leverage": 1.0,
        "max_open_positions": 1,
        "max_daily_loss": 0.02,
        "max_drawdown": 0.20,
        "max_trades_per_day": 4,
        "max_consecutive_losses": 5,
        "cooldown_bars_after_loss_streak": 96,
        "max_order_notional": 1_000_000.0,
        "max_data_staleness_s": 180.0,
        "max_spread_bps": 25.0,
        "max_slippage_bps": 50.0,
        "min_bar_quote_volume": 0.0,
        "allow_short": True,
    },
    "strategy": {"name": "no_trade", "params": {}},
    "live_trading": {"enabled": False},
    "paper": {
        "state_file": "state/paper_state.json",
        "log_file": "logs/paper.log",
        "alerts_file": "logs/alerts.log",
        "poll_seconds": 30,
    },
}


class ConfigError(ValueError):
    """Raised for missing or invalid configuration."""


class LiveTradingDisabled(RuntimeError):
    """Raised whenever code attempts a live (real-money) action without approval."""


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def validate_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """Validate a merged config dict; raise ConfigError with every problem found."""
    errors: list[str] = []
    if cfg.get("mode") not in VALID_MODES:
        errors.append(f"mode must be one of {sorted(VALID_MODES)}, got {cfg.get('mode')!r}")

    costs = cfg["costs"]
    for key in ("taker_fee", "maker_fee"):
        if not 0 <= float(costs[key]) < 0.05:
            errors.append(f"costs.{key} must be in [0, 0.05), got {costs[key]}")
    if float(costs["slippage_bps"]) < 0:
        errors.append("costs.slippage_bps must be >= 0")

    risk = cfg["risk"]
    if not 0 < float(risk["risk_per_trade"]) <= 0.05:
        errors.append("risk.risk_per_trade must be in (0, 0.05]")
    if not 0 < float(risk["max_leverage"]) <= 3:
        errors.append("risk.max_leverage must be in (0, 3]")
    if not 0 < float(risk["max_daily_loss"]) < 1:
        errors.append("risk.max_daily_loss must be in (0, 1)")
    if not 0 < float(risk["max_drawdown"]) < 1:
        errors.append("risk.max_drawdown must be in (0, 1)")
    if int(risk["max_open_positions"]) < 1:
        errors.append("risk.max_open_positions must be >= 1")
    if int(risk["max_trades_per_day"]) < 1:
        errors.append("risk.max_trades_per_day must be >= 1")

    if float(cfg["capital"]["initial_equity"]) <= 0:
        errors.append("capital.initial_equity must be > 0")

    ex = cfg["execution"]
    if ex["same_bar_stop_target"] not in {"stop_first"}:
        errors.append("execution.same_bar_stop_target only supports 'stop_first' (conservative)")
    if not 0 < float(ex["max_participation"]) <= 1:
        errors.append("execution.max_participation must be in (0, 1]")

    if not isinstance(cfg.get("strategy", {}).get("name"), str):
        errors.append("strategy.name is required")

    live = cfg.get("live_trading", {})
    if cfg.get("mode") == "live" and not live.get("enabled", False):
        errors.append("mode 'live' requires live_trading.enabled: true (and human approval)")
    if live.get("enabled") and cfg.get("mode") != "live":
        errors.append("live_trading.enabled may only be true when mode is 'live'")

    # Secrets must never be stored in config files.
    flat = yaml.safe_dump(cfg).lower()
    for marker in ("api_secret", "private_key", "apisecret"):
        if marker in flat:
            errors.append(f"config appears to contain a secret ({marker}); use environment variables")

    if errors:
        raise ConfigError("Invalid configuration:\n  - " + "\n  - ".join(errors))
    return cfg


def load_config(path: str | os.PathLike[str] | None = None, overrides: dict[str, Any] | None = None) -> dict:
    """Load YAML config (if given), merge over defaults and overrides, validate."""
    cfg = copy.deepcopy(DEFAULTS)
    if path is not None:
        p = Path(path)
        if not p.exists():
            raise ConfigError(f"Config file not found: {p}")
        with p.open() as fh:
            loaded = yaml.safe_load(fh) or {}
        if not isinstance(loaded, dict):
            raise ConfigError(f"Config file {p} must contain a mapping")
        cfg = _deep_merge(cfg, loaded)
    if overrides:
        cfg = _deep_merge(cfg, overrides)
    return validate_config(cfg)


def assert_live_trading_allowed(cfg: dict[str, Any]) -> None:
    """Raise LiveTradingDisabled unless every live-trading gate is satisfied.

    Gates (all required):
      1. ``mode: live`` and ``live_trading.enabled: true`` in the config file;
      2. environment variable ``QTRADE_LIVE_TRADING_APPROVED`` equal to the
         approval phrase, set by a human operator for that process only;
      3. ``live_trading.readiness_report`` pointing at an existing file
         (the human-reviewed readiness report).
    """
    live = cfg.get("live_trading", {})
    if cfg.get("mode") != "live" or not live.get("enabled", False):
        raise LiveTradingDisabled("Live trading is disabled in configuration (default).")
    if os.environ.get(LIVE_APPROVAL_ENV) != LIVE_APPROVAL_PHRASE:
        raise LiveTradingDisabled(
            f"Live trading requires explicit human approval via {LIVE_APPROVAL_ENV}."
        )
    report = live.get("readiness_report")
    if not report or not Path(report).exists():
        raise LiveTradingDisabled("Live trading requires an existing, human-reviewed readiness report.")
