"""Layer B/F: order validation, simulated exchange, Kraken adapter (fully mocked, no network)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import requests

from qtrade.config import LIVE_APPROVAL_ENV, LiveTradingDisabled, load_config
from qtrade.execution.feeds import ReplayFeed, clean_feed_bars
from qtrade.execution.kraken import KrakenPrivateClient, KrakenPublicClient, kraken_signature, parse_ohlc
from qtrade.execution.orders import (
    ExchangeError,
    ExchangeTimeout,
    Order,
    OrderRejected,
    OrderStatus,
    RateLimited,
    validate_order,
)
from qtrade.execution.simulator import SimulatedExchange

T0 = pd.Timestamp("2024-01-01 00:00", tz="UTC")


@pytest.fixture
def ex_cfg():
    return load_config(overrides={"costs": {"taker_fee": 0.004, "maker_fee": 0.002, "slippage_bps": 10.0,
                                            "short_open_fee": 0.0, "short_rollover_per_4h": 0.0}})


def mk(cid="o1", side=1, qty=1.0, typ="market", price=None, **kw):
    return Order(client_id=cid, side=side, qty=qty, order_type=typ, price=price, **kw)


# --------------------------------------------------------------- validation
@pytest.mark.parametrize("order,needle", [
    (mk(qty=0), "positive"),
    (mk(qty=-1), "positive"),
    (mk(qty=float("nan")), "positive"),
    (mk(qty=0.00001), "below minimum"),
    (mk(qty=0.123456789), "decimals"),
    (mk(side=2), "side"),
    (mk(typ="iceberg"), "unsupported"),
    (mk(typ="limit", price=None), "price"),
    (mk(typ="limit", price=100.05), "decimals"),
    (mk(cid=""), "client_id"),
])
def test_order_validation(ex_cfg, order, needle):
    errs = validate_order(order, ex_cfg["execution"])
    assert any(needle in e for e in errs), errs


def test_valid_order_passes(ex_cfg):
    assert validate_order(mk(qty=0.5, typ="limit", price=100.1), ex_cfg["execution"]) == []


# ---------------------------------------------------------------- simulator
def test_market_fill_fees_and_idempotent_submit(ex_cfg):
    ex = SimulatedExchange(ex_cfg, 10_000, 60)
    a = ex.submit_order(mk(qty=1.0, tag="entry"))
    b = ex.submit_order(mk(qty=5.0, tag="entry"))           # same client id -> no duplicate
    assert a.client_id == b.client_id and len(ex.orders) == 1 and b.qty == 1.0
    fills = ex.process_bar(T0, 100, 101, 99, 100)
    assert len(fills) == 1 and fills[0].price == pytest.approx(100.1) and fills[0].liquidity == "taker"
    assert fills[0].fee == pytest.approx(100.1 * 0.004)
    assert ex.position() == 1.0 and ex.usd == pytest.approx(10_000 - 100.1 - 0.4004)


def test_bracket_stop_first_and_oco(ex_cfg):
    ex = SimulatedExchange(ex_cfg, 10_000, 60)
    ex.submit_order(mk(cid="e", qty=1.0, tag="entry", meta={"stop": 95.0, "target": 110.0}))
    ex.process_bar(T0, 100, 101, 99, 100)
    assert ex.get_order("e-SL").status == OrderStatus.OPEN and ex.get_order("e-TP").status == OrderStatus.OPEN
    fills = ex.process_bar(T0 + pd.Timedelta(hours=1), 100, 111, 94, 100)   # both touched
    assert [f.client_id for f in fills] == ["e-SL"]
    assert fills[0].price == pytest.approx(95 * 0.999)
    assert ex.get_order("e-TP").status == OrderStatus.CANCELED and ex.position() == 0


def test_limit_entry_trade_through_and_expiry(ex_cfg):
    ex = SimulatedExchange(ex_cfg, 10_000, 60)
    ex.submit_order(mk(cid="L", qty=1.0, typ="limit", price=98.0, tag="entry",
                       expire_ts=(T0 + pd.Timedelta(hours=2)).isoformat()))
    assert ex.process_bar(T0, 100, 101, 98.0, 100) == []                     # touch only
    assert ex.process_bar(T0 + pd.Timedelta(hours=1), 100, 101, 98.5, 100) == []
    assert ex.process_bar(T0 + pd.Timedelta(hours=2), 99, 100, 97, 98) == []  # expired at 02:00
    assert ex.get_order("L").status == OrderStatus.EXPIRED


def test_partial_fills_are_protected_immediately_and_bracket_resized(ex_cfg):
    ex = SimulatedExchange(ex_cfg, 10_000, 60, faults={"partial_fill_frac": 0.5})
    ex.submit_order(mk(cid="p", qty=1.0, tag="entry", meta={"stop": 90.0}))
    ex.process_bar(T0, 100, 101, 99, 100)
    assert ex.get_order("p").status == OrderStatus.PARTIALLY_FILLED and ex.position() == 0.5
    assert ex.get_order("p-SL").qty == pytest.approx(0.5)        # protected after the first partial fill
    for k in range(1, 20):
        ex.process_bar(T0 + pd.Timedelta(hours=k), 100, 101, 99, 100)
        if ex.get_order("p").status == OrderStatus.FILLED:
            break
    assert ex.position() == pytest.approx(1.0)
    assert ex.get_order("p-SL").qty == pytest.approx(1.0)        # resized with every fill


def test_stop_breach_during_partial_fill_exits_and_cancels_remainder(ex_cfg):
    # Audit reproduction: previously no stop existed and the remainder kept filling into the crash.
    ex = SimulatedExchange(ex_cfg, 10_000, 60, faults={"partial_fill_frac": 0.5})
    ex.submit_order(mk(cid="p", qty=10.0, tag="entry", meta={"stop": 95.0}))
    ex.process_bar(T0, 100, 101, 99, 100)
    assert ex.position() == pytest.approx(5.0)
    ex.process_bar(T0 + pd.Timedelta(hours=1), 80, 81, 60, 70)    # gaps far below the stop
    assert ex.get_order("p").status == OrderStatus.CANCELED
    assert ex.position() == pytest.approx(0.0)
    ex.process_bar(T0 + pd.Timedelta(hours=2), 70, 71, 69, 70)
    assert ex.position() == pytest.approx(0.0)                    # nothing keeps filling afterwards


def test_reduce_only_cannot_open_or_flip(ex_cfg):
    ex = SimulatedExchange(ex_cfg, 10_000, 60)
    with pytest.raises(OrderRejected, match="reduce-only"):
        ex.submit_order(mk(side=-1, reduce_only=True))
    ex.submit_order(mk(cid="b", qty=1.0, tag="entry"))
    ex.process_bar(T0, 100, 101, 99, 100)
    ex.submit_order(mk(cid="x", side=-1, qty=3.0, reduce_only=True, tag="exit"))
    ex.process_bar(T0 + pd.Timedelta(hours=1), 100, 101, 99, 100)
    assert ex.position() == 0.0                              # capped at position size, no flip


def test_fault_injection_timeout_reject_ratelimit_duplicates(ex_cfg):
    ex = SimulatedExchange(ex_cfg, 10_000, 60, faults={"timeout_prob": 1.0, "timeout_accepts_prob": 1.0})
    with pytest.raises(ExchangeTimeout):
        ex.submit_order(mk(cid="t1"))
    assert ex.get_order("t1") is not None                    # accepted despite timeout
    ex2 = SimulatedExchange(ex_cfg, 10_000, 60, faults={"timeout_prob": 1.0, "timeout_accepts_prob": 0.0})
    with pytest.raises(ExchangeTimeout):
        ex2.submit_order(mk(cid="t2"))
    assert ex2.get_order("t2") is None                       # lost
    with pytest.raises(OrderRejected):
        SimulatedExchange(ex_cfg, 10_000, 60, faults={"reject_prob": 1.0}).submit_order(mk())
    with pytest.raises(RateLimited):
        SimulatedExchange(ex_cfg, 10_000, 60, faults={"rate_limit_prob": 1.0}).submit_order(mk())
    ex3 = SimulatedExchange(ex_cfg, 10_000, 60, faults={"duplicate_fill_prob": 1.0})
    ex3.submit_order(mk(cid="d"))
    ex3.process_bar(T0, 100, 101, 99, 100)
    fills, _ = ex3.fills_since(0)
    assert len(fills) == 2 and fills[0].fill_id == fills[1].fill_id


def test_simulator_persistence_roundtrip(ex_cfg, tmp_path):
    ex = SimulatedExchange(ex_cfg, 10_000, 60)
    ex.submit_order(mk(cid="e", tag="entry", meta={"stop": 95.0}))
    ex.process_bar(T0, 100, 101, 99, 100)
    ex.save(tmp_path / "ex.json")
    ex2 = SimulatedExchange(ex_cfg, 0, 60)
    assert ex2.load(tmp_path / "ex.json")
    assert ex2.position() == ex.position() and ex2.usd == ex.usd
    assert ex2.get_order("e-SL").price == 95.0 and len(ex2.fills) == 1


# -------------------------------------------------------------------- feeds
def test_clean_feed_bars_and_replay_faults():
    idx = pd.date_range(T0, periods=6, freq="1h")
    bars = pd.DataFrame({"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0}, index=idx)
    dirty = pd.concat([bars, bars.iloc[[2]]]).sort_index()
    dirty.iloc[4, dirty.columns.get_loc("high")] = np.nan
    clean, problems = clean_feed_bars(dirty)
    assert len(clean) == 5 and any("duplicate" in p for p in problems) and any("malformed" in p for p in problems)
    feed = ReplayFeed(bars, 60)
    assert len(feed.fetch(T0 + pd.Timedelta(hours=3))) == 3            # only closed bars
    frozen = ReplayFeed(bars, 60, faults={"freeze_between": (str(T0 + pd.Timedelta(hours=2)),
                                                              str(T0 + pd.Timedelta(hours=9)))})
    assert len(frozen.fetch(T0 + pd.Timedelta(hours=5))) == 2


# ------------------------------------------------------------------- kraken
def test_kraken_signature_matches_documented_example():
    sig = kraken_signature(
        "/0/private/AddOrder",
        {"nonce": "1616492376594", "ordertype": "limit", "pair": "XBTUSD", "price": 37500, "type": "buy",
         "volume": 1.25},
        "kQH5HW/8p1uGOVjbgWA7FunAmGO8lsSUXNsu3eow76sz84Q18fWxnyRzBHCd3pd5nE9qa99HAZtuZuj6F1huXg==",
    )
    assert sig == "4/dpxb3iT4tp/ZCVEwSnEsLxx0bqyhLpdfOpc6fn7OR8+UClSV5n9E6aSS8MPtnRfp32bAb0nmbRn6H8ndwLUQ=="


def test_parse_ohlc_drops_unclosed_candle():
    rows = [[1704067200 + 300 * i, "100", "101", "99", "100.5", "100.2", "2.0", 5] for i in range(4)]
    df = parse_ohlc(rows, 5)
    assert len(df) == 3 and df.index[0] == pd.Timestamp("2024-01-01", tz="UTC")
    assert df.quote_volume.iloc[0] == pytest.approx(200.4)


class _Resp:
    def __init__(self, status=200, payload=None):
        self.status_code, self._p = status, payload

    def json(self):
        return self._p

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


class _Sess:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def post(self, *a, **k):  # pragma: no cover - must never be reached in tests
        raise AssertionError("private endpoint called")


def _client(responses):
    c = KrakenPublicClient(session=_Sess(responses), min_interval_s=0.0)
    return c


def test_public_client_retries_and_errors(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    ok = {"error": [], "result": {"XXBTZUSD": [[1704067200, "1", "1", "1", "1", "1", "1", 1],
                                               [1704067500, "1", "1", "1", "1", "1", "1", 1]], "last": 1}}
    c = _client([_Resp(429), _Resp(502), _Resp(200, ok)])
    assert len(c.ohlc("XBTUSD", 5)) == 1 and c.session.calls == 3
    with pytest.raises(ExchangeTimeout):
        _client([requests.Timeout("t")] * 3).server_time()
    with pytest.raises(ExchangeError, match="EQuery"):
        _client([_Resp(200, {"error": ["EQuery:Unknown asset pair"], "result": {}})]).ticker("NOPE")
    with pytest.raises(RateLimited):
        _client([_Resp(200, {"error": ["EAPI:Rate limit exceeded"]})] * 3).server_time()


def test_private_client_refuses_without_live_approval(monkeypatch):
    monkeypatch.delenv(LIVE_APPROVAL_ENV, raising=False)
    monkeypatch.setenv("QTRADE_KRAKEN_API_KEY", "k")
    monkeypatch.setenv("QTRADE_KRAKEN_API_SECRET", "c2VjcmV0")
    client = KrakenPrivateClient(load_config(), session=_Sess([]))
    for call in (lambda: client.add_order("XBTUSD", 1, 0.001, "market"), client.balance, client.open_orders):
        with pytest.raises(LiveTradingDisabled):
            call()
