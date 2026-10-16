# Experiment & Decision Log

Chronological record of experiments, failures, fixes and decisions (2026-10-16, single session).
Machine-readable record of **every** backtest run (181 entries: dev 53, val 53, walk-forward 50,
test 25; each with git commit, data hashes, parameters, period, cost scenario and metrics):
`experiment_log.jsonl`.

| # | Step | Command / action | Result | Decision |
|---|---|---|---|---|
| 1 | Environment inventory | `curl` to Kraken, Binance, Coinbase, Yahoo, Kaggle, HF, CryptoDataDownload, GitHub | all exchange/data hosts **403/DNS-blocked**; GitHub raw reachable | use GitHub-hosted Bitstamp 1m dataset; document blocked Kraken access |
| 2 | Data download | `python -m qtrade.data.download` | 93.8 MB + 52.0 MB, pinned commit `b1d538ca`; history SHA-256 = maintainer's manifest | accepted |
| 3 | Validation + resampling | `python -m qtrade.data.pipeline` | 5,675,144 minutes 2016-01-01→2026-10-16; 0 duplicates/OHLC errors; 325,863 zero-volume minutes; 15 zero-volume runs ≥ 60 min | accepted; zero-trade bars may not trigger entries |
| 4 | Sanity check vs. known prices | daily bars on 2017-12-17, 2020-03-12, 2021-11-10, 2022-11-09, 2024-03-14 | match known BTC history (e.g. 69,000 ATH on 2021-11-10) | accepted |
| 5 | Smoke backtests (dev data, 2021-H2) | ad-hoc script | **bug:** trades-per-day never reset; ORB produced 0 signals | root cause below |
| 6 | **Bug: timestamp unit** | inspected `DatetimeIndex.asi8` | pandas 3 stores s/ms units; code assumed ns → wrong day keys, bar spacing **and the data-gap check (reported 0 gaps invalidly)** | fixed with `epoch_ns()`; pipeline re-run (still 0 gaps — now valid); regression test added |
| 7 | Engine rule change (before pre-registration) | design review | cancelling market entries that gap through the stop is unrealistic | market entries always fill; stop exits at the worse open on the same bar |
| 8 | Cost model update (before pre-registration) | web research | Kraken fees changed 2026-07-09 (tier 1: 0.40/0.80%; tier 3: 0.22/0.38%) | baseline = tier 3; stress = tier 1 |
| 9 | Paper vs. backtest equivalence (real data, 2021) | `equiv.py` C1 | entries/exits identical; **bug:** P&L off by cents on shorts (entry-bar financing not attributed) | added financing ledger → 0 mismatches |
| 10 | Equivalence C2, C3, C4 (real data) | `equiv.py` | 0 mismatches (C3: one $0.0001 float difference) | accepted |
| 11 | **Pre-registration** | commit `953093a` | splits, 33-trial grid, costs, criteria fixed | — |
| 12 | Test suite development | `pytest` | failures found and resolved: (a) SweepFVG look-ahead test vacuous on short data → longer data + non-vacuity guard; (b) **mutation test showed the perturbation check missed an injected leak** → reflection-based perturbation at 6 cut points; (c) **empty-input crash** in `true_range` → fixed; (d) test-data error in extreme-move test → fixed test; (e) daily-loss limit also firing in drawdown test (correct behaviour) → fixed test; (f) **drawdown duration measured from first underwater bar instead of the peak** → fixed code; (g) **paper trader adopted fills of unknown orders** (would hide a rogue position) → now halts + alerts; (h) mismatch alert repeated every poll → alert on transition; (i) slow SweepFVG replay test → deterministic scenario | 131 tests pass |
| 13 | Validation script | `python scripts/run_validation.py` | 8/8 checks PASS | — |
| 14 | Dev stage | `run_experiments.py --stage dev` | all baselines lose at baseline costs; C1 −11.5%, C2–C4 ≈ −100%, C5 10 trades | no parameter changes (pre-registered) |
| 15 | Cost sanity check | per-trade cost / notional | 86–89 bp round trip = 2×0.38% + 2×5 bp (+ gaps/financing) | engine costs confirmed correct |
| 16 | Val stage (first attempt) | shell redirect to missing `runs/` dir | exit 1 before running | created `runs/`, re-ran |
| 17 | Val stage | `--stage val` | all lose; C1 −59.3%; criterion 7 now fails for every candidate | proceed to test anyway (report everything) |
| 18 | Walk-forward | `--stage wf` | all OOS negative (C1 −45.2%) | — |
| 19 | Layer-G paper replay | `paper_trade --replay-start 2026-08-01 --replay-end 2026-10-15` ×2 (uninterrupted vs. restarted) | 24 trades, identical after restart, 48 unique orders, 0 alerts | PASS (mechanics) |
| 20 | **Test stage (holdout), once** | `--stage test` (lock written 13:51 UTC, commit `2d24230`) | C1–C4 FAILED, C5 INSUFFICIENT EVIDENCE | final verdict: no edge demonstrated |
| 21 | Real-data SweepFVG equivalence | first window (Mar–Apr 2021) had **no trades** → crashed on empty frame (vacuous); re-run on Jul–Aug 2023 window containing trades | see `test_report.md` | — |
| 22 | Descriptive analysis | `python scripts/analyze_results.py` | break-even costs, regimes | no effect on verdicts |
| 23 | Independent audit | read-only review by a separate agent | see `test_report.md` §Audit | fixes applied and re-tested where needed |

## Deviations from the pre-registration

* **DSR variance input.** The methodology fixed N = 33 trials but not the cross-trial Sharpe
  variance; the implementation used the variance of daily Sharpe across the 33 validation-grid
  configurations. This inflates the deflation benchmark (strategies with catastrophic losses
  widen the variance) and makes the DSR uninformative. Verdicts do not depend on it (all test
  Sharpe ratios are negative).
* **Random-control matching.** Controls were matched to the candidate's *signal* count (as
  written), which exceeds executed trades for C1/C2; "beats controls" is therefore weak evidence.
* No strategy parameter, cost assumption, split or criterion was changed after any validation or
  test result was seen.
