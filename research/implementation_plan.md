# Implementation Plan

Status legend: ✅ done and tested · 🟡 partial · ⛔ blocked · ⬜ not started.
Order reflects the mission's execution stages; later items depend on earlier ones.

| # | Task | Depends on | Acceptance criteria | Tests | Status |
|---|---|---|---|---|---|
| 1 | Environment & source inventory | — | reachable/blocked hosts documented | `data_sources.md` §12 | ✅ |
| 2 | Trader investigation, strategy taxonomy | 1 | cited, verification status per trader | — (documents) | ✅ (snippet-level sources; see limits) |
| 3 | Data download with provenance | 1 | pinned commit, sha256, retrieval time, licence | `test_download_records_provenance…` | ✅ |
| 4 | Validation + complete-bar resampling | 3 | every defect class counted; incomplete bars flagged | data tests | ✅ |
| 5 | Causal features + strategies C1–C5 | 4 | no look-ahead; hand scenarios exact | `test_lookahead.py`, `test_strategies.py` | ✅ |
| 6 | Backtest engine (conservative fills, costs) | 5 | hand-calculated examples exact; accounting identity | `test_engine.py` | ✅ |
| 7 | Metrics + bootstrap + DSR | 6 | known-value tests | `test_risk_metrics.py` | ✅ |
| 8 | Risk manager | 6 | each control tested in isolation | `test_risk_metrics.py` | ✅ |
| 9 | Pre-registration of experiments | 5–8 | committed before val/test results | git history (`953093a`) | ✅ |
| 10 | Dev / validation / walk-forward / test experiments | 9 | all results reported incl. failures | `run_experiments.py` | see `results.md` |
| 11 | Order model, simulator with faults | 6 | idempotent, partial fills, rejects, timeouts | `test_execution.py` | ✅ |
| 12 | Paper trader (OMS, reconciliation, persistence, alerts) | 8, 11 | replay == backtest; restart-safe; fail-safe | `test_paper.py` | ✅ |
| 13 | Validation script + CI | all | non-zero exit on failure; no live/secrets | `run_validation.py`, CI workflow | ✅ |
| 14 | Kraken live-feed paper trading | 12 + network access to `api.kraken.com` | ≥ 4 weeks, ≥ 30 signals, zero reconciliation alerts, signal timing ≤ 60 s after bar close | live run log | ⛔ blocked by network policy |
| 15 | Kraken-native historical data (OHLCVT ZIPs / Trades) | network access | re-run all experiments on Kraken prices | experiment re-run | ⛔ |
| 16 | 1-minute intrabar resolution for 5m strategies ("bar magnifier") | 4 | stop/target ordering resolved from 1m data; compare with stop-first assumption | new engine tests | ⬜ (next) |
| 17 | Client-side OCO for Kraken (one conditional close per order) | 14 | bracket semantics reproduced with separate orders; tested on Kraken's validate-only mode | integration tests | ⬜ |
| 18 | Alert delivery (webhook/e-mail) | 12 | alerts delivered; failures logged | mocked tests | 🟡 file-based only |
| 19 | Live-trading readiness report + human approval | 14, 15, 17, results | see `final_recommendation.md` §"evidence required" | — | ⬜ not justified by current evidence |

## Next concrete actions

1. Decide, based on `final_recommendation.md`, whether any candidate merits further work (the
   pre-registered criteria determine this; do not re-tune on the 2024-2026 holdout).
2. If continuing research: obtain Kraken-native data (allow `api.kraken.com` or download Kraken's
   OHLCVT archive), add 1-minute intrabar resolution (task 16), and design *new* hypotheses with a
   **fresh** untouched holdout (e.g. data after 2026-10-15 collected via paper trading).
3. Allow `api.kraken.com` in the environment's network settings to run live-feed paper trading
   (task 14) — still simulated orders only.
