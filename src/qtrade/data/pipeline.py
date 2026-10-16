"""Build the cleaned dataset: raw files -> validated minutes -> complete bars.

Usage::

    python -m qtrade.data.download            # fetch raw files (pinned commit)
    python -m qtrade.data.pipeline            # validate + resample -> data/clean

Outputs (``data/clean``):
    btcusd_1min.parquet            validated minutes (from --start)
    btcusd_<tf>.parquet            complete-bar flagged resamples
    validation_report.json         every check, count and cleaning action
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from qtrade.data.bars import resample_bars
from qtrade.data.download import SOURCES, sha256_file
from qtrade.data.validate import validate_minutes

log = logging.getLogger(__name__)

DEFAULT_TIMEFRAMES = ("5min", "15min", "30min", "1h", "1D")


def read_raw_minutes(raw_dir: Path) -> pd.DataFrame:
    frames = []
    for src in SOURCES.values():
        path = raw_dir / Path(src.path_in_repo).name
        if not path.exists():
            raise FileNotFoundError(f"{path} missing: run `python -m qtrade.data.download` first")
        log.info("reading %s", path)
        frames.append(pd.read_csv(path, dtype={"timestamp": "int64"}))
    return pd.concat(frames, ignore_index=True)


def build(raw_dir: Path, clean_dir: Path, start: str, timeframes=DEFAULT_TIMEFRAMES) -> dict:
    raw = read_raw_minutes(raw_dir)
    start_ts = int(pd.Timestamp(start, tz="UTC").timestamp())
    raw = raw[raw["timestamp"] >= start_ts]
    minutes, rep = validate_minutes(raw)
    clean_dir.mkdir(parents=True, exist_ok=True)
    minutes.to_parquet(clean_dir / "btcusd_1min.parquet")

    manifest_path = raw_dir / "manifest.json"
    raw_manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    report = {
        "built_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "start": start,
        "raw_manifest": raw_manifest,
        "minute_validation": rep.to_dict(),
        "bars": {},
    }
    for tf in timeframes:
        bars = resample_bars(minutes, tf)
        out = clean_dir / f"btcusd_{tf}.parquet"
        bars.to_parquet(out)
        report["bars"][tf] = {
            "rows": len(bars),
            "incomplete_bars": int((~bars["complete"]).sum()),
            "no_trade_bars": int((bars["n_active"] == 0).sum()),
            "first": bars.index[0].isoformat() if len(bars) else None,
            "last": bars.index[-1].isoformat() if len(bars) else None,
            "sha256": sha256_file(out),
        }
        log.info("wrote %s (%d bars)", out, len(bars))
    (clean_dir / "validation_report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def load_bars(tf: str, clean_dir: str | Path = "data/clean", start: str | None = None,
              end: str | None = None) -> pd.DataFrame:
    """Load cleaned bars for ``tf``; ``end`` is exclusive."""
    path = Path(clean_dir) / f"btcusd_{tf}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing: run `python -m qtrade.data.pipeline` first")
    bars = pd.read_parquet(path)
    if start is not None:
        bars = bars[bars.index >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        bars = bars[bars.index < pd.Timestamp(end, tz="UTC")]
    return bars


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate raw minutes and build clean bars.")
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--clean-dir", default="data/clean")
    parser.add_argument("--start", default="2016-01-01")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    report = build(Path(args.raw_dir), Path(args.clean_dir), args.start)
    print(json.dumps(report["minute_validation"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
