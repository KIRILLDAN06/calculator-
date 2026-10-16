"""Layers A/B/C: configuration, data validation/pipeline, indicator calculations."""

from __future__ import annotations

import gzip
import io
import json

import numpy as np
import pandas as pd
import pytest

from conftest import make_bars
from qtrade import features as F
from qtrade.config import (
    LIVE_APPROVAL_ENV,
    LIVE_APPROVAL_PHRASE,
    ConfigError,
    LiveTradingDisabled,
    assert_live_trading_allowed,
    load_config,
)
from qtrade.data import download as dl
from qtrade.data.bars import resample_bars
from qtrade.data.pipeline import build
from qtrade.data.validate import validate_minutes

# --------------------------------------------------------------------- config


def test_default_config_is_valid_and_live_disabled():
    cfg = load_config()
    assert cfg["mode"] == "backtest" and cfg["live_trading"]["enabled"] is False
    for path in ("configs/backtest.yaml", "configs/paper.yaml"):
        c = load_config(path)
        assert c["live_trading"]["enabled"] is False


@pytest.mark.parametrize("override,match", [
    ({"mode": "yolo"}, "mode"),
    ({"costs": {"taker_fee": -0.1}}, "taker_fee"),
    ({"risk": {"risk_per_trade": 0.5}}, "risk_per_trade"),
    ({"risk": {"max_leverage": 50}}, "max_leverage"),
    ({"capital": {"initial_equity": 0}}, "initial_equity"),
    ({"mode": "live"}, "live_trading.enabled"),
    ({"live_trading": {"enabled": True}}, "only be true"),
    ({"exchange": {"api_secret": "abc"}}, "secret"),
])
def test_invalid_config_rejected(override, match):
    with pytest.raises(ConfigError, match=match):
        load_config(overrides=override)


def test_missing_config_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml")


def test_live_trading_gate(tmp_path, monkeypatch):
    monkeypatch.delenv(LIVE_APPROVAL_ENV, raising=False)
    with pytest.raises(LiveTradingDisabled):
        assert_live_trading_allowed(load_config())
    live = load_config(overrides={"mode": "live", "live_trading": {"enabled": True}})
    with pytest.raises(LiveTradingDisabled, match="human approval"):
        assert_live_trading_allowed(live)
    monkeypatch.setenv(LIVE_APPROVAL_ENV, LIVE_APPROVAL_PHRASE)
    with pytest.raises(LiveTradingDisabled, match="readiness report"):
        assert_live_trading_allowed(live)
    report = tmp_path / "readiness.md"
    report.write_text("reviewed")
    live["live_trading"]["readiness_report"] = str(report)
    assert_live_trading_allowed(live)  # all three gates satisfied -> no exception


# ----------------------------------------------------------------------- data


def _raw(rows):
    return pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])


def test_validate_minutes_detects_and_cleans_every_issue():
    ok = [10, 10.1, 9.9, 10]
    raw = _raw([
        [180, *ok, 1],                    # unsorted
        [0, *ok, 1],
        [60, *ok, 1],
        [60, *ok, 1],                     # exact duplicate
        [120, *ok, 1],
        [120, 10, 10.2, 9.9, 10.1, 1],    # conflicting duplicate
        [240, np.nan, 10.1, 9.9, 10, 1],  # null
        [300, -1, 10.1, 9.9, 10, 1],      # non-positive price
        [330, *ok, 1],                    # misaligned
        [360, 10, 9.95, 9.9, 10, 1],      # high < close
        [420, *ok, -5],                   # negative volume
        [600, *ok, 0],                    # zero volume; gap 240..540 -> 6 missing minutes
        [660, 10, 30, 9.9, 10, 1],        # extreme range
    ])
    df, rep = validate_minutes(raw)
    assert rep.rows_in == 13
    assert rep.dropped_null_or_nonfinite == 1
    assert rep.dropped_nonpositive_price == 1
    assert rep.dropped_misaligned_ts == 1
    assert rep.dropped_ohlc_inconsistent == 1
    assert rep.dropped_negative_volume == 1
    assert rep.was_unsorted
    assert rep.duplicate_timestamps == 2 and rep.conflicting_duplicates == 1
    assert rep.missing_minutes == 6 and rep.gap_count == 1 and rep.largest_gap_minutes == 6
    assert rep.zero_volume_minutes == 1
    assert rep.extreme_move_minutes == 1
    assert df.index.is_monotonic_increasing and df.index.tz is not None
    assert len(df) == rep.rows_out == 6


def test_resample_complete_bars_and_incomplete_tail():
    idx = pd.date_range("2024-01-01", periods=13, freq="1min", tz="UTC")
    m = pd.DataFrame({"open": np.arange(13.0) + 100, "high": np.arange(13.0) + 101,
                      "low": np.arange(13.0) + 99, "close": np.arange(13.0) + 100.5,
                      "volume": [1.0] * 12 + [0.0]}, index=idx)
    m = m.drop(idx[7])  # internal gap in the 2nd bar
    b = resample_bars(m, "5min")
    assert list(b.index) == [idx[0], idx[5]]            # 10:00-10:13 tail bar (3 min) dropped
    assert b.iloc[0].open == 100 and b.iloc[0].close == 104.5
    assert b.iloc[0].high == 105 and b.iloc[0].low == 99
    assert bool(b.iloc[0].complete) and not bool(b.iloc[1].complete)
    assert b.iloc[1].n_minutes == 4
    # ms-resolution index (pandas may store ms/us): gap logic must still work
    m_ms = m.copy()
    m_ms.index = m_ms.index.as_unit("ms")
    pd.testing.assert_frame_equal(resample_bars(m_ms, "5min").reset_index(drop=True),
                                  b.reset_index(drop=True))


def test_validate_gap_detection_independent_of_index_unit():
    raw = _raw([[0, 1, 1, 1, 1, 1], [60, 1, 1, 1, 1, 1], [300, 1, 1, 1, 1, 1]])
    _, rep = validate_minutes(raw)
    assert rep.missing_minutes == 3  # regression: asi8 unit bug reported 0


class _FakeResp:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        yield self.payload


class _FakeSession:
    def __init__(self, payload: bytes):
        self.payload, self.calls = payload, 0

    def get(self, url, stream, timeout):
        self.calls += 1
        assert url.startswith("https://raw.githubusercontent.com/")
        return _FakeResp(self.payload)


def test_download_records_provenance_and_skips_verified_file(tmp_path):
    src = dl.SOURCES["bitstamp_btcusd_1m_updates"]
    sess = _FakeSession(b"timestamp,open,high,low,close,volume\n0,1,1,1,1,1\n")
    e1 = dl.download_source(src, tmp_path, session=sess)
    assert e1["sha256"] == dl.sha256_file(tmp_path / "btcusd_bitstamp_1min_latest.csv")
    assert e1["commit"] == dl.DATASET_COMMIT and "retrieved_at_utc" in e1 and e1["license"]
    dl.download_source(src, tmp_path, session=sess)
    assert sess.calls == 1  # second call verified the hash and skipped the download


def test_pipeline_end_to_end_on_synthetic_raw(tmp_path):
    raw_dir, clean_dir = tmp_path / "raw", tmp_path / "clean"
    raw_dir.mkdir()
    start = int(pd.Timestamp("2020-01-01", tz="UTC").timestamp())
    n = 3 * 24 * 60
    ts = start + 60 * np.arange(n)
    px = 100 + np.sin(np.arange(n) / 50)
    df = pd.DataFrame({"timestamp": ts, "open": px, "high": px + 0.1, "low": px - 0.1, "close": px,
                       "volume": 1.0})
    half = n // 2
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(df.iloc[:half].to_csv(index=False).encode())
    (raw_dir / "btcusd_bitstamp_1min_2012-2025.csv.gz").write_bytes(buf.getvalue())
    df.iloc[half - 5:].to_csv(raw_dir / "btcusd_bitstamp_1min_latest.csv", index=False)  # 5 overlap rows
    rep = build(raw_dir, clean_dir, "2020-01-01", timeframes=("15min", "1h"))
    assert rep["minute_validation"]["duplicate_timestamps"] == 5
    assert rep["minute_validation"]["missing_minutes"] == 0
    bars = pd.read_parquet(clean_dir / "btcusd_1h.parquet")
    assert len(bars) == 72 and bars["complete"].all()
    assert json.loads((clean_dir / "validation_report.json").read_text())["bars"]["15min"]["rows"] == 288


# ------------------------------------------------------------------- features


def test_sma_ema_hand_values():
    x = pd.Series([1.0, 2, 3, 4, 5])
    assert F.sma(x, 3).tolist()[2:] == [2, 3, 4]
    assert np.allclose(F.ema(x, 3).to_numpy()[2:], [2.25, 3.125, 4.0625])
    assert F.ema(x, 3).isna().sum() == 2


def test_atr_constant_true_range_and_adx_regimes():
    bars = make_bars([(100, 101, 99, 100)] * 50)
    assert F.atr(bars, 14).iloc[-1] == pytest.approx(2.0)
    trend = make_bars([(100 + i, 101.5 + i, 99.8 + i, 101 + i) for i in range(80)])
    assert F.adx(trend, 14).iloc[-1] > 50
    z = F.zscore(pd.Series([1.0, 1, 1, 1, 5]), 5)
    assert z.iloc[-1] == pytest.approx((5 - 1.8) / np.std([1, 1, 1, 1, 5]))


def test_rolling_features_are_causal():
    rng = np.random.default_rng(0)
    bars = make_bars([(p, p + 1, p - 1, p) for p in 100 + rng.normal(0, 1, 300).cumsum()])
    funcs = [lambda b: F.atr(b, 14), lambda b: F.adx(b, 14), lambda b: F.ema(b.close, 20),
             lambda b: F.zscore(b.close, 20), lambda b: F.rolling_high(b.high, 10)]
    for f in funcs:
        full = f(bars)
        part = f(bars.iloc[:200])
        pd.testing.assert_series_equal(full.iloc[:200], part, check_names=False)
