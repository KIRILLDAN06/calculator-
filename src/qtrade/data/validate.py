"""OHLCV validation for 1-minute candles.

Every check reports counts; cleaning actions are explicit and recorded:

* rows with null / non-finite / non-positive prices or negative volume -> dropped
* OHLC-inconsistent rows (high < max(open, close) or low > min(open, close)) -> dropped
* duplicate timestamps -> first kept; conflicting duplicates counted separately
* timestamps not aligned to the minute grid -> dropped
* missing minutes -> NOT filled here (resampling marks affected bars incomplete)
* extreme moves -> flagged only (genuine crashes exist; we do not delete them)
* runs of zero-volume minutes (the source fills missing minutes with flat,
  zero-volume candles) -> reported as possible outages
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

PRICE_COLS = ["open", "high", "low", "close"]
REQUIRED_COLS = ["timestamp", *PRICE_COLS, "volume"]


@dataclass
class ValidationReport:
    rows_in: int = 0
    rows_out: int = 0
    first_ts: str | None = None
    last_ts: str | None = None
    dropped_null_or_nonfinite: int = 0
    dropped_nonpositive_price: int = 0
    dropped_negative_volume: int = 0
    dropped_ohlc_inconsistent: int = 0
    dropped_misaligned_ts: int = 0
    duplicate_timestamps: int = 0
    conflicting_duplicates: int = 0
    was_unsorted: bool = False
    missing_minutes: int = 0
    gap_count: int = 0
    largest_gap_minutes: int = 0
    zero_volume_minutes: int = 0
    zero_volume_runs_ge_60min: int = 0
    longest_zero_volume_run_min: int = 0
    extreme_move_minutes: int = 0
    extreme_move_examples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _run_lengths(mask: np.ndarray) -> np.ndarray:
    """Lengths of consecutive True runs in a boolean array."""
    if mask.size == 0:
        return np.array([], dtype=int)
    padded = np.concatenate(([False], mask, [False])).astype(np.int8)
    diff = np.diff(padded)
    starts = np.flatnonzero(diff == 1)
    ends = np.flatnonzero(diff == -1)
    return ends - starts


def validate_minutes(raw: pd.DataFrame, extreme_move: float = 0.15) -> tuple[pd.DataFrame, ValidationReport]:
    """Validate and clean raw 1-minute candles.

    ``raw`` must have columns timestamp (UTC epoch seconds, candle open time),
    open, high, low, close, volume. Returns a frame indexed by a tz-aware UTC
    DatetimeIndex and a :class:`ValidationReport`.
    """
    missing = [c for c in REQUIRED_COLS if c not in raw.columns]
    if missing:
        raise ValueError(f"missing required columns: {missing}")
    rep = ValidationReport(rows_in=len(raw))
    df = raw[REQUIRED_COLS].copy()
    for col in REQUIRED_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    finite = np.isfinite(df[REQUIRED_COLS].to_numpy(dtype=float)).all(axis=1)
    rep.dropped_null_or_nonfinite = int((~finite).sum())
    df = df[finite]

    pos = (df[PRICE_COLS] > 0).all(axis=1)
    rep.dropped_nonpositive_price = int((~pos).sum())
    df = df[pos]

    nonneg = df["volume"] >= 0
    rep.dropped_negative_volume = int((~nonneg).sum())
    df = df[nonneg]

    ts = df["timestamp"].astype(np.int64)
    aligned = (ts % 60) == 0
    rep.dropped_misaligned_ts = int((~aligned).sum())
    df = df[aligned.to_numpy()]

    consistent = (df["high"] >= df[["open", "close"]].max(axis=1)) & (
        df["low"] <= df[["open", "close"]].min(axis=1)
    ) & (df["high"] >= df["low"])
    rep.dropped_ohlc_inconsistent = int((~consistent).sum())
    df = df[consistent]

    if not df["timestamp"].is_monotonic_increasing:
        rep.was_unsorted = True
        df = df.sort_values("timestamp", kind="mergesort")

    dup_mask = df["timestamp"].duplicated(keep=False)
    if dup_mask.any():
        dups = df[dup_mask]
        rep.duplicate_timestamps = int(df["timestamp"].duplicated().sum())
        n_variants = dups.drop_duplicates().groupby("timestamp").size()
        rep.conflicting_duplicates = int((n_variants > 1).sum())
        df = df.drop_duplicates(subset="timestamp", keep="first")

    df.index = pd.to_datetime(df["timestamp"].astype(np.int64), unit="s", utc=True)
    df.index.name = "ts"
    df = df.drop(columns="timestamp")

    if len(df):
        rep.first_ts = df.index[0].isoformat()
        rep.last_ts = df.index[-1].isoformat()
        step = np.diff(df.index.asi8) // 60_000_000_000
        gaps = step[step > 1] - 1
        rep.gap_count = int(gaps.size)
        rep.missing_minutes = int(gaps.sum())
        rep.largest_gap_minutes = int(gaps.max()) if gaps.size else 0

        zero = (df["volume"].to_numpy() == 0)
        rep.zero_volume_minutes = int(zero.sum())
        runs = _run_lengths(zero)
        rep.zero_volume_runs_ge_60min = int((runs >= 60).sum())
        rep.longest_zero_volume_run_min = int(runs.max()) if runs.size else 0

        close = df["close"].to_numpy()
        prev = np.concatenate(([close[0]], close[:-1]))
        move = np.abs(np.log(df["high"].to_numpy() / df["low"].to_numpy()))
        jump = np.abs(np.log(close / prev))
        extreme = (move > extreme_move) | (jump > extreme_move)
        rep.extreme_move_minutes = int(extreme.sum())
        rep.extreme_move_examples = [t.isoformat() for t in df.index[extreme][:10]]

    rep.rows_out = len(df)
    return df, rep
