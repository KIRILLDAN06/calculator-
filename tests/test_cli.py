"""Layer A/C: command-line entry points end to end (subprocess), on synthetic data."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from conftest import random_walk_bars

ROOT = Path(__file__).resolve().parents[1]


def _run(*args, cwd=ROOT):
    return subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True, timeout=600)


def _setup(tmp_path, mode="backtest", strategy="donchian_trend"):
    clean = tmp_path / "clean"
    clean.mkdir()
    bars = random_walk_bars(2000, tf="1h", seed=4, vol=0.006, start="2024-01-01")
    bars.to_parquet(clean / "btcusd_1h.parquet")
    cfg = {
        "mode": mode, "data": {"clean_dir": str(clean)}, "strategy": {"name": strategy, "params": {}},
        "backtest": {"start": "2024-01-20", "end": "2024-03-20"},
        "paper": {"state_file": str(tmp_path / "st.json"), "exchange_state_file": str(tmp_path / "ex.json"),
                  "alerts_file": str(tmp_path / "alerts.jsonl"), "log_file": str(tmp_path / "paper.log"),
                  "kill_file": str(tmp_path / "STOP")},
    }
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return path


def test_backtest_cli_runs_and_is_reproducible(tmp_path):
    cfg = _setup(tmp_path)
    r1 = _run("-m", "qtrade.backtest", "--config", str(cfg), "--out", str(tmp_path / "o1"))
    r2 = _run("-m", "qtrade.backtest", "--config", str(cfg), "--out", str(tmp_path / "o2"))
    assert r1.returncode == 0, r1.stderr
    assert r2.returncode == 0, r2.stderr
    m1 = json.loads((tmp_path / "o1" / "metrics.json").read_text())
    m2 = json.loads((tmp_path / "o2" / "metrics.json").read_text())
    assert m1 == m2 and m1["n_trades"] > 0 and m1["total_costs"] > 0
    assert (tmp_path / "o1" / "trades.csv").read_text() == (tmp_path / "o2" / "trades.csv").read_text()


def test_cli_rejects_missing_and_invalid_config(tmp_path):
    r = _run("-m", "qtrade.backtest", "--config", str(tmp_path / "missing.yaml"))
    assert r.returncode == 2 and "not found" in r.stderr
    bad = tmp_path / "bad.yaml"
    bad.write_text("risk:\n  risk_per_trade: 5\n")
    r = _run("-m", "qtrade.backtest", "--config", str(bad))
    assert r.returncode == 2 and "risk_per_trade" in r.stderr


def test_paper_cli_replay_and_mode_guard(tmp_path):
    cfg = _setup(tmp_path, mode="paper")
    r = _run("-m", "qtrade.paper_trade", "--config", str(cfg), "--replay-start", "2024-02-01",
             "--replay-end", "2024-02-20", "--fresh")
    assert r.returncode == 0, r.stderr
    summary = json.loads(r.stdout[r.stdout.index("{"):])
    assert summary["steps"] > 400 and not summary["halted"]
    assert (tmp_path / "st.json").exists() and (tmp_path / "ex.json").exists()
    (tmp_path / "x").mkdir()
    cfg_bt = _setup(tmp_path / "x", mode="backtest")
    r = _run("-m", "qtrade.paper_trade", "--config", str(cfg_bt), "--replay-start", "2024-02-01")
    assert r.returncode == 2 and "mode: paper" in r.stderr


def test_secret_scanner_flags_planted_key(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    from run_validation import scan_for_secrets

    (tmp_path / "ok.py").write_text("API_KEY = os.environ['QTRADE_KRAKEN_API_KEY']\n")
    assert scan_for_secrets([tmp_path / "ok.py"]) == []
    (tmp_path / "leak.py").write_text('KRAKEN_API_SECRET = "' + "A" * 40 + 'xyz+/=="\n')
    (tmp_path / "pem.txt").write_text("-----BEGIN " + "PRIVATE KEY-----\nabc\n")
    hits = scan_for_secrets([tmp_path / "leak.py", tmp_path / "pem.txt"])
    assert len(hits) == 2
