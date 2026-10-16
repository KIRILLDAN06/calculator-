> **Provenance.** Researched on 2026-10-16 by a research sub-agent using web search; reviewed and integrated by the lead agent. Direct page fetches of most primary sites (Kraken, TradingView, YouTube, TJR, SEC, FTC) failed from this environment (DNS/proxy policy), so many facts come from search-engine extracts of the cited pages and are labelled accordingly. Treat "unverified" items as unverified.

# Trader / Educator Analysis (skeptical review)

Date accessed for all sources: **2026-10-16**. Full source log: `trader_sources.md` (same folder).

## 0. Read this first: method limits

- **No full-page reads were possible.** In this session, WebFetch failed with DNS errors (`getaddrinfo ENOTFOUND`) on every domain tried: tjrtrades.com, tradingview.com, sozai.app, youtube.com, jointjrtrades.com, snappchart.app, forex.in.rs, sec.gov and ftc.gov. The tool refused web.archive.org outright. A WebSearch restricted to reddit.com was blocked ("domains are not accessible to our user agent").
- **What the evidence is.** Everything below comes from **WebSearch result titles, URLs and the search engine's snippet/summary text**. I did not read any page in full. Treat every claim as "reported by a search snippet of URL X". Short quoted phrases are from those snippets.
- **TJR's disclosure page is unread.** I could not read `tjrtrades.com/full-disclosure` live or archived. A search turned up nothing that reproduces it, so **its contents are UNKNOWN** here.
- **No transcripts were read.** I read no original YouTube video and no transcript in full. Transcript and summary sites (sozai.app, youtubesummary.com, aibimb.com) were seen only as search snippets. These are secondary sources, and youtubesummary is AI-generated.

---

## 1. TJR (TJR Trades)

### 1.1 What he publicly teaches (concept inventory)

| Concept | What sources say | Source(s) (all snippet-level) | Confidence |
|---|---|---|---|
| Liquidity | Liquidity rests above highs and below lows. A **liquidity sweep** shows where orders *may* have filled, and a **break of structure (BOS)** confirms that they did. | sozai.app transcript of "Path to Profitability: Liquidity Explained" — https://sozai.app/transcript/path-to-profitability-liquidity-explained/ | low-med (3rd-party transcript) |
| Liquidity levels marked | **Asia and London session highs/lows** and **previous-day highs/lows**. Also "previous session highs/lows" and "high-timeframe highs/lows" as draws on liquidity. | sozai.app "TJR's Strategy Explained" — https://sozai.app/transcript/path-to-profitability-tjr-strategy/ ; youtubesummary AI summary — https://youtubesummary.com/summary/TEp3a-7GUds ; snappchart blog — https://www.snappchart.app/blog/beginner-playbook/tjr-ict-trading-strategy | low-med |
| Framework (3 steps) | (1) identify draws on liquidity, (2) confirm potential order fills, (3) target exits | youtubesummary AI summary of "Path to Profitability: TJR's Strategy Explained" — https://youtubesummary.com/summary/TEp3a-7GUds | low-med (AI summary) |
| Discretion | The summary describes the strategy as **"discretionary and adaptive"**, relying on market conditions and experience **"rather than rigid rules"**. | same | low-med; **important for testability** |
| Fair value gaps (FVG) | FVGs are mainly for **retracements**. Sweeps and BOS drive reversals and bias shifts. A TJR-linked video description says an FVG that looks "perfect" is not a valid trade by itself and should be read with order blocks, displacement and structure. | Studocu excerpt — https://www.studocu.com/en-us/document/northwest-vista-college/principles-of-microeconomics/tjr-trade-how-to-spot-order-blocks/46179545 ; YouTube snippet — https://m.youtube.com/watch?v=gwgN0Ek7GXk | low |
| Inverse FVG (iFVG) | A common description: wait for a liquidity sweep, confirm with an **iFVG**, enter on the pullback | forex.in.rs blog — https://www.forex.in.rs/tjr-trader-strategy/ (search snippet) | low |
| SMT divergence | Divergence between related indexes (e.g. **S&P 500 vs Nasdaq**, i.e. ES vs NQ) used to spot reversals. A review says the "lagging" index signals the true direction. | youtubesummary — https://youtubesummary.com/summary/TEp3a-7GUds ; premiumcourses review — https://www.premiumcourses.net/blog/tjr-blueprint-review-2026 | low |
| Timeframes | A clip summary describes "5-minute manipulation, SMT divergence, 1-minute [fair] value gap inverse and trade execution" | TikTok discover page — https://www.tiktok.com/discover/tjr-trading-strategy | low |
| Other series topics | "How To Find Daily Bias", "Time Theory Explained", "Advanced Liquidity Concepts", "Equilibrium Explained" (the last one's attribution is unclear) | Spotify listing — https://open.spotify.com/episode/3TTOg3hRU9a16uYQTOfX2k ; YouTube — https://www.youtube.com/watch?v=AGmAVyAuBE0 | low |
| Session timing | A common setup is built around the **New York open**. A community "TJR SEEK AND DESTROY" script restricts itself to **09:30–16:00** US hours. | forex.in.rs (snippet); TradingView script — https://www.tradingview.com/script/9yqF7p26-TJR-SEEK-AND-DESTROY/ | low (no primary statement of exact minutes found) |
| Stop placement | **Beyond the sweep extreme** ("a few ticks/pips beyond the wick"), or "under the sweep" for longs | forex.in.rs blog (snippet); also third-party guide text in search summaries | low |
| Targets | The liquidity on the **other side** of the range. Exits aim at liquidity areas, with **partials plus "runners"** in one third-party guide. First target is the nearest internal liquidity, second is the opposite side of the range (generic guide). | forex.in.rs (snippet); youtubesummary (snippet); aibimb.com breakdown — https://aibimb.com/videos/path-to-profitability-tjrs-strategy-explained | low |
| Risk:reward | **No specific R:R rule or per-trade risk % from TJR was found** in any reachable snippet | — | gap |

**Instruments.** One search summary said TJR-style setups trade US index futures (NQ/ES) around the NYSE open. That statement **was not attributable to a specific TJR primary source**. The SMT examples (S&P 500 vs Nasdaq) are consistent with index futures. Status: **probable but unverified**.

### 1.2 Original videos identified (titles and URLs as seen in search results)

| Title (as indexed) | URL | Verified as TJR's own channel? |
|---|---|---|
| Path to Profitability: TJR's Strategy Explained (described as the final episode of the series) | video ID `TEp3a-7GUds`, inferred from https://youtubesummary.com/summary/TEp3a-7GUds | Title contains "TJR"; channel not directly verified |
| Advanced Liquidity Concepts (Path to Profitability) | https://www.youtube.com/watch?v=AGmAVyAuBE0 | Description points to TJR's program (snippet); channel not directly verified |
| (title not shown) TJR-linked FVG video | https://m.youtube.com/watch?v=gwgN0Ek7GXk | Snippet only |

A generic search for "only trading strategy" videos returned several YouTube URLs, but none of them could be attributed to TJR, so they are **excluded**.

**Transcripts.** sozai.app hosts transcripts of the "Path to Profitability" episodes (Liquidity Explained, TJR's Strategy Explained, Equilibrium Explained) and "Teaching My Friend How To Day Trade". **None could be fetched (DNS).** Secondary.

### 1.3 Business income and performance verification

- **Free funnel.** jointjrtrades.com advertises "TJR Bootcamp – Free Trading Course": "3+ hours … valued at $997, yours for free". It also offers a free private Discord, live sessions and trade-idea sharing through the "TJR Freaks" community on Whop. Sources: https://www.jointjrtrades.com/course and https://www.jointjrtrades.com/ (search snippet; fetch failed with DNS).
- **Paid tiers (reported, unconfirmed).** "VIP ~$150/mo" and "'Blueprint' ~$4,997 (reported — requires confirmation)", from a competitor's comparison page, which is a conflict of interest: https://www.comelearnforex.com/compare/trading-course-providers/. A "TJR Blueprint Review 2026" page also exists: https://www.premiumcourses.net/blog/tjr-blueprint-review-2026.
- **Bundles and indicators.** A coupon aggregator mentions "35% off on a bundle of courses + indicators": https://couponstroller.com/store/tjrtrades/. Low quality.
- **Prop-firm affiliates and sponsorships.** Searches found **no** prop-firm affiliate code or sponsorship disclosure tied to TJR. The full-disclosure page that would most likely list these could not be read. Status: **UNKNOWN**. For context only, the prop-firm affiliate model pays influencers commissions on challenge fees: https://propfirmmap.com/glossary/affiliate-program. The Topstep–Wieland dispute illustrates influencer revenue share: https://tradeinformer.com/prop-weekly/will-patrick-wieland-have-to-pay-topstep-5m. **Neither source is evidence about TJR.**
- **Audited or broker-verified performance: NONE FOUND.** Searches surfaced only low-quality "net worth" pages, which I did not rely on. They are unreliable, and one is hosted on an unrelated `.uz` domain.

### 1.4 Specific answers requested

| Question | Best available answer | Strength |
|---|---|---|
| Sessions / times traded | **New York open** (cash open 09:30 ET). Asia and London ranges are mapped **before** NY as liquidity. Exact entry-window minutes are **not found** in TJR primary material. Generic sources call 09:30–11:00 ET the highest-volume window for index futures (https://youngmoneyinvestments.com/blog/best-time-to-trade-futures-es-nq-session-guide, https://www.edgeful.com/blog/posts/trading-sessions-explained). | weak |
| Liquidity levels marked | Previous-day high/low; Asia high/low; London high/low; "previous session" highs/lows; higher-timeframe highs/lows. Equal highs/lows appear only in a community script. | moderate (several secondary sources agree) |
| Confirmation | Sweep → **BOS** (liquidity lesson); **iFVG** on the 1-minute (blog plus clip summary); **SMT** between ES and NQ (strategy video summary). Their combination and priority are **not specified** in reachable sources. | weak-moderate |
| Stop | Beyond the sweep wick extreme, plus a small buffer | weak (blog-level) |
| Target | Opposite-side liquidity or a draw on liquidity; partials plus runner | weak |
| Rules complete & public? | **No.** It is self-described as discretionary, and parts sit behind paid tiers. | — |

---

## 2. Other public traders / educators

### 2.1 Comparison table

| Trader | Markets | Timeframes | Entry / exit (as described) | Method type | Risk rules public? | Full rules public? | Performance verifiability | Net of costs? | Losses disclosed? | Non-trading income | Deterministic-rule translatable? | Data availability |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TJR** | Likely ES/NQ index futures (unverified) | 5m/1m execution (clip summary) | Sweep → BOS / iFVG / SMT → pullback entry; target opposite liquidity | Discretionary SMC/ICT-derived | Partial (stop beyond sweep); no R or %-risk rule found | No | **None found** | Unknown | Unknown | Courses (free funnel, reported paid tiers), Discord/Whop community; prop-firm affiliates unknown | **Partially**, needs many EXPERIMENTAL ASSUMPTIONS (sec. 5) | Needs 1-min ES and NQ futures (not researched) |
| **ICT (Michael Huddleston)** | Forex, index futures (per mentorship content) | Intraday "kill zones" | FVG, order blocks, liquidity, kill zones | Discretionary | Vague | No (definitions inconsistent across sources) | **No verified record found.** Forum posts allege past blown accounts (https://forums.babypips.com/t/rrram-fx-fitness-journal/171207/108); a NexusFi post questions Robbins World Cup multi-account transparency for **2024**, not specific to ICT (https://nexusfi.com/showthread.php?p=899824) | Unknown | Anecdotal only | Mentorship / YouTube | Partially (FVG is mechanical; "liquidity" and "bias" are not) | 1-min FX/futures |
| **Ross Cameron (Warrior Trading)** | US equities day trading | Intraday | Not researched in detail this session | Discretionary momentum (not verified here) | Not verified | No | Company publishes an earnings page. A 3rd-party article reports **$18,810,638 cumulative, Jan 2017–Dec 2025, "audited by an independent CPA"** (https://www.financialtechwiz.com/post/ross-cameron-net-worth). Audible bio: results "NOT typical. Most day traders lose money." (https://www.audible.com/author/Ross-Cameron/B072B7TYHB). **Primary page not read.** | Unknown | Self-published statements reported; not read | Large education business. **FTC settlement April 2022: $3M** for consumer refunds; barred from baseless earnings claims; no admission (https://www.ftc.gov/business-guidance/blog/2022/04/ftc-bids-good-night-deceptive-day-trading-earnings-claims ; https://www.ftc.gov/node/78914 ; https://theberkshireedge.com/great-barrington-stock-trading-company-agrees-to-3-million-settlement-with-feds/) | Hard (stock selection discretionary) | Intraday small-cap data (not researched) |
| **Kevin Davey** | Futures | Various | Algorithmic systems; book on building and validating them | **Systematic** | Yes (process published in book) | Process yes; his live systems no | Contest results per author bios: **2005 2nd (+148%), 2006 1st (+107%), 2007 2nd (+112%)** in the World Cup Championship of Futures Trading, described as "real time, real money" (https://www.audible.co.uk/author/Kevin-Davey/B00J34ZNPQ ; https://wiley-vch.e-bookshelf.de/building-winning-algorithmic-trading-systems-website-2633092.html). Contest is third-party run, but **leaderboard not checked here**. | Contest = real account (net of real costs presumably; unverified) | Not researched | Books, courses | Yes, by design | Futures data |
| **Larry Connors** | US stocks / ETFs | Daily | RSI(2): long only above the 200-day MA; buy at RSI(2) < 10; exit variants (RSI(2) > 70, or close above 5-day MA) | **Systematic, published** | Reportedly argued **against** stop-losses | Yes, but **published variants differ** | Strategy is replicable; a modern Nasdaq-100 backtest found a high win rate but low total return (https://backtrex.com/en/backtests/connors-rsi-2-nasdaq-100 ; https://www.luxalgo.com/library/concept/rsi-2/) | Depends on tester | N/A (rules, not personal P&L) | Books / research products | **Yes** | Daily OHLC, widely available |
| **Mark Minervini** (US Investing Championship) | US stocks | Swing | Not researched this session | Discretionary growth/momentum | Not researched | Partially (books; not verified here) | **USIC 2021 stock division (>$1M): +334.8%**; 1997 winner (+155%), per organizer press release (https://www.businesswire.com/news/home/20220124005241/en/2021-United-States-Investing-Championship-Winners-%E2%80%94-Minervini-Smashes-Record). The contest says it is a "real money verified competition" that uses brokerage statements. A 36,000% five-year "audited" claim appears only on a blog (unconfirmed). | Real-money account | Not researched | Books, workshops | Hard | Daily stock data |

**Not covered.** Andreas Clenow: a search for *Stocks on the Move* rules returned nothing usable, so he is **not evaluated**. Laurent Bernut was **not researched** (call budget).

### 2.2 Prose notes

- **ICT/SMC as a family.** The FVG is mechanically definable as a three-candle imbalance (vendor page: https://ctrader.com/products/4891). "Liquidity" and "draw on liquidity", however, depend on which highs and lows the trader chooses. Kill-zone times **disagree across sources**. One blog gives London 02:00–05:00, New York 08:00–11:00 and Asia 19:00–23:00 New York time (https://quantamentaltrader.substack.com/p/unlocking-ict-kill-zones-the-secret).
- **Backtests of SMC/ICT.** The Reddit domain was blocked to the search tool, so **no r/algotrading or r/Daytrading threads could be retrieved**. That is a stated gap. The non-Reddit evidence found:
  - **Offbeat Forex test.** It reports an AI-assisted test of ICT concepts on EURUSD in which one version lost money (https://offbeatforex.com/is-ict-strategy-profitable/). This is vendor-blog quality.
  - **Backtrex study.** It is the marketing page of a no-code backtest tool. It claims a 2019–2024 EURUSD/XAUUSD sweep + FVG retest backtest with a 53.2% win rate and profit factor 1.68 inside kill zones, versus 47.1% and 1.21 across all sessions (https://backtrex.com/en/blog/liquidity-sweep-strategy-backtest-results). Unverified and commercially interested.
  - **Look-ahead warning.** The same Backtrex material warns that look-ahead (evaluating on the unconfirmed current candle) can inflate win rates by **15–30 percentage points**. It also recommends at least 500 trades. Both points are useful design constraints even if the vendor's own numbers are not trusted.
  - **Disclaimers from script authors.** One TradingView SMC indicator says it is "NOT a validated edge" (search snippet, https://pl.tradingview.com/scripts/ifvg/page-2/).
- **Warrior Trading / FTC.** The FTC's theory, as reported, was not that Cameron's own results were fabricated. It was that showcasing his results implied customers would achieve similar results, while the system "ultimately failed to pay off for most customers". This is a third-party characterisation from search summaries of FTC pages and a review (https://daytradingtoolkit.com/reviews/warrior-trading-review). The settlement amount is described as redress or refunds. Sources differ on labels, and I did not verify the final court entry.

---

## 3. Popularity vs claimed vs demonstrated vs independently verified

The table is **not** ranked by followers. Popularity is noted only so it is not mistaken for evidence.

| Trader | Popularity (evidence of audience only) | Claimed profitability | Demonstrated (statements shown publicly) | Independently verified |
|---|---|---|---|---|
| TJR | Large: many 3rd-party scripts, transcripts and flashcards exist | Video titles and marketing imply profitability; no figures read | **None found** | **None found** |
| ICT | Large: many derivative indicators | Yes (mentorship marketing) | None found | None found. Forum allegations of blown accounts (unverified) |
| Ross Cameron | Large | ~$18.8M cumulative (3rd-party report of the company page) | Company publishes statements (reported; not read) | Reported "independent CPA" audit (3rd-party report; **not read**). The FTC case concerned marketing of student outcomes. |
| Kevin Davey | Niche | 148/107/112% contest years | Contest placings (bio) | Contest is third-party run (leaderboard not checked here) |
| Larry Connors | Niche | Strategy statistics in books | Rules published → **replicable** | Independent backtests exist (quality varies) |
| Mark Minervini | Large | Contest returns | Contest results | Organizer says it is a real-money, broker-statement-verified contest (organizer press release) |

**Key point.** The only cases with some third-party measurement are **contest results** (Davey, Minervini) and **published replicable rules** (Connors). Neither validates the SMC/TJR model.

---

## 4. Academic and regulator evidence on day-trader profitability

- **Taiwan: Barber, Lee, Liu, Odean.**
  - *The Cross-Section of Speculator Skill: Evidence from Day Trading*, Journal of Financial Markets 18(1), 2014; Taiwan data 1992–2006. The top 500 day traders, ranked on prior-year returns, earn **49.5 bps/day before fees and 28.1 bps/day after fees** in the following year. Bottom-ranked traders lose before and after fees. Sources: https://faculty.haas.berkeley.edu/odean/papers/day%20traders/Day%20Trading%20Skill%20110523.pdf ; https://www.escholarship.org/content/qt7k75v0qx/qt7k75v0qx.pdf?t=ohrd1z
  - *Do Day Traders Rationally Learn About Their Ability?*, later *Learning, Fast or Slow* (Review of Asset Pricing Studies 2020): the aggregate performance of day traders is **negative**. Over half of day trading comes from experienced traders with a history of losses. The later abstract reports that **97% of day traders are likely to lose money in future day trading**. Sources: https://faculty.haas.berkeley.edu/odean/papers/day%20traders/day%20trading%20and%20learning%20110217.pdf ; https://ideas.repec.org/a/oup/rasset/v10y2020i1p61-93..html ; https://www.econ.puc-rio.br/uploads/adm/seminarios/Learning_fast_or_slow_180606.pdf
  - The often-quoted "**less than 1%** predictably profitable net of fees" figure **was not confirmed** in the snippets I could see. Verify it in the PDF before citing it.
- **Brazil: Chague, De-Losso, Giovannetti, "Day Trading for a Living?"** The sample is 19,646 people who first day-traded mini-Ibovespa futures in 2013–2015. Among those who persisted **more than 300 days, 97% lost money**. Only **1.1%** earned more than the minimum wage and **0.5%** more than a bank teller's starting salary (SSRN version). The authors find no evidence of learning. Caveats from CXO: the results may not generalise to other countries or assets, and the period may have been especially hard for Brazilian index futures. Sources: https://repositorio.fgv.br/items/e87d04fc-4b4c-4a56-ab5a-1c84c1afde1b/full ; https://ideas.repec.org/p/spa/wpaper/2019wpecon47.html ; https://www.cxoadvisory.com/investing-expertise/day-trading-a-bust/
- **SEC (1999).** Investor alert "Day Trading: Your Dollars at Risk", press release 99-114, 16 Sep 1999. It warns that day traders often suffer severe losses in their first months, often trade with borrowed money that magnifies losses, and should trade only money they can afford to lose. The requested URL https://www.sec.gov/newsroom/press-releases/99-114-day-trading-your-dollars-risk-investor-alert could not be fetched (DNS). A search-verified archive copy is https://www.sec.gov/news/press/pressarchive/1999/99-114.txt and the publication is at https://www.sec.gov/files/investor/pubs/daytips.htm.
- **ESMA (2018).** National regulators' analyses found **74–89% of retail CFD accounts typically lose money**, with average per-client losses of **€1,600–€29,000**. ESMA's measures, agreed 23 March 2018, include a **standardised risk warning** that states each provider's percentage of losing retail accounts. They also include leverage caps, margin close-out and negative balance protection. Sources: https://www.esma.europa.eu/node/84933 ; ESMA Q&A PDF via CONSOB https://www.consob.it/documents/1912911/1970971/esma35_43_1000.pdf/6dc9bc30-c528-09dc-9430-398c8df4c3af

**Implication for testing.** The base rate for discretionary retail intraday trading is strongly negative after costs. A TJR/SMC backtest should be judged against that base rate and against simple null models, not against marketing claims.

---

## 5. Testable operational definitions extracted (SMC/TJR-style model)

The model under test: **liquidity sweep of a prior-day / Asia / London high or low → break of structure / market structure shift → fair-value-gap retracement entry**, executed in the NY session on index futures. Times are **America/New_York**. Bars are evaluated **only after they close**, which avoids the look-ahead problem flagged in sec. 2.2. Every item labelled **EXPERIMENTAL ASSUMPTION** is a parameter to sweep or sensitivity-test, not a fact about TJR.

**D1. Instrument and data.**
- Instruments: ES and NQ front-month continuous, 1-minute bars, plus 5-minute bars built from the 1-minute bars.
- **EXPERIMENTAL ASSUMPTION:** the primary instrument is NQ (secondary ES); both are needed for SMT. The NQ/ES choice is only inferred from SMT descriptions.

**D2. Sessions.** All three are **EXPERIMENTAL ASSUMPTIONS**; sources disagree (sec. 2.2).
- Asia range = 20:00–00:00 ET. Alternative: 19:00–23:00 ET, the substack kill-zone version.
- London range = 02:00–05:00 ET. Alternative: 00:00–05:00 ET.
- NY entry window = 09:30–11:00 ET. Alternatives: 08:00–11:00 ET (kill-zone blog) and 09:30–16:00 ET (community script).

**D3. Prior-day high/low (PDH/PDL).** High and low of the previous trading day's **RTH session, 09:30–16:15 ET**. **EXPERIMENTAL ASSUMPTION**; alternative: full Globex day, 18:00–17:00 ET.

**D4. Liquidity level set L.** {PDH, PDL, Asia high, Asia low, London high, London low}, frozen at 09:30 ET.
- **EXPERIMENTAL ASSUMPTION:** exclude any level already traded through between its formation and 09:30, because it is no longer "resting" liquidity.
- Equal highs/lows are excluded in the baseline.

**D5. Liquidity sweep.**
- A *buy-side sweep* of level ℓ ∈ L occurs at bar t (1-minute bars, inside the NY window) if `high[t] ≥ ℓ + 1 tick`, and within N bars of t (t itself included) some bar **closes back below ℓ**.
- The *sell-side sweep* is the mirror image.
- **EXPERIMENTAL ASSUMPTION:** N = 3 (sweep N ∈ {1, 3, 5, 10}). The wick-through plus close-back requirement separates a sweep from a breakout. Sources say "price pushing above/below significant highs/lows" but give no close rule.
- Sweep extreme `X` = max(high) (or min(low)) from t until the BOS.

**D6. Swing points.**
- A swing high at bar j means `high[j]` > highs of the k bars on each side; swing lows are the mirror image.
- **EXPERIMENTAL ASSUMPTION:** k = 2 on 1-minute bars (sweep k ∈ {1, 2, 3}; one community script used 5-bar highs and lows). Swings are only known k bars after j (no look-ahead).

**D7. Break of structure / market structure shift (MSS).**
- After a buy-side sweep, the BOS is the first 1-minute bar whose **close** is below the most recent confirmed swing low formed **before** the sweep extreme X. The bullish case is the mirror image.
- It must occur within M bars of the sweep. **EXPERIMENTAL ASSUMPTION:** M = 30.
- Close rather than wick: **EXPERIMENTAL ASSUMPTION**.
- Optional *displacement* filter: the BOS bar's |close − open| ≥ 1.0 × ATR(14, 1-minute). **EXPERIMENTAL ASSUMPTION**; test with and without it.

**D8. Fair value gap (three-candle).** Bars i-2, i-1, i:
- Bearish FVG if `high[i] < low[i-2]`; the zone is [high[i], low[i-2]].
- Bullish FVG if `low[i] > high[i-2]`; the zone is [high[i-2], low[i]].
- It must form within the displacement leg, between X and the BOS bar (inclusive) or up to 3 bars after it.
- Minimum size ≥ 2 ticks.
- The wick-to-wick formula and the size floor are **EXPERIMENTAL ASSUMPTIONS**. Sources only say "three-candle imbalance".

**D9. Inverse FVG (iFVG) confirmation (variant B).**
- After a buy-side sweep, take a **bullish** FVG formed during the up-move into the sweep. The trigger is a 1-minute **close below its lower edge**, which "inverts" it. Entry is short on a retrace into the inverted zone.
- **EXPERIMENTAL ASSUMPTION:** the definition is inferred from blog and clip summaries. Test it as an alternative to D7 + D8.

**D10. SMT divergence filter (optional, variant C).**
- Bearish SMT: within the sweep window, NQ sweeps its level (by D5) while ES does **not** exceed its corresponding level, or vice versa.
- Per community-script wording, the "lagging" index signals direction.
- **EXPERIMENTAL ASSUMPTION:** use the same level type (e.g. London high) on both, with a ±5-bar alignment window.

**D11. Bias filter (optional).**
- **EXPERIMENTAL ASSUMPTION:** take a short only if the 09:30 open is below the prior RTH day's midpoint, and longs for the mirror condition. Baseline: no bias filter. TJR's actual daily-bias method ("How To Find Daily Bias" episode) was not accessed.

**D12. Entry.**
- Limit order at the FVG **proximal edge** (variant E1) or at its **50% midpoint, "consequent encroachment"** (variant E2). Both variants are cited in the community-script snippet.
- Valid for at most 20 bars after the FVG forms and only inside the NY window. It is cancelled if the target is hit before the fill.
- Conservative fill: the limit fills only if price trades **through** it by 1 tick.
- These details are **EXPERIMENTAL ASSUMPTIONS**.

**D13. Stop.**
- Sweep extreme X ± 2 ticks (variant S1, matching "beyond the sweep wick").
- Alternative S2: beyond the FVG's far edge.
- The buffer size is an **EXPERIMENTAL ASSUMPTION**.

**D14. Targets.**
- T1: the nearest opposite-side level in L, or the nearest opposite swing point.
- T2: fixed 2R. T3: 50% exit at 1R, then the stop moves to breakeven and the runner targets opposite-side liquidity.
- Time stop: flat at 11:00 ET (or 16:00 for the wide-window variant).
- **EXPERIMENTAL ASSUMPTIONS.** Sources give "opposite liquidity" and "partials + runners" without numbers.

**D15. Trade limits and risk.**
- At most 1 trade per day per instrument. Size is fixed at 1 contract, or risk is fixed at 0.5% of equity per trade.
- **EXPERIMENTAL ASSUMPTION:** no TJR risk-% rule was found.

**D16. Costs.**
- Round-turn commissions and fees, plus 1 tick of slippage on stop and market exits, and 0 on limit entries (only under the conservative-fill rule).
- **EXPERIMENTAL ASSUMPTION:** report gross and net results separately.

**D17. Null models (required for any claim of edge).**
- (a) Same time window, random direction, same stop and target geometry.
- (b) Sweep with no BOS/FVG requirement.
- (c) BOS + FVG with no prior sweep.
- (d) Breakout continuation instead of reversal after the sweep.

**D18. Evaluation hygiene.**
- Use walk-forward or out-of-sample splits by year. Report the number of trades, expectancy in R, profit factor, max drawdown and bootstrap confidence intervals.
- Count every parameter combination tried, to correct for multiple testing.
- Aim for at least 500 trades before drawing conclusions. This is a vendor heuristic; it is not authoritative.

---

## 6. Open questions

1. What does `tjrtrades.com/full-disclosure` actually say: hypothetical results, affiliate or prop-firm relationships, income sources? It was unreadable live and archived in this session. Try a browser or another archive.
2. Which exact minutes does TJR trade (09:30 only? 09:30–11:00? 08:30 news?), and which session boundaries does he use for Asia and London?
3. Does TJR require **all** of sweep + BOS + iFVG + SMT, or are they interchangeable confirmations? Which takes priority?
4. Does a "BOS" need a body close or just a wick? Which swing (internal vs external) counts?
5. How does he set daily bias? The "How To Find Daily Bias" episode was not accessed.
6. What are his actual stop buffers, fixed R:R minimums, and per-trade risk %?
7. Does TJR have prop-firm affiliate deals or sponsorships, and is any broker-verified or audited P&L published?
8. Verify the paid-tier prices (VIP ~$150/mo, Blueprint ~$4,997). The current source is a competitor page.
9. Retrieve Reddit r/algotrading and r/Daytrading threads on failed ICT/SMC backtests. They were blocked to this tool.
10. Confirm the "less than 1% predictably profitable" figure in the Barber et al. paper text.
11. Check the Robbins World Cup leaderboards directly for Davey (2005–2007) and for any ICT entries.
12. Read the Warrior Trading earnings page and the CPA report directly. Check the FTC complaint for the customer-outcome statistics it cites.
13. Data: what does 1-minute ES and NQ history cost and where does it come from (rolls, back-adjustment)? Not researched.
