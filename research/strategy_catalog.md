> **Provenance.** Researched on 2026-10-16 by a research sub-agent using web search; reviewed and integrated by the lead agent. Direct page fetches of most primary sites (Kraken, TradingView, YouTube, TJR, SEC, FTC) failed from this environment (DNS/proxy policy), so many facts come from search-engine extracts of the cited pages and are labelled accordingly. Treat "unverified" items as unverified.

# Strategy Catalog — taxonomy, hypotheses, failure modes, evidence

Compiled 2026-10-16. Citation policy: every literature claim links to a URL actually returned in this session's searches. Where a requested paper could not be located, it is marked **UNVERIFIED (not retrieved)** — do not cite it from this file without checking. Most evidence here came from search-engine extracts of abstracts/repository pages, not full-text reads.

## Universal edge test (applies to every entry)
An edge is established only if **all** hold: (1) a pre-registered rule with parameters fixed before the test window; (2) positive net-of-cost returns using realistic fees (Kraken base tier 0.40%/0.80%, see data_sources.md §1.7), spread and slippage; (3) out-of-sample / walk-forward performance, not just in-sample; (4) significance after multiple-testing correction — deflated Sharpe ratio / PBO (https://papers.ssrn.com/abstract=2460551, https://papers.ssrn.com/abstract=2326253), White Reality Check / Hansen SPA (methodology_refs.md); (5) robustness to parameter perturbation, sub-periods, and venues; (6) enough trades (hundreds+) that bootstrap CIs exclude zero.

---

## A. Price action / market structure
| Strategy | Hypothesis | May work when | Why it fails | Data needs |
|---|---|---|---|---|
| Opening-range breakout (ORB) | Early-session range break reveals informed/directional flow that persists | Session-anchored assets (US stocks/ETFs) with real "open"; news-driven "stocks in play"; high RVOL days | Crypto has no true open (24/7) — "open" must be defined (e.g. 00:00 UTC or 13:30 UTC US cash open); false breakouts in chop; costs on small ranges | 1-min bars (stocks: consolidated SIP, not IEX-only); for stocks, survivorship-free universe |
| Breakout–retest | Broken level flips support/resistance; retest gives better entry | Trending regimes | Level definition is discretionary → hard to code without look-ahead; many degrees of freedom | 1–15 min bars |
| Liquidity-sweep reversal | Stops above/below obvious highs/lows get run, then price reverts | Thin books, around session opens | Sweeps that continue (true breakouts) are indistinguishable ex-ante; needs intrabar sequencing | 1-min bars minimum; ideally trades/L2 to see stop cascades |
| Fair value gap (FVG, ICT/SMC) | 3-bar imbalance gaps get "filled"/act as magnets | — | Definition fluid; gaps on 1-min crypto are tiny relative to fees | 1-min bars |
| VWAP (trend/hold above-below) | Institutions benchmark to VWAP; price relative to VWAP signals pressure | Equity sessions with institutional execution | Crypto VWAP anchor is arbitrary (24/7) | Volume-weighted bars or trades |
| Previous-day high/low | Prior-day extremes are reference levels for breakout/fade | Liquid markets with day boundaries | Same as above; crypto "day" boundary choice changes results (multiple testing) | 1-min + daily |

**Evidence:**
- **ORB on QQQ** — Zarattini & Aziz, "Can Day Trading Really Be Profitable?" (SSRN, 2023): 5-min ORB on QQQ 2016–2023; with TQQQ reports 1,484% cumulative vs 169% buy-and-hold QQQ and ~33% annualized alpha net of commissions — https://papers.ssrn.com/abstract=4416622. Caveat: leverage-driven headline; single instrument; authors are practitioner-affiliated (Concretum).
- **ORB on "stocks in play"** — Zarattini, Barbon & Aziz, "A Profitable Day Trading Strategy For The U.S. Equity Market" (SSRN, 2024): 5-min ORB on >7,000 US stocks 2016–2023; stocks in play (unusual activity/news) significantly outperform; compares 5/15/30/60-min ranges — https://concretumgroup.com/a-profitable-day-trading-strategy-for-the-u-s-equity-market/ , https://www.alexandria.unisg.ch/entities/publication/ab50f49b-4d5c-4aa8-aaa1-af7a4c131008. Screen (open > $5, 14-day ADV ≥ 1M sh, ATR > $0.50) per third-party summary https://www.cxoadvisory.com/individual-investing/intraday-trading-of-overactive-stocks-via-opening-range-breakout/. Independent QuantConnect replication reports Sharpe ~2.4 but omits ATR filter — https://www.quantconnect.com/forum/discussion/18444/opening-range-breakout-for-stocks-in-play/.
- **FVG:** **No rigorous public (peer-reviewed or independently replicated) backtest of ICT/SMC fair value gaps was found.** Only a self-published TradingView indicator comparing FVG zones to placebo zones, whose author warns results are inconclusive below ~1,000 resolved zones and that conclusions flip across periods — https://in.tradingview.com/scripts/backtest/. Treat FVG as an untested hypothesis; test against a placebo (random-gap) control.
- Liquidity sweep, breakout-retest, VWAP, PDH/PDL: **no rigorous published evidence retrieved in this session.**

## B. Momentum / trend
| Strategy | Hypothesis | May work when | Why it fails | Data |
|---|---|---|---|---|
| MA crossover, MACD | Trends persist (underreaction, herding) | Strong trending regimes (crypto bull/bear runs) | Whipsaws in ranges; lag; heavily data-mined | Daily/hourly bars |
| RSI (as momentum or overbought) | Overextension → continuation or reversal (ambiguous!) | Depends on regime | Sign ambiguity invites overfitting | Bars |
| ADX filter | Trade trend rules only when trend strength high | Reduces whipsaw | Adds parameters | Bars |
| Time-series momentum (TSMOM) | Own past return predicts future return | Diversified futures; crypto at weekly horizons | Momentum crashes, regime shifts | Daily |
| Donchian breakout | N-day high/low breakout captures trends (turtle-style) | Trending, diversified portfolio | Long losing streaks; single-asset results fragile | Daily |
| Intraday momentum (first period → last period) | Early-day return predicts end-of-day return | Equity indices, high-vol days | Small per-trade edge vs costs | Intraday bars |

**Evidence:**
- **Crypto TSMOM:** Liu & Tsyvinski, "Risks and Returns of Cryptocurrency", *Review of Financial Studies* 34(6):2689–2727 (2021): strong time-series momentum; investor-attention proxies forecast returns; little exposure to standard stock/macro factors — https://papers.ssrn.com/abstract=3226806 ; NBER WP 24877 https://www.nber.org/system/files/working_papers/w24877/w24877.pdf.
- **Technical rules in crypto:** Hudson & Urquhart, "Technical trading and cryptocurrencies", *Annals of Operations Research* 297:191–220 (2021; online 2019): ~15,000 rules across five classes show in-sample predictability, but **no out-of-sample predictability for Bitcoin** — https://hull-repository.worktribe.com/output/2328042.
- **Market intraday momentum:** Gao, Han, Li & Zhou, "Market intraday momentum", *Journal of Financial Economics* 129(2):394–414 (2018) — bibliographic details seen only in a reference list at https://ideas.repec.org:443/a/eee/ecofin/v62y2022ics1062940822000833.html; **abstract/findings not retrieved in this session (UNVERIFIED content)**.
- **Bitcoin intraday TSMOM:** *Financial Review* (2022) "Bitcoin intraday time series momentum" — momentum driven by liquidity provision rather than late-informed trading — https://research.birmingham.ac.uk/en/publications/bitcoin-intraday-time-series-momentum/.
- **Moskowitz, Ooi & Pedersen, "Time series momentum" (JFE 2012):** **UNVERIFIED (not retrieved)**.

## C. Mean reversion
| Strategy | Hypothesis | May work when | Why it fails | Data |
|---|---|---|---|---|
| Bollinger band fade | Moves beyond k·σ revert | Range-bound, liquid markets; short horizons | Trend days / vol expansion → large losses; fat tails | Bars |
| Z-score of price vs MA | Same, parametric | Stationary spreads | Price is non-stationary | Bars |
| VWAP reversion | Price reverts to VWAP intraday | Equity sessions with institutional anchoring | Crypto VWAP anchor arbitrary | Trades/vol bars |
| Pairs / cointegration (e.g. BTC–ETH, same coin across venues) | Spread is stationary → mean-reverts | Stable economic link | Cointegration breaks; borrow/short costs; two-leg fees | Synchronized bars both legs |

**Evidence:** Cross-sectional daily **reversal** in >3,600 coins (low prior-day return outperforms), attributed to illiquidity, while the largest coins show daily momentum instead — https://earsiv.medeniyet.edu.tr/items/23a96c9f-3952-4bdf-aec5-abafb3aaab70. Implication: reversal profits concentrate where costs are highest. Specific evidence on BTC Bollinger/z-score/pairs: **not retrieved in this session.**

## D. Volume / order flow
| Strategy | Hypothesis | Data required |
|---|---|---|
| Order-book imbalance (OBI / OFI) | Imbalance between best bid/ask supply-demand predicts next price change | **L2 / L1 quote updates (tick)** — Kraken WS book recorded yourself, or Tardis/CoinAPI/Kaiko |
| Trade-flow imbalance (signed volume) | Aggressive buy vs sell volume predicts short-term drift | **Trade ticks with side** (Kraken Trades REST/WS; Binance taker-buy volume as bar-level proxy) |
| Relative volume (RVOL) | Unusual volume flags information arrival ("in play") | Bars with volume suffice; needs time-of-day-normalized baseline |

- **Cont, Kukanov & Stoikov**, "The Price Impact of Order Book Events", *J. Financial Econometrics* 12(1):47–88 (2014): short-horizon price changes driven mainly by OFI at best bid/ask (NYSE TAQ, 50 stocks); linear relation with slope inversely proportional to depth; robust across stocks/time scales — https://arxiv.org/abs/1011.6402 , https://ideas.repec.org/a/oup/jfinec/v12y2014i1p47-88..html.
- **Why it fails for retail:** OFI is largely *contemporaneous*; predictive horizon is seconds; edge is smaller than taker fees (0.80% base tier) and needs maker execution + queue modelling. Bar data cannot test it.

## E. Volatility / regime
- **ATR-based stops/position sizing; volatility expansion breakouts; time-of-day filters; regime switching (HMM/vol-threshold).** Hypothesis: returns/risk are state-dependent; trade only in favourable states. Fails because regime labels are fit in-sample (look-ahead), states are unstable, and filters multiply the number of tests. Data: bars suffice; time-of-day work needs long intraday history (e.g. ff137 Bitstamp 1-min, 2012→).
- Evidence: Bitcoin **intraday return curves** show time-of-day predictability exploitable by intraday strategies (Bouri et al., *Int. Review of Financial Analysis* 2021) — https://ideas.repec.org/a/eee/finana/v76y2021ics1057521921001228.html , https://research.tees.ac.uk/en/publications/on-the-intraday-return-curves-of-bitcoin-predictability-and-tradi/ , PDF https://repository.essex.ac.uk/30487/1/Bitcoin_Functional%20V8%20Clean.pdf. Net-of-cost robustness: **not verified**.

## F. Crypto-specific
| Strategy | Type | Hypothesis | Data | Notes |
|---|---|---|---|---|
| Intraday momentum/reversal in BTC/ETH | Directional | Early-window return predicts later window | 1-min bars | See evidence below |
| Funding-rate signal (fade extreme funding) | Directional | Crowded perp positioning mean-reverts | Kraken Futures funding history (§1.5) | Evidence: not retrieved |
| Cash-and-carry / basis | **Arbitrage-like (market-neutral)** | Long spot + short perp/future earns funding/basis | Spot + perp prices + funding | Risks: exchange/counterparty, margin calls, funding flips; not "free" |
| Weekend / day-of-week | Directional | Lower weekend liquidity → different drift/vol | Daily/hourly | Evidence: not retrieved |
| Cross-exchange price gaps | **Arbitrage** if simultaneous buy/sell on both venues with pre-funded inventory; **directional** if using one venue's move to predict the other (lead-lag) | Synchronized tick data both venues | Withdrawal delays, fees on both legs, latency |
| BTC around US equity open (13:30 UTC) | Directional | Equity-session flow spills into BTC | 1-min bars | **No published evidence retrieved in this session (UNVERIFIED)** |

**Evidence:**
- "Intraday return predictability in the cryptocurrency markets: Momentum, reversal, or both", *North American Journal of Economics and Finance* 62 (2022), DOI 10.1016/j.najef.2022.101733 — https://ideas.repec.org:443/a/eee/ecofin/v62y2022ics1062940822000833.html. **Author list (Wen, Bouri, Xu, Zhao) NOT confirmed** in the retrieved record; findings not read.
- Bitcoin intraday TSMOM (Financial Review 2022) and Bitcoin intraday return curves (IRFA 2021): see B and E above.
- **Eross, McGroarty, Urquhart & Wolfe, "The intraday dynamics of bitcoin": UNVERIFIED (not retrieved).**
- Hudson & Urquhart: no out-of-sample Bitcoin predictability for classic technical rules (B).

## G. Stocks
- **ORB on stocks in play** (strongest evidence, see A). **Gap-and-go**: premarket gap + volume → continuation; no rigorous public evidence retrieved.
- **Low-float / penny stocks — structural risks (general market-structure knowledge; specific statistics not retrieved, so no numbers given):** trading halts (LULD/news halts) make stops unfillable and gap through; dilution via shelf offerings/ATMs/warrants; short borrow scarce/expensive (hard-to-borrow, locates, recalls); wide and unstable spreads and thin L2 make bar-based fills fictitious; pump-and-dump / promotion manipulation; survivorship bias is extreme (many delist) → need Norgate/CRSP-style delisted data (data_sources.md §10). Free IEX-only bars (Alpaca Basic) misstate volume/highs/lows — https://docs.alpaca.markets/docs/about-market-data-api.

## H. Advanced
- **ML with purged/embargoed CV and meta-labeling (López de Prado, *Advances in Financial Machine Learning*):** purging removes training labels overlapping test periods; embargo adds a gap; meta-labeling uses a secondary model to size/filter a primary signal. **Book citation not retrieved in this session (UNVERIFIED reference)**; related verified work by the same author: deflated Sharpe ratio https://papers.ssrn.com/abstract=2460551 and PBO via combinatorially symmetric cross-validation https://papers.ssrn.com/abstract=2326253.
- **Reinforcement learning caveats:** non-stationary reward, tiny signal-to-noise, simulator ≠ market (no impact/queue), extreme overfitting capacity — evaluate with the same DSR/PBO machinery. No specific citation retrieved.

## Overfitting / multiple testing literature (applies to all)
- **Sullivan, Timmermann & White (1999)**, "Data-snooping, technical trading rule performance, and the bootstrap", *Journal of Finance* 54(5):1647–1691: applies White's Reality Check to an expanded universe of Brock-Lakonishok-LeBaron rules on 100 years of DJIA — https://ideas.repec.org/p/fmg/fmgdps/dp303.html , https://researchonline.lse.ac.uk/id/eprint/119144. Secondary accounts differ on whether the best rule survives full-sample (nuance noted in search extract); later sub-periods show no significant profitability (secondary: https://c.mql5.com/forextsd/forum/211/Re-Examining%20the%20Profitability%20of%20Technical%20Analysis%20with%20Whitets%20Reality%20Check%20and%20Hansen9s%20SPA%20Tes.pdf).
- **Bailey & López de Prado — Deflated Sharpe Ratio** (*J. Portfolio Management* 2014): corrects SR for selection bias under multiple testing and non-normal returns — https://papers.ssrn.com/abstract=2460551.
- **Bailey, Borwein, López de Prado & Zhu — Probability of Backtest Overfitting** (*J. Computational Finance*, DOI 10.21314/jcf.2016.322): PBO via CSCV = fraction of splits where the in-sample best is below median OOS — https://papers.ssrn.com/abstract=2326253 , https://escholarship.org/content/qt4w1110bb/qt4w1110bb.pdf.
- **Harvey, Liu & Zhu (2016) "...and the Cross-Section of Expected Returns"** (*Journal of Finance*): new factors should clear t ≈ 3.0 rather than 2.0 — **primary not retrieved; per secondary sources** https://tradingstrategy.ai/docs/learn/backtesting.html , https://fffinstill.com/learning/concepts/backtesting-methodology.
- **Park & Irwin (2007) survey of technical-analysis profitability: UNVERIFIED (not retrieved).**

## Sources
| URL | type | quality | claim |
|---|---|---|---|
| https://papers.ssrn.com/abstract=4416622 | SSRN working paper | medium (practitioner, unrefereed) | QQQ ORB 2016–23, TQQQ 1,484% vs 169%, alpha 33% |
| https://concretumgroup.com/a-profitable-day-trading-strategy-for-the-u-s-equity-market/ | author site | medium | stocks-in-play 5-min ORB, >7,000 stocks |
| https://www.alexandria.unisg.ch/entities/publication/ab50f49b-4d5c-4aa8-aaa1-af7a4c131008 | univ. repository | medium-high | same paper record |
| https://www.cxoadvisory.com/individual-investing/intraday-trading-of-overactive-stocks-via-opening-range-breakout/ | third-party summary | medium | stocks-in-play screen |
| https://www.quantconnect.com/forum/discussion/18444/opening-range-breakout-for-stocks-in-play/ | replication forum | low-medium | Sharpe ~2.4, no ATR filter |
| https://in.tradingview.com/scripts/backtest/ | self-published script | low | FVG placebo test, inconclusive <1,000 zones |
| https://papers.ssrn.com/abstract=3226806 | RFS paper (SSRN) | high | crypto TSMOM, attention |
| https://www.nber.org/system/files/working_papers/w24877/w24877.pdf | NBER WP | high | same |
| https://hull-repository.worktribe.com/output/2328042 | repository (Annals OR) | high | ~15k rules, no OOS BTC predictability |
| https://ideas.repec.org:443/a/eee/ecofin/v62y2022ics1062940822000833.html | IDEAS record | medium | NAJEF 2022 crypto intraday paper; Gao et al. JFE 2018 ref |
| https://research.birmingham.ac.uk/en/publications/bitcoin-intraday-time-series-momentum/ | univ. repository | high | BTC intraday TSMOM via liquidity provision |
| https://ideas.repec.org/a/eee/finana/v76y2021ics1057521921001228.html | IDEAS record | high | BTC intraday return curves, IRFA 2021 |
| https://research.tees.ac.uk/en/publications/on-the-intraday-return-curves-of-bitcoin-predictability-and-tradi/ | univ. repository | high | same |
| https://earsiv.medeniyet.edu.tr/items/23a96c9f-3952-4bdf-aec5-abafb3aaab70 | univ. repository | medium | daily reversal across 3,600 coins; large coins momentum |
| https://arxiv.org/abs/1011.6402 | arXiv / JFEc | high | OFI drives short-horizon price changes |
| https://ideas.repec.org/p/fmg/fmgdps/dp303.html | IDEAS (FMG DP) | high | STW 1999 Reality Check on technical rules |
| https://researchonline.lse.ac.uk/id/eprint/119144 | LSE repository | high | same |
| https://papers.ssrn.com/abstract=2460551 | SSRN (JPM) | high | Deflated Sharpe Ratio |
| https://papers.ssrn.com/abstract=2326253 | SSRN (JCF) | high | PBO / CSCV |
| https://escholarship.org/content/qt4w1110bb/qt4w1110bb.pdf | repository | high | PBO published DOI |
| https://tradingstrategy.ai/docs/learn/backtesting.html | secondary | low | HLZ t>3 (secondary) |
| https://docs.alpaca.markets/docs/about-market-data-api | official docs | high | IEX ~2.5% of volume |
