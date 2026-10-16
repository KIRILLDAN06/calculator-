> **Provenance.** Researched on 2026-10-16 by a research sub-agent using web search; reviewed and integrated by the lead agent. Direct page fetches of most primary sites (Kraken, TradingView, YouTube, TJR, SEC, FTC) failed from this environment (DNS/proxy policy), so many facts come from search-engine extracts of the cited pages and are labelled accordingly. Treat "unverified" items as unverified.

# Methodology References (short notes)

Compiled 2026-10-16. Formulas marked "standard form" are written from the cited papers' well-known definitions; the exact equations were **not displayed** in this session's search extracts, so verify against the primary PDF before publishing.

## 1. Sharpe annualization for 24/7 crypto
- Crypto trades every calendar day, so with **daily** returns: SR_ann = SR_daily × √365 (not √252). Hourly: √(365·24) = √8760; 1-minute: √525,600. Convention, not a sourced fact — no citation retrieved in this session.
- Caveat: √q scaling assumes i.i.d. returns; serial correlation (common in intraday crypto, see strategy_catalog.md B/F) biases it. Lo (2002) "The Statistics of Sharpe Ratios" gives the correction — **citation not retrieved (UNVERIFIED)**.
- Be consistent: compute SR on the **same calendar** for strategy and benchmark; include zero-return days when flat (do not compute SR only over in-market bars).

## 2. Stationary bootstrap (Politis & Romano 1994)
- *JASA* 89(428):1303–1313 — https://gnosis.library.ucy.ac.cy/handle/7/57533. Resamples blocks of **random, geometrically distributed length** so the resampled series is stationary; preserves short-range dependence (volatility clustering) better than i.i.d. bootstrap.
- Use: CIs for Sharpe/mean return of a strategy's daily P&L; as the resampling engine for White RC / Hansen SPA. Implementation: `arch` package (https://arch.readthedocs.io/en/stable/multiple-comparison/generated/arch.bootstrap.SPA.html, which also implements SPA).

## 3. White's Reality Check (2000) and Hansen's SPA (2005)
- **White Reality Check:** tests H0 "the best of all K strategies examined has no superior performance vs benchmark", accounting for the full universe searched — description via https://nm.dev/author/kevinsun/ and https://macroforecast.readthedocs.io/en/stable/encyclopedia/l6/axes/multiple_model_test.html. Journal (Econometrica 68(5), 2000) **not confirmed by retrieved results**. Applied to technical rules by Sullivan, Timmermann & White (1999), *J. Finance* 54(5):1647–1691 — https://ideas.repec.org/p/fmg/fmgdps/dp303.html.
- **Hansen SPA:** *J. Business & Economic Statistics* 23(4):365–380 (2005); studentizes performance and uses a centred bootstrap p-value; **less sensitive to inclusion of poor/irrelevant strategies** than RC — https://macroforecast.readthedocs.io/en/stable/encyclopedia/l6/axes/multiple_model_test.html ; implementation https://arch.readthedocs.io/en/stable/multiple-comparison/generated/arch.bootstrap.SPA.html.
- Practical rule: log **every** variant tried (parameters, filters, instruments, sessions); feed all their return series into SPA, not just the winner.

## 4. Probabilistic & Deflated Sharpe Ratio (Bailey & López de Prado)
- DSR paper: https://papers.ssrn.com/abstract=2460551 — corrects for selection bias under multiple testing and non-normal returns; conditions on number of trials, cross-sectional variance of trial Sharpes, skewness and kurtosis (per extract).
- **PSR (standard form; verify):**
  PSR(SR*) = Φ( (ŜR − SR*) · √(T − 1) / √(1 − γ̂₃·ŜR + ((γ̂₄ − 1)/4)·ŜR²) )
  where ŜR = non-annualized per-period Sharpe, T = number of return observations, γ̂₃ = skewness, γ̂₄ = kurtosis (non-excess; =3 for normal), Φ = standard normal CDF.
- **DSR (standard form; verify):** DSR = PSR(SR₀) with
  SR₀ = √V[{ŜR_n}] · ( (1 − γ)·Φ⁻¹(1 − 1/N) + γ·Φ⁻¹(1 − 1/(N·e)) ),
  N = number of independent trials, V[{ŜR_n}] = variance of Sharpe ratios across trials, γ ≈ 0.5772 (Euler–Mascheroni), e = Euler's number.
- Source paper for PSR ("The Sharpe Ratio Efficient Frontier") **not retrieved (UNVERIFIED citation)**.
- **PBO** (Bailey, Borwein, López de Prado, Zhu): estimate via combinatorially symmetric cross-validation; PBO = share of CSCV splits where the in-sample-best configuration ranks below the OOS median — https://papers.ssrn.com/abstract=2326253 ; published *J. Computational Finance*, DOI 10.21314/jcf.2016.322 (https://escholarship.org/content/qt4w1110bb/qt4w1110bb.pdf).
- Multiple-testing hurdle: Harvey, Liu & Zhu suggest t ≥ ~3.0 for new findings (secondary: https://tradingstrategy.ai/docs/learn/backtesting.html) — primary not retrieved.

## 5. Walk-forward analysis
- Procedure: split history into consecutive [train | test] windows (rolling or anchored); optimize only on train; trade the frozen parameters on the next test window; concatenate test-window P&L only; report that concatenated OOS series (and run PSR/DSR/SPA on it). Add an **embargo** gap between train and test when labels/features use overlapping horizons (López de Prado purging/embargo — book citation **UNVERIFIED**).
- Pitfalls: re-using the final test period to choose among walk-forward designs re-introduces overfitting (count those as trials for DSR); window length is itself a parameter. No primary citation retrieved for walk-forward specifically.

## 6. Conservative intrabar fill rules (bar data)
When both stop-loss and take-profit lie inside one bar's [low, high], OHLC cannot reveal which hit first.
1. **Worst case (default):** assume the **stop fills first** (and at the stop price or worse). Report results under this rule.
2. **Resolve with finer data:** re-simulate that bar using 1-minute bars or trades (TradingView's "bar magnifier" does this, limited to 200,000 lower-TF bars — https://www.tradingview.com/pine-script-docs/faq/strategies/ via search extract); if still ambiguous at 1-min, apply rule 1.
3. **Do NOT rely on path heuristics** like TradingView's legacy assumption (high closer to open ⇒ open→high→low→close, else open→low→high→close — https://www.tradingview.com/pine-script-docs/v4/essential/strategies/) for headline results; report them only as a sensitivity.
4. **Gaps:** if the bar opens beyond the stop, fill at the **open** (not the stop). Stops are market orders after trigger → add slippage (≥ half-spread + impact).
5. **Limit orders:** require price to **trade through** the limit (low < buy limit / high > sell limit), not merely touch it, since queue position is unknown.
6. **No same-bar signal-and-fill:** a signal computed on bar t's close fills at bar t+1's open (TradingView default with `process_orders_on_close=false`).
7. **Zero-volume/filled candles** (e.g., ff137 Bitstamp flat candles; Kraken omitted intervals) are not tradeable: no fills on them.
8. Fees: apply taker fee for market/stop orders and maker only for resting limits that trade through; Kraken base tier currently 0.40% maker / 0.80% taker (data_sources.md §1.7).

## Sources
| URL | type | quality | claim |
|---|---|---|---|
| https://gnosis.library.ucy.ac.cy/handle/7/57533 | univ. repository | high | Politis & Romano 1994 JASA 89(428):1303–1313; geometric block lengths |
| https://arch.readthedocs.io/en/stable/multiple-comparison/generated/arch.bootstrap.SPA.html | software docs | high | SPA implementation |
| https://macroforecast.readthedocs.io/en/stable/encyclopedia/l6/axes/multiple_model_test.html | software docs | medium | Hansen SPA JBES 23(4):365–380; vs RC |
| https://nm.dev/author/kevinsun/ | blog | low-medium | White RC description |
| https://ideas.repec.org/p/fmg/fmgdps/dp303.html | IDEAS | high | STW 1999 |
| https://papers.ssrn.com/abstract=2460551 | SSRN | high | DSR |
| https://papers.ssrn.com/abstract=2326253 | SSRN | high | PBO/CSCV |
| https://escholarship.org/content/qt4w1110bb/qt4w1110bb.pdf | repository | high | PBO JCF DOI |
| https://tradingstrategy.ai/docs/learn/backtesting.html | secondary | low | HLZ t≥3 |
| https://www.tradingview.com/pine-script-docs/faq/strategies/ | official docs (search extract) | high | bar magnifier, process_orders_on_close |
| https://www.tradingview.com/pine-script-docs/v4/essential/strategies/ | official legacy docs | high | open→high→low→close heuristic |
