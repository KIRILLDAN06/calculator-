# qtrade — research-first systematic trading (BTC/USD)

A reproducible research and paper-trading framework built to answer one question honestly:
**do any publicly described day-trading strategies show a genuine, cost-surviving edge?**
It contains a validated data pipeline, a conservative event-driven backtester, independent risk
controls, a fault-injectable simulated exchange, a restart-safe paper trader, and 131 automated tests.

> **Live trading is disabled.** No real-money order has been placed or can be placed without three
> separate human-controlled gates (see `research/risk_management.md`). Software tests passing is
> not evidence of profitability. Read `research/final_recommendation.md` first.

(The repository also still contains `index.html`, an unrelated browser calculator from its first commit.)

## Quick start

```bash
python -m pip install -r requirements.txt && python -m pip install -e .

# 1. data (≈150 MB from a pinned GitHub commit; SHA-256 recorded in data/raw/manifest.json)
python -m qtrade.data.download
python -m qtrade.data.pipeline            # validate + build complete bars -> data/clean/

# 2. validation suite (lint, configs, live-gate, secrets scan, 131 tests, reproducible backtest)
python scripts/run_validation.py          # exit code != 0 on any mandatory failure

# 3. a single backtest
python -m qtrade.backtest --config configs/backtest.yaml --strategy orb --start 2022-01-01 --end 2024-01-01

# 4. the pre-registered experiments (see research/backtest_methodology.md)
python scripts/run_experiments.py --stage dev
python scripts/run_experiments.py --stage val
python scripts/run_experiments.py --stage wf
python scripts/run_experiments.py --stage test     # holdout; locked after first run

# 5. paper trading (simulated orders only) on replayed data
python -m qtrade.paper_trade --config configs/paper.yaml --replay-start 2026-08-01 --replay-end 2026-10-15 --fresh
#    live-feed paper trading (still simulated orders) needs network access to api.kraken.com:
python -m qtrade.paper_trade --config configs/paper.yaml --feed kraken
```

Emergency stop for a running paper trader: `touch state/EMERGENCY_STOP` (flattens and halts).

## Layout

```
src/qtrade/
  config.py              defaults + YAML + validation; live-trading gate
  data/                  download (provenance), validate, bars (complete-bar resampling), pipeline
  features.py            causal indicators, NY session clock, confirmed fractal swings
  strategies/            signal contract (base.py), C1-C5 + controls
  backtest/              engine (fills/costs), metrics, stats (bootstrap, PSR/DSR), CLI
  risk.py                independent risk manager (shared by backtest and paper)
  execution/             orders, simulated exchange (faults), Kraken adapter, feeds
  paper.py, paper_trade.py   paper trader (OMS, reconciliation, persistence, alerts) + CLI
  experiments.py         pre-registered experiment stages
configs/                 backtest.yaml, paper.yaml (no secrets; live disabled)
scripts/                 run_validation.py, run_experiments.py
tests/                   131 tests across layers A-G
research/                all research deliverables (start with README.md there)
PROJECT_STATUS.md        requirement-by-requirement PASS / FAIL / BLOCKED / NOT TESTED
```

## Data licence

Market data comes from [ff137/bitstamp-btcusd-minute-data](https://github.com/ff137/bitstamp-btcusd-minute-data):
history © "Zielak (mczielinski), Bitcoin Historical Data, Kaggle" under CC BY-SA 4.0; updates under
CC BY 4.0. Data files are downloaded, not committed.
