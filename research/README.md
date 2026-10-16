# Research: objectives, scope, limitations, status

## Objective

Determine, with reproducible evidence, whether publicly described day-trading strategies (with a
focus on those taught by popular educators such as TJR) have a genuine, repeatable,
cost-surviving statistical edge — and only then build software around what the evidence supports.

## Outcome (short)

**No edge was demonstrated.** Five pre-registered candidates (trend, mean reversion, intraday
momentum, US-open ORB, TJR/SMC-style sweep→BOS→FVG) all lost money after realistic Kraken costs in
validation, walk-forward and the untouched 2024-2026 holdout. See `final_recommendation.md`.
The software (pipeline, backtester, risk manager, simulated exchange, paper trader, 131 tests) is
complete and verified; live trading is disabled and not recommended.

## Reading order

| File | Contents |
|---|---|
| `final_recommendation.md` | answers to the 12 decision questions; what would be needed before live trading |
| `results.md` | every result, failures included; `results_tables.md` = generated tables |
| `backtest_methodology.md` | **pre-registered** splits, costs, metrics, statistics, acceptance criteria |
| `candidate_specifications.md` | exact mechanical rules of every tested strategy |
| `trader_analysis.md` | public traders: claims vs. evidence; testable definitions extracted |
| `strategy_catalog.md` | taxonomy A–H: hypotheses, failure modes, data needs, literature |
| `data_sources.md` | data/API availability, fees, licences, and what was reachable here |
| `source_registry.md` | all sources with type, quality and supported claim |
| `methodology_refs.md` | references for Sharpe annualisation, bootstrap, DSR, walk-forward, fills |
| `risk_management.md` | every risk control and its exact behaviour |
| `architecture.md` | modules and responsibilities |
| `implementation_plan.md` | task status, dependencies, acceptance criteria, next actions |
| `test_plan.md`, `test_report.md` | tests defined up front; what was executed and verified |
| `experiment_log.md`, `experiment_log.jsonl` | every experiment, failure, fix and decision |

## Scope

* **Market:** BTC/USD spot only (Bitstamp 1-minute data 2016-2026; Kraken fee and order rules).
* **Strategies:** five bar-based candidates (5m–1h) plus benchmarks and random controls.
  Order-book / trade-flow strategies were out of scope (no tick/L2 data available).
* **Execution:** simulated only — backtest engine and paper trader with a simulated exchange.

## Limitations (precise)

1. **Network policy blocked all exchange APIs** (Kraken, Binance, Coinbase) and most research
   sites; no Kraken endpoint was ever called live. Kraken's request signing was verified only
   against Kraken's published example; live-feed paper trading could not run.
2. **Venue mismatch:** Bitstamp prices with Kraken costs.
3. **Research sources** were mostly read through search-engine extracts (WebFetch failed on most
   primary domains); TJR's disclosure page and original videos/transcripts could not be read.
4. **Bar-level simulation:** stops/targets inside one 5-minute bar use a conservative stop-first
   rule; no 1-minute intrabar resolution yet.
5. **Single instrument and one interpretation of each strategy**; TJR's method is discretionary,
   so C5 is one operational reading of it, applied to BTC rather than the index futures he trades.
6. The DSR as implemented and the random controls are imperfect (see `results.md` §1).

## Status

All required deliverables exist. Requirement-by-requirement status with evidence:
`../PROJECT_STATUS.md`.
