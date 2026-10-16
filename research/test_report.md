# Test Report

Date: 2026-10-16. Everything below was **executed** in this environment unless explicitly marked
otherwise; nothing is reported as passing on the basis of code inspection alone.

## 1. Environment

| Item | Value |
|---|---|
| OS / kernel | Linux 6.18.44 (cloud container), 4 CPUs |
| Python | 3.13.16 |
| Packages | numpy 2.5.3, pandas 3.0.5, pyarrow 26.0.0, scipy 1.18.1, PyYAML 6.0.1, requests 2.34.2, pytest 9.1.1, ruff 0.16.8 (pinned in `requirements.txt`) |
| Data | `ff137/bitstamp-btcusd-minute-data` @ `b1d538ca`; history SHA-256 `1be15206…` (matches maintainer manifest); clean-bar hashes in `data/clean/validation_report.json` |
| Network | exchange APIs blocked (403 at proxy); GitHub reachable |

## 2. Commands executed

```bash
python -m pip install -e .
python -m qtrade.data.download && python -m qtrade.data.pipeline
python scripts/run_validation.py                       # 8 checks
python -m pytest -q                                    # full suite
python scripts/run_experiments.py --stage dev|val|wf|test
python scripts/analyze_results.py
python -m qtrade.paper_trade --config runs/paper_g/A.yaml --replay-start 2026-08-01 --replay-end 2026-10-15 --fresh
python -m qtrade.paper_trade --config runs/paper_g/B.yaml --replay-start 2026-08-01 --replay-end 2026-09-10 --fresh
python -m qtrade.paper_trade --config runs/paper_g/B.yaml --replay-start 2026-09-10 --replay-end 2026-10-15
python <scratchpad>/equiv.py <strategy> <warmup> <start> <end> [window]   # paper-vs-backtest on real data
```

## 3. Results by layer

| Layer | Tests | Passed | Failed | Skipped | Notes |
|---|---|---|---|---|---|
| A static/basic | compile, imports (19 modules), ruff, configs, live gate, secrets scan + 11 pytest | all | 0 | 0 | `run_validation.py`: 8/8 PASS |
| B unit | engine 16, strategies 17, risk+metrics 21, execution 23, config/data/features 19 | 96 | 0 | 0 | engine expectations hand-calculated |
| C integration | paper-vs-backtest (3), CLI (4), pipeline end-to-end | all | 0 | 0 | |
| D backtest correctness | look-ahead 21 (incl. 2 on real data), stale/incomplete bars, reproducibility | all | 0 | 0 | mutation-checked (§5) |
| E robustness/OOS | experiment stages dev/val/wf/test | executed | — | — | strategy outcomes in `results.md` (all strategies fail criteria) |
| F failure/recovery | 8 paper tests + simulator fault tests | all | 0 | 0 | |
| G paper trading | replay run + restart run | PASS (mechanics) | 0 | — | live-feed paper: **BLOCKED** |
| **Total pytest** | **131** | **131** | **0** | **0** | 2 data-marked tests skip automatically when the dataset is absent (e.g. CI) |

Final full run: `python scripts/run_validation.py` → `RESULT: PASS` (pytest: 131 passed).

## 4. Bugs discovered and fixed

| # | Bug | Found by | Fix | Regression test |
|---|---|---|---|---|
| 1 | Timestamp unit (`asi8` in s/ms, assumed ns): wrong UTC-day keys (daily trade limit never reset), wrong bar spacing (ORB never fired), **invalid gap check in data validation** | smoke backtest | `features.epoch_ns()`; pipeline re-run | `test_validate_gap_detection_independent_of_index_unit`, ms-index resample test |
| 2 | Per-trade financing attribution in paper trader missed the entry bar | paper-vs-backtest equivalence | financing ledger | `test_paper_replay_matches_backtest_trade_for_trade` |
| 3 | `true_range` crashed on empty input | edge-case test | guard | `test_every_strategy_handles_tiny_and_empty_input` |
| 4 | Drawdown duration measured from first underwater bar, not the peak | metrics test | start at the peak bar | `test_drawdown_sharpe_sortino_known_values` |
| 5 | **Paper trader adopted fills of orders it never placed** (would mask a rogue/manual position) | failure test | unknown fills → critical alert + halt; reconciliation flags mismatch | `test_unexpected_position_halts_new_entries` |
| 6 | Reconciliation alert repeated every poll | failure test | alert on state transition | same |
| 7 | Look-ahead perturbation test could miss a leak (single cut point) | mutation test | reflection perturbation at 6 cut points | `test_future_perturbation_invariance` |

Test-side corrections (test was wrong, code right): extreme-move test data; daily-loss limit
correctly firing in the drawdown-halt test; non-vacuity guard for SweepFVG look-ahead tests.

## 5. Verification of the verification

* **Hand-verified backtester:** 16 engine tests with expected values computed by hand (fees,
  slippage, gaps, stop-first, limit trade-through, expiry, short financing, time exits, trailing
  stops, sizing caps) plus an accounting identity (final equity = initial + Σ net P&L) on random data.
* **Independent implementation cross-check:** the order-level simulator + paper trader reproduce
  the vectorised engine trade-for-trade on real data: C1 39/39 trades, C2 38/38, C3 90/90 (one exit
  price differs by $0.0001 — floating-point order of operations), C4 20/20 compared, C5 see §8.
* **Mutation test of look-ahead detection:** a strategy peeking one bar ahead is caught by both the
  truncation and the perturbation checks; a centred-window leak is caught by the truncation check.
* **Cost model:** measured round-trip cost 86–89 bp of notional vs. 86 bp expected from first principles.
* **Kraken signing:** reproduces Kraken's published API-Sign example exactly (512-bit HMAC).

## 6. Paper-trading status (Layer G)

| Item | Result |
|---|---|
| Mode | replay of real 1h bars (simulated exchange); **no live feed** (api.kraken.com blocked) |
| Window / strategy | 2026-08-01 → 2026-10-15, C1 donchian_trend, `configs/paper.yaml` risk (0.25%/trade, 10% DD kill switch) |
| Steps / trades | 1,800 bar steps; 24 round trips; 48 orders (all unique client ids); 48 fills, all with fees |
| Consistency | internal position = exchange position throughout (0 mismatch alerts); flat at end |
| Restart | split run (stop at 2026-09-10, new process resumes from state files) → **identical** 24 trades and order ids |
| P&L | +$400.77 (+4.0%), one +$1,165.62 trade; 18/24 trades lost — not evidence of profitability |
| Real-money orders | none possible: `PaperTrader` accepts only `SimulatedExchange`, refuses live configs |

## 7. Failure and recovery results (Layer F, all executed in `tests/test_paper.py` / `test_execution.py`)

API timeouts (accepted and lost) → UNKNOWN state resolved by client id before any new order, no
duplicates · rate limits → skip and retry · partial fills → books consistent, bracket on full fill ·
duplicate fill events → ignored by fill id · stale feed (300 frozen steps) → zero entries + alerts ·
malformed and duplicate bars → dropped + alerts · rejected orders → logged · unexpected position →
halt + single critical alert · process restart → identical results, no duplicate orders ·
missing/invalid config → exit code 2 · drawdown breach → kill switch flattens + halts ·
emergency-stop file → flatten + permanent halt · live config / non-simulated exchange → refused.

## 8. Remaining issues and external blockers

* **BLOCKED:** live-feed paper trading and any Kraken API interaction (network policy).
* **NOT TESTED:** Kraken private endpoints against the real exchange (by design, live disabled);
  client-side OCO for Kraken; webhook alert delivery.
* Bar-level stop/target ordering (no 1-minute intrabar resolution) — conservative but approximate.
* Real-data SweepFVG equivalence: Jul–Aug 2023 window (2 real setups) — see appended result below.
* Independent audit findings — see §9.

## 9. Independent audit

(Appended after the read-only audit completes.)

## 10. Reproduction

```bash
git clone <repo> && cd <repo>
python -m pip install -r requirements.txt && python -m pip install -e .
python -m qtrade.data.download && python -m qtrade.data.pipeline     # verifies SHA-256
python scripts/run_validation.py                                    # expect RESULT: PASS
python scripts/run_experiments.py --stage dev && python scripts/run_experiments.py --stage val
python scripts/run_experiments.py --stage wf && python scripts/run_experiments.py --stage test --allow-rerun
python scripts/analyze_results.py                                   # regenerates results_tables.md
```

Expected: identical metrics to `runs/experiments/*/summary.json` (deterministic: seeded controls,
pinned data, no wall-clock dependence).

## 11. Conclusion — what is and is not verified

| Claim | Status |
|---|---|
| Code written for all modules in the architecture | yes |
| Code executed (pipeline, backtests, experiments, paper replay, CLIs) | yes |
| Automated tests passed | 131/131, validation 8/8 |
| Historical strategy performance measured | yes — all candidates unprofitable after costs |
| Paper trading completed | replay mode only; live-feed paper trading **not** run (blocked) |
| Live execution tested | **no** — never authorised, never attempted |
