# Test Plan

Written before the final (test-period) evaluation. "Actual" columns are filled from executed
runs; nothing is marked PASS unless the command was executed and its output inspected.
Full command output and environment are in `test_report.md`.

**One-command validation:** `python scripts/run_validation.py` (exit code ≠ 0 if any mandatory
check fails). CI runs the same script (`.github/workflows/validate.yml`).

## Minimum acceptance criteria (software)

| # | Criterion | How verified |
|---|---|---|
| S1 | Project imports and starts | `run_validation.py` imports check; CLI tests start both entry points |
| S2 | All mandatory unit tests pass | `pytest` (layers B) |
| S3 | All mandatory integration tests pass | `pytest` (layers C, G) |
| S4 | No known critical risk-control defects | risk tests + paper failure tests; open issues listed in `test_report.md` |
| S5 | Backtests reproducible | `test_cli.py::test_backtest_cli_runs_and_is_reproducible`, validation step 8 |
| S6 | Transaction costs included | hand-calculated cost tests; `total_costs > 0` checks |
| S7 | Out-of-sample results reported honestly | `results.md` (all candidates, failures included) |
| S8 | Failure/recovery scenarios tested | `tests/test_paper.py`, `tests/test_execution.py` |
| S9 | Paper mode cannot submit real-money orders | type/config guards + tests; private client gated |
| S10 | Reproduction documented | `README.md`, `test_report.md` |

Software correctness says nothing about profitability (strategy criteria are in `backtest_methodology.md` §8).

## Test inventory

| Layer | Test (file::name) | Purpose | Expected result |
|---|---|---|---|
| A | `run_validation.py` compile / imports / ruff | syntax, imports, lint | all PASS |
| A | `run_validation.py` config files | every `configs/*.yaml` valid, live disabled | PASS |
| A | `run_validation.py` secrets scan + `test_cli::test_secret_scanner_flags_planted_key` | no secrets committed; scanner works | clean; planted keys detected |
| A | `test_config_data_features::test_invalid_config_rejected` (8 cases), `test_missing_config_file` | invalid/missing config fails loudly | ConfigError |
| A | `test_config_data_features::test_live_trading_gate` | live requires config + env approval + readiness report | raises until all 3 gates met |
| B | `test_engine.py` (16 tests) | fills, fees, slippage, gaps, stop-first, limit trade-through, expiry, short financing, time exit, trailing stops, sizing caps, stale bars, trade limits, accounting identity, buy-and-hold — **hand-calculated expected values** | exact match |
| B | `test_strategies.py` (17 tests) | ORB (DST-aware), SMC sweep→MSS→FVG on a hand-built day, failed sweep, pre-taken level, Donchian, Bollinger, intraday momentum, signal validation, empty input | exact signals |
| B | `test_risk_metrics.py` (risk: 12) | each risk control independently of strategies; persistence | approve/reject with reason |
| B | `test_risk_metrics.py` (metrics: 6) | drawdown, duration, Sharpe/Sortino, PF, expectancy, PSR/DSR, bootstrap | known values |
| B | `test_execution.py` (23) | order validation edge cases (zero/negative/NaN qty, precision), simulator, Kraken signing vector, mocked REST errors, private client gated | as specified |
| B/C | `test_config_data_features.py` data tests | validation counts every defect; resampling; incomplete tail; ms-unit regression; download provenance; pipeline end-to-end | exact counts |
| C | `test_paper::test_paper_replay_matches_backtest_trade_for_trade` | signals → risk → orders → fills → positions → P&L consistent with the backtester | identical trades and P&L |
| C | `test_paper::test_limit_entry_bracket_and_session_exit_match_backtest` (2) | limit/bracket/session-exit path | identical |
| C | `test_cli.py` (4) | CLI entry points, reproducible outputs, error exit codes | exit 0/2 as specified |
| D | `test_lookahead.py` truncation (9) + reflection (9) + real data (2) | no future data in any strategy | signals unchanged |
| D | `test_engine::test_no_trading_outside_window_and_flat_at_end`, stale-bar test | correct candles, incomplete-candle handling | as specified |
| D | mutation check (documented in `test_report.md`) | look-ahead tests catch an injected leak | leak detected |
| E | `scripts/run_experiments.py --stage dev/val/wf/test` | OOS, walk-forward, cost stress, parameter grid, random controls | results reported in `results.md` |
| F | `test_paper.py`: restart, emergency stop, stale/malformed/duplicate data, exchange timeouts/rate limits/partial fills/duplicate fills, unexpected position, risk-limit breach, live-config refusal | fail safe, reconcile, no duplicates | as specified |
| F | `test_execution.py` fault-injection, reduce-only, persistence | exchange-side failure modes | as specified |
| G | `python -m qtrade.paper_trade --feed replay` on recent data | paper trading over a predefined replay window | trades logged, books consistent |
| G | live-feed paper trading (Kraken OHLC) | real-time signal timing | **BLOCKED** (api.kraken.com denied by network policy) |

## Acceptance thresholds for Layer G (replay paper trading)

Predefined before running: replay window 2026-08-01 → 2026-10-15 (last ~2.5 months of data,
inside the test period), strategy = C1 donchian_trend baseline with `configs/paper.yaml` risk
settings. Pass = completes without unhandled errors; internal position equals simulated-exchange
position at every step (no mismatch alerts); no duplicate client order ids; every fill has fees
recorded; restart mid-window produces identical trades. Profitability is **not** a pass criterion
(sample far too small).
