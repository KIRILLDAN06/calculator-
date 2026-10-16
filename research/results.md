# Results

All numbers below were produced by `scripts/run_experiments.py` (stages `dev`, `val`, `wf`,
`test`) on the validated Bitstamp BTC/USD data and are reproducible from the pinned dataset and
the commit recorded in `runs/experiments/test_lock.json` / `research/experiment_log.jsonl`.
Full generated tables (incl. break-even and regime analyses): `results_tables.md`.
Methodology, cost scenarios and acceptance criteria were **pre-registered** in
`backtest_methodology.md` (commit `953093a`) before any validation or test result existed.

**Headline: no candidate demonstrated an edge.** All five pre-registered candidates lose money
after realistic costs on the untouched 2024-2026 holdout; four fail the pre-registered criteria
and the TJR/SMC-style candidate produced too few trades (20) to evaluate. Every one of them also
lost money out of sample in the validation period and in walk-forward testing.

## 1. Holdout (test period, 2024-01-01 → 2026-10-15), evaluated once

Buy-and-hold BTC over the same period: **+92.7%**, Sharpe 0.73, max drawdown −53.8%.

| Cand. | Strategy | Trades | Net (baseline costs) | Sharpe | Max DD | Win % | Profit factor | Exp. R | Net (stress) | Net (optimistic) | Net (zero cost) | Bootstrap 90% CI (Sharpe) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | donchian_trend (1h) | 443 | −76.2% | −2.70 | −78.9% | 21 | 0.50 | −0.59 | −96.5% | −14.6% | +61.7% | [−4.09, −1.50] |
| C2 | bollinger_mr (15m) | 1067 | −99.9% | −15.2 | −99.9% | 12 | 0.05 | −1.62 | −99.9% | −95.1% | −12.9% | [−17.0, −13.4] |
| C3 | intraday_momentum (30m) | 1018 | −99.6% | −43.2 | −99.6% | 0 | 0.00 | −1.05 | −99.9% | −80.5% | −5.9% | [−46.5, −40.4] |
| C4 | orb (5m) | 726 | −97.9% | −10.5 | −97.9% | 22 | 0.26 | −1.08 | −99.9% | −61.8% | +25.4% | [−11.9, −9.3] |
| C5 | sweep_fvg (5m, TJR/SMC-style) | 20 | −5.1% | −0.95 | −6.5% | 35 | 0.44 | −0.60 | −12.1% | +1.6% | +3.0% | [−1.78, −0.04] |

Cost scenarios: baseline = Kraken tier 3 (0.22% maker / 0.38% taker) + 5 bp slippage; stress =
tier 1 (0.40% / 0.80%) + 10 bp; optimistic = 0% / 0.10% + 2 bp; zero cost = diagnostic only.
Sharpe uses daily returns × √365. Equity is $10,000, risk 0.5% per trade.

### Pre-registered acceptance criteria (all must pass)

| Cand. | ≥30 trades | net>0 & Sharpe≥0.5 | CI low>0 | DSR≥0.90 | >95% of controls | stress Sharpe>0 | val Sharpe>0 | PF≥1.10 | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| C1 | ✅ | ❌ | ❌ | ❌ | ✅ (100%) | ❌ | ❌ | ❌ | **FAILED** |
| C2 | ✅ | ❌ | ❌ | ❌ | ❌ (42%) | ❌ | ❌ | ❌ | **FAILED** |
| C3 | ✅ | ❌ | ❌ | ❌ | ❌ (57%) | ❌ | ❌ | ❌ | **FAILED** |
| C4 | ✅ | ❌ | ❌ | ❌ | ✅ (96%) | ❌ | ❌ | ❌ | **FAILED** |
| C5 | ❌ | ❌ | ❌ | ❌ | ✅ (100%) | ❌ | ❌ | ❌ | **INSUFFICIENT EVIDENCE** |

**How to read "beats controls".** The pre-registered random-entry controls fire as often as the
candidate's *signals* (not executed trades) and pay the same costs, so they lose even more (C1
controls: median −91.7%; C4: −98.5%; C5: −23.7%). Beating them shows the candidates are not
*worse* than random timing; it is not evidence of profitability. The independent audit showed the
design is only partially matched, so a **supplementary** control matched to *executed* trade count
(100 seeds, not a decision input) was added: there **C1 beats only 41% of controls** (its 100% was
an artifact of the signal-count matching), C2 0%, C3 56%, C4 97%, C5 98% (C5 controls still use
taker entries, C5 uses maker limit entries).

**DSR caveat.** The pre-registered Deflated Sharpe Ratio used the cross-trial variance of daily
Sharpe in the validation grid (0.21), which is inflated by the catastrophically negative
strategies; the resulting deflation benchmark is uninformative. A supplementary DSR with the null
variance 1/(n−1) is also 0.00 for every candidate. The verdict does not depend on either: every
candidate's test Sharpe is negative and its plain PSR (vs. 0) is ≈ 0 (C5: 0.04).

**Re-run note.** These are the results of the re-run on the audited code (commit `9e690ff`); the
first run (commit `2d24230`) gave the same verdicts and, apart from C2 trade counts (±1) and the
C3 control percentile (33% → 57%, via the corrected holding-period count), the same numbers.

Yearly holdout returns (baseline costs): C1 −30.7% / −49.8% / −31.7% (2024/25/26);
C4 −70.4% / −77.5% / −68.5%; C5 −0.9% / −1.0% / −3.1%. Losses were not concentrated in one episode.

## 2. Validation period (2022-01-01 → 2023-12-31)

Buy-and-hold: −9.4%, Sharpe 0.19, max DD −67.4%.

| Cand. | Trades | Net (baseline) | Sharpe | Net (optimistic) | Net (zero cost) | Sharpe (zero cost) |
|---|---|---|---|---|---|---|
| C1 | 284 | −59.3% | −2.31 | −7.3% | +38.2% | 1.03 |
| C2 | 1218 | −100.0% | −22.3 | −82.7% | +37.2% | 1.50 |
| C3 | 722 | −97.4% | −35.5 | −62.6% | +6.1% | 1.09 |
| C4 | 514 | −87.9% | −6.02 | **+9.3%** | +120.8% | 2.76 |
| C5 | 12 | −3.3% | −1.04 | −0.2% | +0.5% | 0.20 |

## 3. Development period (2017-01-01 → 2021-12-31, in-sample)

Buy-and-hold: +4,642%, Sharpe 1.36, max DD −83.9%.

| Cand. | Trades | Net (baseline) | Sharpe | Net (optimistic) | Net (zero cost) | Sharpe (zero cost) |
|---|---|---|---|---|---|---|
| C1 | 664 | −11.5% | −0.06 | **+178.9%** | +392.4% | 2.03 |
| C2 | 1861 | −100.0% | −12.9 | −98.3% | −35.8% | −0.76 |
| C3 | 1821 | −99.7% | −26.9 | −81.3% | +3.6% | 0.26 |
| C4 | 1285 | −99.8% | −7.31 | −64.0% | +117.5% | 1.16 |
| C5 | 10 | −2.9% | −0.72 | −0.8% | −0.2% | −0.07 |

Grid sensitivity (33 configurations, baseline costs): **every** configuration of C2, C3 and C4 lost
more than 95% in development; the best C1 configuration (entry 96 bars, stop 3 ATR) made +3.4%
(Sharpe 0.12); no C5 configuration had more than 10 trades. Full grid in `runs/experiments/dev/summary.json`.

## 4. Walk-forward (10 × 6-month OOS windows, 2019-H1 → 2023-H2, baseline costs)

Parameters re-selected on each preceding 24 months by net Sharpe (min. 20 trades).

| Cand. | OOS trades | OOS net | OOS Sharpe | OOS max DD | Bootstrap 90% CI |
|---|---|---|---|---|---|
| C1 | 491 | −45.2% | −0.81 | −48.4% | [−1.71, −0.05] |
| C2 | 764 | −98.6% | −8.88 | −98.6% | [−9.49, −8.28] |
| C3 | 916 | −97.3% | −17.8 | −97.3% | [−18.8, −16.8] |
| C4 | 1285 | −99.6% | −7.06 | −99.6% | [−8.29, −6.04] |
| C5 | 19 | −6.6% | −1.11 | −6.6% | [−1.71, −0.41] |

Re-optimisation did not rescue any candidate; selection drifted toward slower/fewer-trade variants
(C1 → 96-bar channel; C2 → z = 3, ADX < 20; C3 → mode "both"), i.e. toward paying fewer costs.

## 5. Why they fail: costs versus gross edge

Gross expectancy per trade from zero-cost runs (bp of entry notional, 95% CI), against a modelled
baseline round trip of ≈ 86 bp for taker-in/taker-out trades (2 × 0.38% + 2 × 5 bp; measured
median 86–89 bp), ≈ 70 bp for C2's maker take-profits and ≈ 44–65 bp for C5's maker limit entries:

| Cand. | Development | Validation | Test |
|---|---|---|---|
| C1 donchian | 50.3 [13.1, 87.5] | 24.5 [−18.8, 67.8] | 6.5 [−17.7, 30.7] |
| C2 bollinger | −3.6 [−7.7, 0.5] | 3.3 [−0.8, 7.3] | −1.8 [−4.9, 1.2] |
| C3 intraday momentum | 0.5 [−2.2, 3.1] | 1.0 [−1.4, 3.4] | −0.7 [−2.3, 0.9] |
| C4 ORB | 9.6 [0.4, 18.9] | 22.8 [8.4, 37.2] | 5.8 [−3.9, 15.4] |
| C5 sweep/FVG | −5.4 [−84, 73] | 13.4 [−61, 88] | 28.2 [−20, 77] |

* Intraday stops are tight (median ≈ 0.9–1.1% from entry for ORB/Bollinger), so one round trip
  costs ≈ 0.7–1.0 R before the trade starts. Even a genuine 10–20 bp edge cannot survive that.
* **C2 and C3 show no gross edge at all** (CIs straddle zero in every period).
* **C1's gross edge decayed** from 50 bp (2017-21) to 6.5 bp (2024-26) — consistent with the
  literature finding that crypto technical-rule profits fade out of sample (Hudson & Urquhart).
* **C4 (ORB around the US cash open) is the only candidate with a positive gross point estimate in
  all three periods**, and its validation CI excludes zero. This was *not* a pre-registered decision
  criterion and was observed after 33 configurations × 3 periods, so it is a hypothesis for future
  work, not a finding. Its size (6–23 bp) is far below retail costs and marginal even at
  institutional costs (optimistic scenario: −64%, +9%, −62%).
* **C5 (TJR/SMC-style)** fired 10–20 times per period under the pre-registered definition (≈ 4–7
  trades a year): no conclusion about its edge is possible from this sample in either direction.

## 6. Other robustness views (test period)

* **Regimes** (`results_tables.md`): trend regime = BTC above/below its 200-day SMA at the prior
  close; volatility regime = 20-day realised volatility above/below the 2017-21 median. At baseline
  costs every candidate lost on average in every regime; gross, C1 earned only in low-volatility
  regimes (+6.8 bp/day) and lost in high volatility (−12.1 bp/day); C4 was slightly positive in
  all four regimes (gross).
* **Direction:** losses are spread across long and short trades for every candidate (e.g. C4:
  371 long / 355 short trades, −$4,813 / −$4,978).
* **Instruments:** only BTC/USD was tested (no other instrument's data was reachable) — results
  may not transfer to ETH, altcoins or equities, in either direction.

## 7. Paper trading (replay) and execution consistency

* Paper trader vs. backtest on real data, trade-for-trade: identical entries, exits, prices and
  P&L for C1 (Mar–May 2021, 39 trades), C2 (May 2021, 38), C3 (Mar–Jun 2021, 90; one exit price
  differing by $0.0001 from floating-point order of operations), C4 (May 2021, 20) — see `test_report.md`.
* Layer-G replay (2026-08-01 → 2026-10-15, C1 with paper risk settings): 24 trades, net +$400.77
  (+4.0%), driven by a single +$1,165.62 trend trade; 18 of 24 trades lost money.
  **This is not evidence of profitability** (24 trades, one outlier); it validates mechanics only.
* Live-feed paper trading could not be run (exchange APIs blocked).

## 8. Failed tests and negative results (all reported)

Every experiment run is logged (`experiment_log.jsonl`, `experiment_log.md`). Nothing was
discarded or re-run with altered parameters after seeing validation or test results.
