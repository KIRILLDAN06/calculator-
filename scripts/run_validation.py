#!/usr/bin/env python
"""Run the safe validation suite and exit non-zero if any mandatory check fails.

    python scripts/run_validation.py            # everything
    python scripts/run_validation.py --skip-slow

Checks (all offline; none places orders or enables live trading):
  1. syntax / byte-compilation          5. live-trading gate closed by default
  2. package imports                    6. secrets scan of tracked files
  3. lint (ruff)                        7. pytest (unit, integration, failure, look-ahead, paper)
  4. config files valid, live disabled  8. reproducible backtest smoke run (if dataset present)
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_-]?secret|secret[_-]?key|private[_-]?key|api[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9+/=_\-]{24,}['\"]"),
    re.compile(r"(?i)aws_secret_access_key\s*[:=]"),
]
# Kraken's *published documentation example* secret, used only in the signature unit test.
ALLOWLIST = {"kQH5HW/8p1uGOVjbgWA7FunAmGO8lsSUXNsu3eow76sz84Q18fWxnyRzBHCd3pd5nE9qa99HAZtuZuj6F1huXg=="}


def scan_for_secrets(paths: list[Path]) -> list[str]:
    hits = []
    for p in paths:
        try:
            text = p.read_text(errors="ignore")
        except (IsADirectoryError, FileNotFoundError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if any(a in line for a in ALLOWLIST):
                continue
            if any(rx.search(line) for rx in SECRET_PATTERNS):
                hits.append(f"{p}:{i}")
    return hits


def _sh(cmd: list[str], timeout: int = 3600) -> tuple[bool, str]:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=env)
    return r.returncode == 0, (r.stdout + r.stderr)[-4000:]


def check_compile():
    return _sh([sys.executable, "-m", "compileall", "-q", "src", "scripts", "tests"])


def check_imports():
    mods = ["qtrade", "qtrade.config", "qtrade.features", "qtrade.risk", "qtrade.paper", "qtrade.paper_trade",
            "qtrade.data.download", "qtrade.data.validate", "qtrade.data.bars", "qtrade.data.pipeline",
            "qtrade.backtest.engine", "qtrade.backtest.metrics", "qtrade.backtest.stats",
            "qtrade.backtest.__main__", "qtrade.execution.orders", "qtrade.execution.simulator",
            "qtrade.execution.kraken", "qtrade.execution.feeds", "qtrade.strategies"]
    failed = []
    for m in mods:
        try:
            importlib.import_module(m)
        except Exception as exc:  # noqa: BLE001 - report every import failure
            failed.append(f"{m}: {exc!r}")
    return not failed, "\n".join(failed) or f"{len(mods)} modules imported"


def check_lint():
    try:
        return _sh([sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"])
    except FileNotFoundError:
        return False, "ruff not installed"


def check_configs():
    from qtrade.config import load_config

    msgs, ok = [], True
    for p in sorted((ROOT / "configs").glob("*.yaml")):
        try:
            cfg = load_config(p)
            if cfg["live_trading"]["enabled"] or cfg["mode"] == "live":
                ok = False
                msgs.append(f"{p.name}: LIVE TRADING ENABLED")
            else:
                msgs.append(f"{p.name}: valid, live disabled")
        except Exception as exc:  # noqa: BLE001
            ok = False
            msgs.append(f"{p.name}: {exc}")
    return ok, "\n".join(msgs)


def check_live_gate():
    from qtrade.config import LIVE_APPROVAL_ENV, LiveTradingDisabled, assert_live_trading_allowed, load_config

    if os.environ.get(LIVE_APPROVAL_ENV):
        return False, f"{LIVE_APPROVAL_ENV} is set in the validation environment"
    for p in sorted((ROOT / "configs").glob("*.yaml")):
        try:
            assert_live_trading_allowed(load_config(p))
            return False, f"{p.name}: live gate OPEN"
        except LiveTradingDisabled:
            pass
    return True, "live-trading gate closed for every config"


def check_secrets():
    r = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    files = [ROOT / f for f in r.stdout.splitlines()] if r.returncode == 0 else list(ROOT.rglob("*.py"))
    hits = scan_for_secrets(files)
    tracked_env = [f for f in r.stdout.splitlines() if Path(f).name in {".env", "secrets.yaml"}]
    return not hits and not tracked_env, "\n".join(hits + tracked_env) or f"{len(files)} tracked files clean"


def check_pytest(skip_slow: bool):
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:logging"]
    if skip_slow:
        cmd += ["--deselect", "tests/test_paper.py"]
    ok, out = _sh(cmd)
    summary = [ln for ln in out.splitlines() if ("passed" in ln or "failed" in ln or "error" in ln)][-1:]
    return ok, "\n".join(summary) or out[-1500:]


def check_reproducible_backtest():
    if not (ROOT / "data/clean/btcusd_1h.parquet").exists():
        return None, "SKIPPED: dataset not downloaded (python -m qtrade.data.download && python -m qtrade.data.pipeline)"
    outs = []
    for _ in range(2):
        d = tempfile.mkdtemp()
        ok, out = _sh([sys.executable, "-m", "qtrade.backtest", "--config", "configs/backtest.yaml",
                       "--strategy", "donchian_trend", "--start", "2023-01-01", "--end", "2023-07-01",
                       "--out", d])
        if not ok:
            return False, out
        outs.append(json.loads(Path(d, "metrics.json").read_text()))
    same = outs[0] == outs[1]
    return same, f"two runs identical: {same}; trades={outs[0]['n_trades']} costs={outs[0]['total_costs']:.2f}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-slow", action="store_true", help="skip the slower paper-trading integration tests")
    args = ap.parse_args(argv)
    checks = [
        ("compile", check_compile, True),
        ("imports", check_imports, True),
        ("lint (ruff)", check_lint, True),
        ("config files", check_configs, True),
        ("live-trading gate", check_live_gate, True),
        ("secrets scan", check_secrets, True),
        ("pytest", lambda: check_pytest(args.skip_slow), True),
        ("reproducible backtest", check_reproducible_backtest, False),
    ]
    failed = False
    print(f"{'check':<24} {'status':<8} seconds  detail")
    for name, fn, mandatory in checks:
        t = time.time()
        try:
            ok, detail = fn()
        except Exception as exc:  # noqa: BLE001
            ok, detail = False, repr(exc)
        status = "SKIP" if ok is None else ("PASS" if ok else ("FAIL" if mandatory else "WARN"))
        failed |= status == "FAIL"
        first = detail.strip().splitlines()[-1] if detail.strip() else ""
        print(f"{name:<24} {status:<8} {time.time() - t:7.1f}  {first}")
        if status in ("FAIL", "WARN"):
            print("    " + detail.strip().replace("\n", "\n    ")[:3000])
    print("RESULT:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
