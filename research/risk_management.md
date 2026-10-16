# Risk Management

Risk controls live in one independent component, `qtrade.risk.RiskManager`, shared by the backtest
engine and the paper trader. Strategies can only *propose* entries; every entry is sized and
approved (or rejected with a logged reason) by the risk manager, which can also force flattening.
Each control is unit-tested independently of any strategy (`tests/test_risk_metrics.py`) and in
integration (`tests/test_paper.py`).

## Controls and exact behaviour

| Control | Paper default (`configs/paper.yaml`) | Behaviour when breached | Reset |
|---|---|---|---|
| Max risk per trade | 0.25% equity | size = risk budget / stop distance (stop must be on the correct side) | per trade |
| Max leverage / aggregate exposure | 1.0× equity | notional capped | — |
| Max order notional | $1,000,000 | notional capped | — |
| Liquidity (participation) | 5% of prior bar's traded USD | notional capped | — |
| Exchange minimum / precision | 0.0001 BTC, 8 lot decimals, 0.1 USD tick | floor quantity; reject below minimum; limit prices rounded conservatively | — |
| Max open positions | 1 | entry rejected | — |
| Max entries per UTC day | 3 | entry rejected | next UTC day |
| Max daily loss (realised + unrealised) | 2% of day-start equity | **no new entries** for the rest of the UTC day; open position keeps its exchange-side stop | next UTC day |
| Max drawdown (kill switch) | 10% from peak equity | **flatten at next open + permanent halt** | manual (operator deletes state after review) |
| Consecutive losses | 4 | cooldown: no entries for 96 bars | automatic |
| Stale data | 180 s after expected bar close | entry rejected; alert | when fresh data arrives |
| Malformed / duplicate bars | — | dropped before strategy evaluation; alert | — |
| Max spread | 25 bp (when a quote is available) | entry rejected | — |
| Max slippage | 50 bp realised on a taker fill | permanent halt; alert | manual |
| Unexpected fill / unknown order | — | **halt**; fill not adopted; critical alert | manual |
| Position mismatch (internal ≠ exchange) | tolerance 1e-8 BTC | **halt new entries**; critical alert (once per transition) | manual after reconciliation |
| Uncertain order state (submit timeout) | — | order marked UNKNOWN; queried by client id before anything else is sent; exits resubmitted only if confirmed absent | automatic |
| Duplicate orders | deterministic client ids + idempotent exchange | resubmission returns the existing order | — |
| Emergency stop | file `state/EMERGENCY_STOP` | flatten + permanent halt; critical alert | manual |
| Live trading | disabled | three independent gates (config, env approval phrase, readiness report) | human decision only |

Research backtests use the same component with the drawdown kill switch and loss-streak
cooldown **disabled** (drawdown is reported instead) so strategies are compared on equal terms;
see `backtest_methodology.md` §5.

## Important limitations

* **A stop-loss does not guarantee its price.** The engine and simulator fill gapped stops at the
  worse open; real slippage in fast markets can be larger than the modelled 5–10 bp.
* Exchange-side protective orders are modelled as an OCO bracket (stop + target). Kraken spot
  supports one conditional close per order; a live implementation would need client-side OCO
  management or separate orders — **not implemented / not tested live**.
* Margin (shorts) adds liquidation risk not modelled here (no liquidation engine; leverage ≤ 1).
* Rollover rates vary and are locked at execution on Kraken; the model uses a fixed "up to" rate.
* Partial fills on market entries leave the unfilled remainder unprotected until fully filled
  (a bracket is placed on the filled quantity when the order completes or expires).

## Recovery procedure (paper; would apply to live)

1. Process restarts: state (`state/paper_state.json`) and the paper exchange
   (`state/paper_exchange.json`) are written atomically after every step. On start the trader
   reloads both, resolves UNKNOWN orders by client id, ingests missed fills (de-duplicated by fill
   id), reconciles the position, and only then evaluates signals. Bars already processed are not
   re-traded.
2. After any halt: inspect `logs/alerts.jsonl`, reconcile positions/orders manually, decide whether
   to flatten, then archive the state files to reset. Never delete state while a position is open.
3. Data outage: the trader keeps polling; no new entries while data is stale; existing positions
   remain protected by exchange-side stops.
