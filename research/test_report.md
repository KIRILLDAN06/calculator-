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
| B unit | engine 18, strategies 17, risk+metrics 21, execution 24, config/data/features 19 | 99 | 0 | 0 | engine expectations hand-calculated |
| C integration | paper-vs-backtest (3), CLI (4), pipeline end-to-end | all | 0 | 0 | |
| D backtest correctness | look-ahead 21 (incl. 2 on real data), stale/incomplete bars, reproducibility | all | 0 | 0 | mutation-checked (§5) |
| E robustness/OOS | experiment stages dev/val/wf/test | executed | — | — | strategy outcomes in `results.md` (all strategies fail criteria) |
| F failure/recovery | 12 paper tests + simulator fault tests | all | 0 | 0 | incl. 4 audit regressions |
| G paper trading | replay run + restart run | PASS (mechanics) | 0 | — | live-feed paper: **BLOCKED** |
| **Total pytest** | **138** | **138** | **0** | **0** | 2 data-marked tests skip automatically when the dataset is absent (e.g. CI) |

Final full run: `python scripts/run_validation.py` → `RESULT: PASS` (pytest: 138 passed).

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
| 8 | **Emergency stop ignored when already halted; failed kill-switch exit never retried** | independent audit | persistent `flatten_required`; flatten re-attempted every step until the exchange is flat (incl. positions not opened by the trader) | `test_emergency_stop_flattens_even_when_already_halted`, `test_flatten_is_retried_after_rejected_exit`, `test_rogue_position_is_flattened_not_adopted` |
| 9 | **Timeout-accepted entry forgotten → second entry order could be sent** | independent audit | UNKNOWN entry found on exchange restored as pending; any working entry blocks new entries; session exit cancels all entry orders | `test_timeout_accepted_entry_never_leads_to_second_entry` |
| 10 | **Partially filled entries unprotected (no stop until fully filled)** | independent audit | bracket created/resized on every fill; triggered stop cancels the remainder | `test_partial_fills_are_protected_immediately…`, `test_stop_breach_during_partial_fill…` |
| 11 | `bars_held` one too high for exits at the open (reporting + control hold time) | independent audit | exposure-based count | `test_day_limit_counts_the_fill_day_and_open_exit_bars_held`, financing test |
| 12 | Risk-manager UTC day rolled at first bar *close* (00:00 fills counted to the previous day) | independent audit | day rolls at bar open; entry checks use the fill day | same + risk test |
| 13 | Drawdown ignored starting equity when the first bar was already below it | independent audit | peak floored at initial equity | `test_drawdown_measured_from_starting_equity` |

All audit regression tests were run against the pre-fix source (stashed) and **failed there**
(10 of 10), then passed on the fixed code.

Test-side corrections (test was wrong, code right): extreme-move test data; daily-loss limit
correctly firing in the drawdown-halt test; non-vacuity guard for SweepFVG look-ahead tests.

## 5. Verification of the verification

* **Hand-verified backtester:** 16 engine tests with expected values computed by hand (fees,
  slippage, gaps, stop-first, limit trade-through, expiry, short financing, time exits, trailing
  stops, sizing caps) plus an accounting identity (final equity = initial + Σ net P&L) on random data.
* **Independent implementation cross-check:** the order-level simulator + paper trader reproduce
  the vectorised engine trade-for-trade on real data: C1 39/39 trades, C2 38/38, C3 90/90 (one exit
  price differs by $0.0001 — floating-point order of operations), C4 20/20 compared, C5 2/2 (the only
  real setups in Jul–Aug 2023; an earlier attempt on a window without setups was vacuous and is not counted).
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
* Supplementary-only analyses (not decision inputs): DSR with null variance; trade-matched controls.
* Simulated short financing is pro-rata per bar (Kraken charges per 4-hour block); difference ≤ ~2 bp per trade.

## 9. Independent audit

A separate agent performed a read-only audit (look-ahead, fills/accounting, metrics/statistics,
paper-trader safety, methodology), confirming each issue with a reproduction.

**Confirmed correct by the auditor:** no look-ahead on real data (19 configurations × 4 cut points,
incl. mid-session cuts — computing signals once over full history then windowing is safe);
accounting identity exact on all test runs; fills conservative (no gap improvement on limits,
stop-first, target ignored on limit fill bar); metrics/PSR/bootstrap formulas correct;
pre-registration followed (methodology committed 13:17 UTC, first result 13:43 UTC); live gates hold.

| Finding | Severity | Resolution |
|---|---|---|
| Emergency stop / kill-switch flatten not retried | major | fixed (#8) |
| Timeout-accepted entry → duplicate entry | major | fixed (#9) |
| Partial fills unprotected | major | fixed (#10) |
| DSR criterion cannot pass (cross-trial variance inflated) | major (methodology) | documented as deviation; supplementary DSR with null variance reported; verdicts unaffected |
| Random controls not matched (signals vs trades, taker vs maker, hold) | major (methodology) | documented; supplementary trade-matched controls reported; verdicts unaffected |
| `bars_held` off by one | minor | fixed (#11) |
| Day-boundary handling | minor | fixed (#12) |
| Drawdown vs starting equity | minor | fixed (#13) |
| Pro-rata short financing | minor | documented (conservative for holds < 4 h) |
| Lock without code/data hash; uncommitted results | minor | lock now hashes code + data; everything committed |
| C5 cost label | minor | fixed in `results_tables.md` |

After the fixes **all experiment stages were re-run** on the fixed code (logged deviation; no
strategy parameter changed). The auditor's bottom line — "nothing overturns *all strategies fail
after costs*" — was confirmed by the re-run.

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
| Automated tests passed | 138/138, validation 8/8 |
| Historical strategy performance measured | yes — all candidates unprofitable after costs |
| Paper trading completed | replay mode only; live-feed paper trading **not** run (blocked) |
| Live execution tested | **no** — never authorised, never attempted |
