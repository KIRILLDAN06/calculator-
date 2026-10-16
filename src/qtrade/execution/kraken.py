"""Kraken REST adapter.

Public endpoints (no credentials): server time, OHLC, ticker, asset pairs.
Private endpoints are implemented for completeness but every call passes
through :func:`qtrade.config.assert_live_trading_allowed`, and order
submission defaults to Kraken's ``validate=true`` (validate-only, nothing is
placed). Live order submission has NOT been tested against Kraken.

Endpoint facts (verify against https://docs.kraken.com/api/ before any use):
* ``GET /0/public/OHLC`` returns at most the 720 most recent candles; the last
  candle is the current, not-yet-closed interval and must be dropped.
* Public-endpoint rate limits are per IP; private calls use a decaying
  "API counter" (see research/data_sources.md).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import time
import urllib.parse
from typing import Any

import pandas as pd
import requests

from qtrade.config import LiveTradingDisabled, assert_live_trading_allowed
from qtrade.execution.orders import ExchangeError, ExchangeTimeout, RateLimited

log = logging.getLogger(__name__)

API_URL = "https://api.kraken.com"
INTERVALS = {1, 5, 15, 30, 60, 240, 1440, 10080, 21600}


def kraken_signature(url_path: str, data: dict[str, Any], secret_b64: str) -> str:
    """API-Sign = base64(HMAC-SHA512(path + SHA256(nonce + postdata), base64decode(secret)))."""
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data["nonce"]) + postdata).encode()
    message = url_path.encode() + hashlib.sha256(encoded).digest()
    mac = hmac.new(base64.b64decode(secret_b64), message, hashlib.sha512)
    return base64.b64encode(mac.digest()).decode()


class _Throttle:
    def __init__(self, min_interval_s: float) -> None:
        self.min_interval_s = min_interval_s
        self._last = 0.0

    def wait(self) -> None:
        dt = time.monotonic() - self._last
        if dt < self.min_interval_s:
            time.sleep(self.min_interval_s - dt)
        self._last = time.monotonic()


class KrakenPublicClient:
    def __init__(self, session: requests.Session | None = None, base_url: str = API_URL,
                 timeout_s: float = 10.0, min_interval_s: float = 1.0, retries: int = 3) -> None:
        self.session = session or requests.Session()
        self.base_url = base_url
        self.timeout_s = timeout_s
        self.retries = retries
        self.throttle = _Throttle(min_interval_s)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        delay = 1.0
        for attempt in range(1, self.retries + 1):
            self.throttle.wait()
            try:
                resp = self.session.get(self.base_url + path, params=params, timeout=self.timeout_s)
            except requests.Timeout as exc:
                if attempt == self.retries:
                    raise ExchangeTimeout(str(exc)) from exc
            except requests.RequestException as exc:
                if attempt == self.retries:
                    raise ExchangeError(str(exc)) from exc
            else:
                if resp.status_code == 429:
                    if attempt == self.retries:
                        raise RateLimited("HTTP 429")
                elif resp.status_code >= 500:
                    if attempt == self.retries:
                        raise ExchangeError(f"HTTP {resp.status_code}")
                else:
                    resp.raise_for_status()
                    payload = resp.json()
                    errors = payload.get("error") or []
                    if errors:
                        if any("Rate limit" in e or "Too many requests" in e for e in errors):
                            if attempt == self.retries:
                                raise RateLimited("; ".join(errors))
                        else:
                            raise ExchangeError("; ".join(errors))
                    else:
                        return payload["result"]
            time.sleep(delay)
            delay *= 2
        raise ExchangeError("unreachable")

    def server_time(self) -> pd.Timestamp:
        res = self._get("/0/public/Time")
        return pd.Timestamp(int(res["unixtime"]), unit="s", tz="UTC")

    def ohlc(self, pair: str = "XBTUSD", interval: int = 5, since: int | None = None) -> pd.DataFrame:
        """Closed candles only (the trailing in-progress candle is dropped)."""
        if interval not in INTERVALS:
            raise ValueError(f"interval must be one of {sorted(INTERVALS)}")
        params: dict[str, Any] = {"pair": pair, "interval": interval}
        if since is not None:
            params["since"] = since
        res = self._get("/0/public/OHLC", params)
        key = next(k for k in res if k != "last")
        return parse_ohlc(res[key], interval)

    def ticker(self, pair: str = "XBTUSD") -> dict[str, float]:
        res = self._get("/0/public/Ticker", {"pair": pair})
        t = next(iter(res.values()))
        bid, ask = float(t["b"][0]), float(t["a"][0])
        mid = (bid + ask) / 2
        return {"bid": bid, "ask": ask, "last": float(t["c"][0]), "spread_bps": (ask - bid) / mid * 1e4}

    def asset_pair(self, pair: str = "XBTUSD") -> dict[str, Any]:
        res = self._get("/0/public/AssetPairs", {"pair": pair})
        return next(iter(res.values()))


def parse_ohlc(rows: list[list[Any]], interval: int) -> pd.DataFrame:
    """Kraken OHLC rows -> qtrade bar frame; drops the final (unclosed) candle."""
    cols = ["time", "open", "high", "low", "close", "vwap", "volume", "count"]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "quote_volume",
                                     "n_minutes", "n_active", "complete"])
    df = df.iloc[:-1]
    for c in cols[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    idx = pd.to_datetime(df["time"].astype("int64"), unit="s", utc=True)
    out = pd.DataFrame(
        {
            "open": df["open"].to_numpy(), "high": df["high"].to_numpy(), "low": df["low"].to_numpy(),
            "close": df["close"].to_numpy(), "volume": df["volume"].to_numpy(),
            "quote_volume": (df["vwap"] * df["volume"]).to_numpy(),
            "n_minutes": interval, "n_active": (df["count"] > 0).astype(int).to_numpy() * interval,
            "complete": True,
        },
        index=pd.DatetimeIndex(idx, name="ts"),
    )
    return out


class KrakenPrivateClient:
    """Authenticated client. Every request is gated by the live-trading approval checks."""

    def __init__(self, cfg: dict[str, Any], session: requests.Session | None = None,
                 base_url: str = API_URL, timeout_s: float = 10.0) -> None:
        self.cfg = cfg
        self.session = session or requests.Session()
        self.base_url = base_url
        self.timeout_s = timeout_s

    def _credentials(self) -> tuple[str, str]:
        key = os.environ.get("QTRADE_KRAKEN_API_KEY")
        secret = os.environ.get("QTRADE_KRAKEN_API_SECRET")
        if not key or not secret:
            raise LiveTradingDisabled("Kraken credentials not set in environment")
        return key, secret

    def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        assert_live_trading_allowed(self.cfg)
        key, secret = self._credentials()
        data = {"nonce": str(int(time.time() * 1000)), **data}
        headers = {"API-Key": key, "API-Sign": kraken_signature(path, data, secret)}
        try:
            resp = self.session.post(self.base_url + path, data=data, headers=headers, timeout=self.timeout_s)
        except requests.Timeout as exc:
            raise ExchangeTimeout(str(exc)) from exc
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("error"):
            raise ExchangeError("; ".join(payload["error"]))
        return payload["result"]

    def add_order(self, pair: str, side: int, qty: float, order_type: str, price: float | None = None,
                  client_id: str | None = None, validate_only: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "pair": pair, "type": "buy" if side > 0 else "sell",
            "ordertype": {"market": "market", "limit": "limit", "stop": "stop-loss"}[order_type],
            "volume": f"{qty:.8f}",
        }
        if price is not None:
            data["price"] = f"{price:.1f}"
        if client_id:
            data["cl_ord_id"] = client_id
        if validate_only:
            data["validate"] = "true"
        return self._post("/0/private/AddOrder", data)

    def cancel_order(self, txid_or_client_id: str) -> dict[str, Any]:
        return self._post("/0/private/CancelOrder", {"txid": txid_or_client_id})

    def open_orders(self) -> dict[str, Any]:
        return self._post("/0/private/OpenOrders", {})

    def balance(self) -> dict[str, Any]:
        return self._post("/0/private/Balance", {})
