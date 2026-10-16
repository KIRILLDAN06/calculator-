# Backtest Methodology (pre-registered)

**Status: PRE-REGISTERED on 2026-10-16, before any validation-period or test-period result
was computed.** The git commit that introduces this file is the timestamp. The only results seen
before writing it were development-period smoke tests (2021) used to debug the code.
Any later deviation is listed in the [Deviations log](#deviations-log) with its reason.

## 1. Data

| Item | Value |
|---|---|
| Instrument | BTC/USD spot, Bitstamp (the only bulk intraday source reachable from this environment; Kraken/Binance/Coinbase APIs were blocked by network policy — see `data_sources.md`) |
| Raw source | `github.com/ff137/bitstamp-btcusd-minute-data` pinned at commit `b1d538ca`, SHA-256 recorded in `data/raw/manifest.json` |
| Granularity | 1-minute OHLCV, resampled to 5m / 15m / 30m / 1h complete bars (labelled by open time, UTC) |
| Coverage used | 2016-01-01 → 2026-10-15 (2016 = indicator warm-up only) |
| Validation result | 5,675,144 minutes; 0 gaps, 0 duplicates, 0 OHLC violations; 325,863 zero-volume (flat-filled) minutes; 15 zero-volume runs ≥ 60 min (possible outages) |

**Venue mismatch (known limitation).** Fees and order rules are modelled on Kraken; prices
come from Bitstamp. BTC/USD on the two venues is closely arbitraged but not identical, and
liquidity differs. Results are a model of "a Kraken-like venue trading Bitstamp prices".

## 2. Chronological splits (no shuffling)

| Segment | Period | Use |
|---|---|---|
| Warm-up | 2016-01-01 → 2016-12-31 | indicator burn-in only, never scored |
| Development (in-sample) | 2017-01-01 → 2021-12-31 | debugging, baseline behaviour, parameter sensitivity |
| Validation | 2022-01-01 → 2023-12-31 | first out-of-sample check of pre-registered baselines |
| **Test (untouched holdout)** | **2024-01-01 → 2026-10-15** | evaluated **once** per pre-registered configuration |

**Walk-forward (2017-2023 only, never touches the test period):** rolling 24-month training
window, 6-month out-of-sample step, from train 2017-01..2018-12 / test 2019-H1 through
train 2021-07..2023-06 / test 2023-H2 (10 OOS windows). On each training window the grid
configuration with the highest net daily Sharpe (min. 20 trades) is selected and applied to the
next 6 months. The concatenated OOS segments form the walk-forward result.

The test-period runner (`scripts/run_experiments.py --stage test`) writes a lock file
recording the exact configurations; re-running with different parameters is refused unless
`--allow-rerun` is passed, and any such re-run must be logged here as a deviation.

## 3. Candidates (pre-registered baselines)

All parameter values are **experimental assumptions**, chosen before testing; see
`candidate_specifications.md` for exact rules.

| Id | Strategy | TF | Baseline parameters | Grid (sensitivity / walk-forward) | Grid size |
|---|---|---|---|---|---|
| C1 | `donchian_trend` (trend baseline) | 1h | entry_n 48, exit_n 24, ATR 24, stop 2.0 ATR | entry_n {24, 48, 96} × stop_atr {2, 3} | 6 |
| C2 | `bollinger_mr` (mean reversion) | 15m | n 20, z 2.5, ADX<25, stop 2 ATR, hold 16 | z {2.0, 2.5, 3.0} × adx_max {20, 25, 100=off} | 9 |
| C3 | `intraday_momentum` (first→last half hour) | 30m | mode first | mode {first, both} | 2 |
| C4 | `orb` (NY opening-range breakout) | 5m | OR 15 min, stop opposite side, exit 16:00 ET | or_minutes {15, 30} × stop_mode {opposite, atr} × rr {none, 2} | 8 |
| C5 | `sweep_fvg` (TJR/SMC-style) | 5m | levels PDH/PDL+Asia+London, window 09:30-11:30, reclaim 3, MSS 12, edge entry, 2R, flat 16:00 | entry {edge, mid} × rr {2, 3} × window_end {11:00, 11:30} | 8 |

**Total configurations = 33** — this is the trial count `N` used for the Deflated Sharpe Ratio.

**Benchmarks and controls** (not counted as trials):

* **Buy-and-hold** BTC (one taker entry/exit, same slippage).
* **No-trade** baseline (0% return).
* **Simple trend baseline** = C1.
* **Random-entry negative control** per candidate: 200 seeds; entry probability set so the
  expected number of entries equals the candidate's signal count in the same period; same
  timeframe; stop 2×ATR(14), target 2R, max hold = candidate's median holding period;
  session candidates (C4, C5) confined to the same NY window and flat at 16:00 ET.

## 4. Execution and cost model

Engine rules (`src/qtrade/backtest/engine.py`): signal on bar close → act at next bar; market
orders at next open ± slippage (taker); limit orders fill only when traded **through** (maker,
no slippage); stops fill at min(open, stop) (gaps get the worse price) ± slippage; stop assumed
first when stop and target share a bar; target ignored on a limit-entry fill bar; shorts pay
margin opening fee + pro-rata rollover; incomplete or no-trade bars cannot trigger entries;
position size ≤ 5% of the signal bar's traded notional; quantities floored to 8 decimals,
min 0.0001 BTC; limit prices rounded conservatively to 0.1 USD.

| Scenario | Maker | Taker | Slippage/side | Rationale |
|---|---|---|---|---|
| **Baseline** | 0.22% | 0.38% | 5 bp | Kraken Pro tier 3 ($10K+ 30-day volume) of the schedule effective 2026-07-09 |
| Stress | 0.40% | 0.80% | 10 bp | Kraken Pro tier 1 (new account) + worse execution |
| Optimistic | 0.00% | 0.10% | 2 bp | ≈ $10M+/month tier; tests whether *any* edge exists for the cheapest participant |
| Gross | 0 | 0 | 0 | diagnostic only — never used for a decision |

Shorts: 0.02% opening fee + 0.02% per 4 h rollover on notional (Kraken's published "up to" values).

## 5. Risk settings (identical for every candidate)

Initial equity $10,000; risk 0.5% of equity per trade (size = risk / stop distance); max
leverage 1.0; one position at a time; max 4 entries per UTC day; daily loss limit 3% (no new
entries that day). For research comparability the drawdown kill switch and loss-streak
cooldown are **disabled** in experiment runs (drawdown is reported instead); paper trading
uses them (`configs/paper.yaml`).

## 6. Metrics (definitions)

* **Net return** = final equity / initial − 1, after all costs. **Gross return** = net + total costs / initial.
* **Total costs** = fees + short financing + slippage (difference between pre-slippage reference and fill).
* **Win rate** = share of trades with net P&L > 0. **Avg win / avg loss** in USD, net.
* **Profit factor** = Σ net wins / |Σ net losses|. **Expectancy** = mean net P&L per trade (USD and R).
* **R multiple** = trade net P&L / initial risk (qty × |entry fill − initial stop|).
* **Max drawdown** = min(equity / running peak − 1) on bar-close marked equity; **duration** = longest peak-to-recovery span in days.
* **Sharpe** = mean / stdev of daily (UTC) equity returns × √365 (24/7 market). **Sortino** uses downside deviation √mean(min(r,0)²).
* **Exposure** = share of bars with an open position; **turnover** = traded notional / mean equity / year; **avg holding time** in hours.
* Breakdowns by year, month, direction.

## 7. Statistical evaluation

* **Stationary bootstrap** (Politis & Romano 1994) of daily returns, mean block 10 days,
  2,000 resamples → 90% CI for annualised Sharpe and a one-sided p-value (demeaned null).
* **Probabilistic / Deflated Sharpe Ratio** (Bailey & López de Prado) with N = 33 trials.
* **Random-entry control percentile** of the candidate's net return.
* All results — failures included — are reported in `results.md`.

## 8. Acceptance criteria (decided now, applied to the test period)

A candidate is a **"candidate for further evaluation (paper trading)"** only if **all** hold for the
pre-registered baseline configuration on the **test period at baseline costs**:

1. ≥ 30 trades (otherwise: "insufficient evidence", not "pass");
2. net return > 0 and net Sharpe ≥ 0.5;
3. bootstrap 90% CI lower bound of Sharpe > 0;
4. Deflated Sharpe Ratio ≥ 0.90 (N = 33);
5. net return above the 95th percentile of its random-entry control distribution;
6. net Sharpe > 0 under the **stress** cost scenario;
7. net Sharpe > 0 on the validation period as well (consistency);
8. profit factor ≥ 1.10.

Software tests passing has no bearing on these criteria. If no candidate passes, the
conclusion is that no edge was demonstrated, and that will be reported as such.

## Deviations log

| Date | Change | Reason | Seen test results before change? |
|---|---|---|---|
| — | none yet | — | — |
