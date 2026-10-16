# Architecture

Python 3.11+ (tested on 3.13), modular package `qtrade` under `src/`. Strategy logic is
independent of execution: the same `Strategy.generate()` drives the backtester and the paper
trader, and both route every entry through the same `RiskManager`.

```
                    ┌─────────────────────────────── configs/*.yaml (no secrets) ──┐
                    │                                                             │
 data.download ──► data/raw (+manifest, sha256) ──► data.validate ──► data.bars ──► data/clean/*.parquet
 (pinned commit)                                    (report)          (complete bars)      │
                                                                                            │
           ┌────────────────────────────────────────────────────────────────────────────────┤
           ▼                                                                                ▼
   strategies.* (pure, causal)                                              execution.feeds
   generate(bars) -> signals ─────────────┐                          ReplayFeed | KrakenOHLCFeed
           │                              │                                       │
           ▼                              ▼                                       ▼
   backtest.engine ◄── risk.RiskManager ──► paper.PaperTrader ──► execution.simulator.SimulatedExchange
   (fills, costs)                          (OMS, reconcile,       (fills = engine rules, faults)
           │                                state, alerts)
           ▼                                      │                 execution.kraken (public REST;
   backtest.metrics / backtest.stats              ▼                  private calls gated, validate-only)
   experiments (pre-registered stages)     state/*.json, logs/*.jsonl
```

## Modules and responsibilities

| # | Responsibility (spec) | Module | Status |
|---|---|---|---|
| 1 | Market-data ingestion | `data/download.py` (historical), `execution/feeds.py` (`KrakenOHLCFeed`, `ReplayFeed`) | historical: done/tested; Kraken feed: implemented, mocked tests only (network blocked) |
| 2 | Historical storage | `data/raw` (immutable) → `data/clean/*.parquet` | done |
| 3 | Data validation | `data/validate.py`, `execution/feeds.clean_feed_bars` | done/tested |
| 4 | Feature engineering | `features.py` (causal indicators, NY session clock, confirmed fractals) | done/tested |
| 5 | Signal generation | `strategies/` (registry; signal contract in `strategies/base.py`) | done/tested |
| 6 | Portfolio & sizing | `risk.RiskManager.check_entry` (single-instrument, one position) | done/tested |
| 7 | Risk management | `risk.py` | done/tested |
| 8 | Backtesting engine | `backtest/engine.py` | done/tested (hand-verified) |
| 9 | Execution simulator | `execution/simulator.py` (fault injection) | done/tested |
| 10 | Exchange adapter | `execution/kraken.py` | public + signing tested offline; live never exercised |
| 11 | Order management | `paper.PaperTrader` (+ `execution/orders.py`) | done/tested |
| 12 | Position reconciliation | `PaperTrader._reconcile_position / _reconcile_unknown` | done/tested |
| 13 | Monitoring & logging | Python logging + `Alerter` (JSON lines) | done (file-based) |
| 14 | Performance analytics | `backtest/metrics.py`, `backtest/stats.py` | done/tested |
| 15 | Alerts | `paper.Alerter` (file + log; webhook hook point not wired) | partial |
| 16 | Configuration | `config.py` (defaults + YAML + validation; secrets only via env) | done/tested |
| 17 | Automated tests | `tests/` (138 tests), `scripts/run_validation.py`, CI workflow | done |
| 18 | Paper trading mode | `paper.py`, `paper_trade.py` | replay mode done/tested; live-feed mode blocked |
| 19 | Live trading mode | `config.assert_live_trading_allowed` + `KrakenPrivateClient` (validate-only default) | **disabled; not tested; not approved** |

## Key design decisions

* **Signal contract** (`strategies/base.py`): position-agnostic intent per completed bar
  (entry/stop/target/limit/expiry/max-hold/exit/trailing). Strategies never see fills, so a
  risk-rejected entry cannot leak back into strategy state.
* **One fill model, two implementations, cross-checked:** the vectorised-state engine and the
  order-level simulator implement the same rules; paper replay is tested trade-for-trade against
  the backtest (market, limit, bracket, trailing, time and session exits).
* **Determinism:** seeded randomness, pinned data commit + hashes, no wall-clock dependence in
  backtests; deterministic client order ids.
* **Fail-safe defaults:** stale/malformed data → no entries; uncertain order state → reconcile
  before sending; unknown fills → halt; live trading needs three human-controlled gates.
* **Secrets:** read only from `QTRADE_KRAKEN_API_KEY` / `QTRADE_KRAKEN_API_SECRET` at call time by
  the gated private client; configs containing secret-like keys are rejected; a secrets scan runs in
  validation. Recommended key permissions for any future live use: query + trade only, **no
  withdrawal**, IP-restricted.
