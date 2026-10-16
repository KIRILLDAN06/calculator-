"""Reproducible download of raw historical data with a provenance manifest.

The only bulk source reachable from the development environment was the
GitHub-hosted Bitstamp BTC/USD 1-minute dataset (exchange APIs were blocked by
the environment's network policy -- see research/data_sources.md). Files are
pinned to a specific repository commit so that results are reproducible, and
each download is recorded with its SHA-256 and retrieval time.

Raw files are stored unchanged under ``data/raw``; cleaned data is written
separately under ``data/clean`` by :mod:`qtrade.data.pipeline`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import requests

log = logging.getLogger(__name__)

DATASET_REPO = "ff137/bitstamp-btcusd-minute-data"
# Commit inspected on 2026-10-16; data through 2026-10-15 23:59 UTC.
DATASET_COMMIT = "b1d538cad6a9dba28b449d550f1adec7219ac48a"


@dataclass(frozen=True)
class RawSource:
    name: str
    path_in_repo: str
    license: str
    attribution: str

    def url(self, commit: str = DATASET_COMMIT) -> str:
        return f"https://raw.githubusercontent.com/{DATASET_REPO}/{commit}/{self.path_in_repo}"


SOURCES: dict[str, RawSource] = {
    "bitstamp_btcusd_1m_hist": RawSource(
        name="bitstamp_btcusd_1m_hist",
        path_in_repo="data/historical/btcusd_bitstamp_1min_2012-2025.csv.gz",
        license="CC BY-SA 4.0",
        attribution="Zielak (mczielinski), Bitcoin Historical Data, Kaggle (via github.com/ff137/bitstamp-btcusd-minute-data)",
    ),
    "bitstamp_btcusd_1m_updates": RawSource(
        name="bitstamp_btcusd_1m_updates",
        path_in_repo="data/updates/btcusd_bitstamp_1min_latest.csv",
        license="CC BY 4.0",
        attribution="Bitstamp BTC/USD 1-minute data collected by github.com/ff137/bitstamp-btcusd-minute-data",
    ),
}


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def download_source(
    source: RawSource,
    raw_dir: Path,
    commit: str = DATASET_COMMIT,
    session: requests.Session | None = None,
    retries: int = 4,
) -> dict:
    """Download one source to ``raw_dir`` and return its manifest entry.

    Skips the download when the file already exists and matches the manifest.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / Path(source.path_in_repo).name
    manifest_path = raw_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    entry = manifest.get(source.name)
    if entry and dest.exists() and entry.get("commit") == commit and sha256_file(dest) == entry["sha256"]:
        log.info("%s already present and verified (%s)", dest, entry["sha256"][:12])
        return entry

    sess = session or requests.Session()
    url = source.url(commit)
    tmp = dest.with_suffix(dest.suffix + ".part")
    delay = 2.0
    for attempt in range(1, retries + 1):
        try:
            with sess.get(url, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                with tmp.open("wb") as fh:
                    for block in resp.iter_content(chunk_size=1 << 20):
                        fh.write(block)
            break
        except requests.RequestException as exc:
            log.warning("download attempt %d/%d failed for %s: %s", attempt, retries, url, exc)
            if attempt == retries:
                raise
            time.sleep(delay)
            delay *= 2
    tmp.replace(dest)

    entry = {
        "name": source.name,
        "url": url,
        "repo": DATASET_REPO,
        "commit": commit,
        "file": dest.name,
        "bytes": dest.stat().st_size,
        "sha256": sha256_file(dest),
        "retrieved_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "license": source.license,
        "attribution": source.attribution,
    }
    manifest[source.name] = entry
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    log.info("downloaded %s (%d bytes, sha256 %s)", dest, entry["bytes"], entry["sha256"][:12])
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download raw historical market data.")
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--commit", default=DATASET_COMMIT)
    parser.add_argument("--source", choices=sorted(SOURCES), action="append")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for name in args.source or sorted(SOURCES):
        download_source(SOURCES[name], Path(args.raw_dir), commit=args.commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
