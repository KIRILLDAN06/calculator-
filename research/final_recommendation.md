# Final Recommendation

**Conclusion: no strategy demonstrated a convincing, cost-surviving edge. Do not build a live
trading bot on any of the tested strategies.** This is a negative result, reported as such — not
a winner manufactured by re-tuning. An untested strategy is a hypothesis; a successful backtest
would not have guaranteed future profits either.

## Answers to the decision framework

**1. Which strategies were investigated?**
Public traders/educators (TJR, ICT, Ross Cameron/Warrior Trading, Kevin Davey, Larry Connors, Mark
Minervini — `trader_analysis.md`) and a taxonomy of ~40 strategy families across price action,
momentum, mean reversion, order flow, volatility/regime, crypto-specific, equity and ML approaches
(`strategy_catalog.md`).

**2. Which could be defined precisely enough to test?**
Five were specified as deterministic state machines and implemented (`candidate_specifications.md`):
C1 Donchian trend (benchmark), C2 Bollinger/ADX mean reversion, C3 first→last half-hour intraday
momentum, C4 US-open opening-range breakout, C5 liquidity-sweep → structure-shift → FVG (TJR/SMC-
style). Order-book/trade-flow strategies were *not* testable: no tick or L2 data was available.
SMT divergence (needs ES+NQ) and discretionary "daily bias" could not be operationalised.

**3. Which traders provided useful, verifiable information?**
Only partially useful, and none verifiable for the strategies tested. TJR's concepts (sweeps, BOS,
FVG, session levels) are publicly described but self-described as discretionary; no audited or
broker-verified performance was found. Useful *verifiable* information came from contest results
(Davey, Minervini — organiser-reported) and published, replicable rules (Connors), none of which
validates the SMC/TJR model. Academic evidence (Taiwan, Brazil, ESMA, SEC) indicates most retail
day traders lose money after costs.

**4. Which profitability claims could not be verified?**
TJR (no performance found; disclosure page unreachable), ICT (none), Ross Cameron (company/CPA
statements reported by third parties but not read; FTC 2022 settlement concerned customer-outcome
marketing), and all vendor claims about ICT/SMC backtests (e.g. a 53% win-rate/1.68 PF claim from a
backtesting-tool vendor).

**5. Which strategies were actually backtested?**
All five candidates, plus buy-and-hold, no-trade and 200-seed random-entry controls, on BTC/USD
2017-01-01 → 2026-10-15 under four cost scenarios, 33 grid configurations and 10 walk-forward windows.

**6. Which survived realistic transaction costs?** **None.** At Kraken tier-3 retail costs
(≈ 86 bp per round trip) every candidate lost money in development, validation, walk-forward and
holdout. Only C1 (in development, 2017-21) and C4 (in validation, 2022-23) were profitable under the
*optimistic* institutional cost scenario, and neither repeated it on the holdout.

**7. Which survived out-of-sample testing?** **None** (validation, walk-forward and holdout all negative).

**8. Which were robust across periods and regimes?** None net of costs. Pre-cost, ORB (C4) was
the only candidate with a positive gross point estimate in all three periods (6–23 bp per trade)
and slightly positive in all four test-period regimes — too small to trade at retail costs, and an
unregistered observation (see 10).

**9. Which failed, and why?**
* C2 Bollinger mean reversion and C3 intraday momentum: **no gross edge at all**; costs alone
  explain the total losses.
* C1 Donchian trend: a real pre-cost edge in 2017-21 (≈ 50 bp/trade) that **decayed** to ≈ 6 bp
  in 2024-26; at ~140 trades/year, costs overwhelm it. Buy-and-hold beat it in every period
  (dev +4,642% vs −11.5%; val −9.4% vs −59.3%; test +92.7% vs −76.2%).
* C4 ORB: small pre-cost edge (6–23 bp) vs. ≈ 86 bp costs; tight opening-range stops make one
  round trip cost ≈ 1 R.
* C5 TJR/SMC-style: **untestable at this definition** — only 4–7 qualifying setups per year on
  BTC; 42 trades in 10 years, net negative in every period, but far too few to conclude either way.
  The model was designed by its educators for index futures (NQ/ES), not BTC.

**10. What uncertainties remain?**
Venue mismatch (Bitstamp prices, Kraken costs); bar-level fill ambiguity (5m bars, stop-first
assumption; no 1-minute intrabar resolution yet); single instrument; research sources read mostly
via search extracts; the ORB gross effect is a post-hoc observation after 33 configurations ×
3 periods (multiple testing); TJR's actual rules are discretionary and partly paywalled, so C5 is
one interpretation among many; the random-control design is only partially matched; the DSR as
implemented is uninformative; live market microstructure (spreads, queue position, partial fills)
on Kraken was never observed.

**11. What is the smallest useful prototype worth building?**
Not a trading bot. What is worth keeping is what was built: the validated data pipeline, the
conservative backtester cross-checked against an order-level simulator, the independent risk
manager and the restart-safe paper trader. The smallest *useful* next experiment is research, not
trading: (a) a **maker-only ORB variant** (limit entries) to test whether cost reduction can cross
the break-even — specified **before** looking at new data — evaluated on data **after 2026-10-15**
collected via live-feed paper trading (a genuinely fresh holdout), or (b) C5 on 1-minute NQ/ES
futures data where the method is actually used, with ≥ 500 setups.

**12. What evidence is required before considering live trading?** All of:
1. A strategy specified in advance that passes every pre-registered criterion on a **fresh**
   holdout not used in any design decision, at the cost tier the account will actually pay.
2. ≥ 300 holdout trades, bootstrap CI of Sharpe excluding zero, robustness to 1.5× costs, and a
   gross edge at least 2× the round-trip cost.
3. Kraken-native data (OHLCVT/trades) results consistent with the Bitstamp results.
4. ≥ 3 months of live-feed paper trading with zero reconciliation incidents, measured slippage
   within the modelled range, and results within the backtest's confidence band.
5. Client-side OCO tested against Kraken's validate-only mode; API key without withdrawal rights;
   a human-reviewed readiness report and explicit approval (the three-gate mechanism).

None of these conditions is currently met. **Live trading is not recommended.**

## What *was* learned that is practically useful

* For retail-sized accounts, **fees are the binding constraint** on intraday crypto strategies:
  at ≈ 0.4% taker per side, a strategy needs a gross edge of roughly 1% per round trip to break
  even — larger than any edge measured here.
* Buy-and-hold outperformed every active strategy in the development (+4,642%) and holdout
  (+92.7%) periods. In the 2022-23 bear market it lost 9.4%, less than C1–C4 but more than C5
  (−3.3%, on only 12 trades). Buy-and-hold also carried far larger drawdowns (−54% to −84%), so it
  is a benchmark, not a recommendation.
