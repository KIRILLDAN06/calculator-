# Source Registry

All sources consulted for this project, with access date, type, evidence quality and the claim each supports.
Access date for every web source: **2026-10-16**. Evidence quality: *high* = official/primary or peer-reviewed;
*medium* = reputable secondary; *low* = blogs, marketing, AI summaries, forums.

**Access limitation.** Most primary pages could not be fetched in full from this environment (DNS/proxy
policy); claims marked "search extract" or "snippet" were read from search-engine extracts of the cited URL.

## 1. Market data actually used

| Source | Type | Quality | Use / claim | Accessed |
|---|---|---|---|---|
| https://github.com/ff137/bitstamp-btcusd-minute-data (commit b1d538ca) | dataset (primary exchange data via Kaggle + Bitstamp API) | high (validated here) | all backtests; CC BY-SA 4.0 (history) / CC BY 4.0 (updates) | yes — downloaded, SHA-256 verified |
| https://www.kaggle.com/datasets/mczielinski/bitcoin-historical-data (v706) | upstream of the history file | medium | attribution: "Zielak (mczielinski), Bitcoin Historical Data, Kaggle" | no (cited via dataset manifest) |

## 2. Trader / educator investigation

**Access note (important):** In this session, WebFetch failed with DNS errors (`getaddrinfo ENOTFOUND`) for EVERY domain tried: tjrtrades.com, tradingview.com, sozai.app, youtube.com, jointjrtrades.com, snappchart.app, forex.in.rs, sec.gov and ftc.gov. The tool refused web.archive.org outright. WebSearch restricted to reddit.com returned an error ("domains are not accessible to our user agent").

**What "Accessed?" means:**
- `failed` = the URL was attempted with WebFetch and failed.
- `failed (search snippet only)` = the URL was not attempted. It appeared in WebSearch results, and the claim rests on the search engine's snippet or summary, not on a full read. No page was read in full.

The evidence-quality column already accounts for this.

| URL | Date accessed | Source type | Evidence quality | Claim it supports | Accessed? |
|---|---|---|---|---|---|
| https://www.tjrtrades.com/full-disclosure | 2026-10-16 | primary | n/a | TJR self-disclosure page (contents unknown) | failed (DNS, earlier attempt) |
| https://tjrtrades.com/full-disclosure | 2026-10-16 | primary | n/a | same | failed (DNS ENOTFOUND) |
| https://web.archive.org/web/2025/https://www.tjrtrades.com/full-disclosure | 2026-10-16 | primary (archived) | n/a | same | failed (tool refuses web.archive.org) |
| https://www.jointjrtrades.com/ | 2026-10-16 | primary | med (snippet) | TJR Freaks community on Whop: free Bootcamp, private Discord, live sessions | failed (fetch DNS); search snippet only |
| https://www.jointjrtrades.com/course | 2026-10-16 | primary | med (snippet) | "TJR Bootcamp – Free Trading Course", "3+ hours… valued at $997, yours for free" | failed (search snippet only) |
| https://www.comelearnforex.com/compare/trading-course-providers/ | 2026-10-16 | commentary (competitor; conflict of interest) | low | VIP ~$150/mo; "Blueprint" ~$4,997 (flagged as "requires confirmation") | failed (search snippet only) |
| https://www.premiumcourses.net/blog/tjr-blueprint-review-2026 | 2026-10-16 | commentary | low | Blueprint product exists; ES/NQ SMT "lagging index" description | failed (search snippet only) |
| https://couponstroller.com/store/tjrtrades/ | 2026-10-16 | commentary (coupon aggregator) | low | Bundles of courses + indicators sold | failed (search snippet only) |
| https://sozai.app/transcript/path-to-profitability-tjr-strategy/ | 2026-10-16 | secondary (3rd-party transcript) | low-med | TJR "Path to Profitability: TJR's Strategy Explained"; Asia/London H/L + previous-day H/L marked as liquidity | failed (fetch DNS; snippet only) |
| https://sozai.app/transcript/path-to-profitability-liquidity-explained/ | 2026-10-16 | secondary (3rd-party transcript) | low-med | Liquidity above highs/below lows; sweep shows where orders may fill, BOS confirms | failed (fetch DNS; snippet only) |
| https://sozai.app/transcript/path-to-profitability-equilibrium-explained/ | 2026-10-16 | secondary | low | Series includes "equilibrium" lesson | failed (search snippet only) |
| https://sozai.app/transcript/teaching-friend-day-trade/ | 2026-10-16 | secondary | low | "Teaching My Friend How To Day Trade" transcript exists | failed (search snippet only) |
| https://youtubesummary.com/summary/TEp3a-7GUds | 2026-10-16 | secondary (AI summary) | low-med | Strategy "discretionary and adaptive… rather than rigid rules"; 3 steps (draws on liquidity, confirm fills, target exits); previous session / HTF highs-lows; SMT between S&P 500 and Nasdaq | failed (search snippet only) |
| https://aibimb.com/videos/path-to-profitability-tjrs-strategy-explained | 2026-10-16 | secondary | low | Sweeps start moves; exits by partials + runners (attribution uncertain) | failed (search snippet only) |
| https://www.youtube.com/watch?v=AGmAVyAuBE0 | 2026-10-16 | primary (video) | low (snippet) | "Advanced Liquidity Concepts (Path to Profitability)"; description points to TJR program | failed (search snippet only) |
| https://m.youtube.com/watch?v=gwgN0Ek7GXk | 2026-10-16 | primary (video) | low (snippet) | TJR-linked description: FVG "looking perfect" not by itself valid; combine with OB, displacement, structure | failed (fetch DNS; snippet only) |
| https://open.spotify.com/episode/3TTOg3hRU9a16uYQTOfX2k | 2026-10-16 | secondary (podcast listing) | low | "Path to Profitability: How To Find Daily Bias" episode exists | failed (search snippet only) |
| https://open.spotify.com/episode/5737xTlIFvZZmgqFWl5Zvk | 2026-10-16 | secondary | low | "Equilibrium Explained" listing (tagged "Floor Boss"; attribution unclear) | failed (search snippet only) |
| https://www.studocu.com/en-us/document/northwest-vista-college/principles-of-microeconomics/tjr-trade-how-to-spot-order-blocks/46179545 | 2026-10-16 | secondary (user upload) | low | FVGs mainly for retracements; sweeps + BOS drive reversals | failed (search snippet only) |
| https://www.scribd.com/document/851903802/TJR-STRAT | 2026-10-16 | secondary (user upload) | low | Reversal from sweeps confirmed by BOS + FVG | failed (search snippet only) |
| https://www.scribd.com/document/916439470/TJR-Liquidity-Sweep-Strategy | 2026-10-16 | secondary (user upload) | low | "TJR Liquidity Sweep Strategy Guide" exists | failed (search snippet only) |
| https://quizlet.com/935969853/tjr-bootcamp-flash-cards/ | 2026-10-16 | secondary (user-made) | low | "TJR Bootcamp" named program | failed (search snippet only) |
| https://www.forex.in.rs/tjr-trader-strategy/ | 2026-10-16 | commentary | low | NY open; sweep → iFVG → pullback entry; stop under sweep; target opposite liquidity | failed (fetch DNS; snippet only) |
| https://www.snappchart.app/blog/beginner-playbook/tjr-ict-trading-strategy | 2026-10-16 | commentary | low | Map Asia/London H/L before NY | failed (fetch DNS; snippet only) |
| https://www.tiktok.com/discover/tjr-trading-strategy | 2026-10-16 | commentary (aggregator) | low | 5-min manipulation, SMT, 1-min inverse FVG execution | failed (search snippet only) |
| https://it.tradingview.com/script/xXrbltSH-TJR-v4-Strategy/ | 2026-10-16 | commentary (3rd-party script) | low | Raid of PDH/PDL / session H/L / equal H/L → displacement BOS → FVG entry at edge or midpoint | failed (fetch DNS; snippet only) |
| https://www.tradingview.com/script/9yqF7p26-TJR-SEEK-AND-DESTROY/ | 2026-10-16 | commentary (3rd-party script) | low | US hours 09:30–16:00; bias + BOS + sweep; BOS as 5-bar high/low crossover | failed (search snippet only) |
| https://www.tradingview.com/script/M6EyQhlQ-TJR-Trades-Strategy/ | 2026-10-16 | commentary (3rd-party script) | low | Community "TJR Trades Strategy" indicator exists | failed (fetch DNS; snippet only) |
| https://www.tradingview.com/script/IYLMKdC6-TJR-Strategy-Indicator/ | 2026-10-16 | commentary (3rd-party script) | low | Another community TJR indicator exists | failed (search snippet only) |
| https://www.tradingview.com/script/PYg9cFMp-Inversion-Fair-Value-Gap-Model-PJ-Trades/ | 2026-10-16 | commentary (3rd-party script) | low | SMT: one index sweeps a session low, the correlated index does not | failed (search snippet only) |
| https://pl.tradingview.com/scripts/ifvg/page-2/ | 2026-10-16 | commentary | low | An SMC indicator author says it is "NOT a validated edge" | failed (search snippet only) |
| https://grandalgo.com/blog/asian-session-trading-strategy | 2026-10-16 | commentary | low | London sweeps Asia range (generic) | failed (search snippet only) |
| https://www.edgeful.com/blog/posts/trading-sessions-explained | 2026-10-16 | commentary | low-med | Session definitions; London/NY overlap | failed (search snippet only) |
| https://youngmoneyinvestments.com/blog/best-time-to-trade-futures-es-nq-session-guide | 2026-10-16 | commentary | low-med | 09:30–11:00 ET highest-volume window for index futures | failed (search snippet only) |
| https://quantamentaltrader.substack.com/p/unlocking-ict-kill-zones-the-secret | 2026-10-16 | commentary | low | ICT kill zones: London 02:00–05:00, NY 08:00–11:00, Asia 19:00–23:00 NY time | failed (search snippet only) |
| https://ctrader.com/products/4891 | 2026-10-16 | commentary (vendor) | low | FVG = three-candle imbalance | failed (search snippet only) |
| https://propfirmmap.com/glossary/affiliate-program | 2026-10-16 | commentary | low | Prop-firm affiliate commissions 8–70% of challenge fee (context only, not TJR) | failed (search snippet only) |
| https://tradeinformer.com/prop-weekly/will-patrick-wieland-have-to-pay-topstep-5m | 2026-10-16 | commentary | low | Influencer revenue share example (Topstep/Wieland; not TJR) | failed (search snippet only) |
| https://nexusfi.com/showthread.php?p=899824 | 2026-10-16 | commentary (forum) | low | Robbins World Cup transparency concerns (2024; multi-account) | failed (search snippet only) |
| https://forums.babypips.com/t/rrram-fx-fitness-journal/171207/108 | 2026-10-16 | commentary (forum) | low | Anecdotal claims of ICT blown accounts | failed (search snippet only) |
| https://offbeatforex.com/is-ict-strategy-profitable/ | 2026-10-16 | commentary (vendor blog) | low | ICT hard to backtest (discretionary); one tested version lost money | failed (search snippet only) |
| https://backtrex.com/en/blog/liquidity-sweep-strategy-backtest-results | 2026-10-16 | commentary (vendor) | low | Sweep+FVG backtest 53.2% WR / PF 1.68 in kill zones vs 47.1% / 1.21 all sessions; look-ahead inflates WR by 15–30 pp; ≥500 trades | failed (search snippet only) |
| https://www.tradezella.com/blog/backtest-ict-strategy | 2026-10-16 | commentary (vendor) | low | ICT backtesting tooling exists | failed (search snippet only) |
| https://www.ftc.gov/business-guidance/blog/2022/04/ftc-bids-good-night-deceptive-day-trading-earnings-claims | 2026-10-16 | regulator | high (if read) / med (snippet) | FTC action against deceptive day-trading earnings claims (Warrior Trading), April 2022 | failed (search snippet only; ftc.gov DNS) |
| https://www.ftc.gov/node/78914 | 2026-10-16 | regulator | med (snippet) | Warrior Trading: $3M refunds; barred from baseless earnings claims; system "failed to pay off for most customers" | failed (search snippet only) |
| https://www.ftc.gov/node/78867 | 2026-10-16 | regulator | low (snippet, content unclear) | Related FTC page | failed (search snippet only) |
| https://theberkshireedge.com/great-barrington-stock-trading-company-agrees-to-3-million-settlement-with-feds/ | 2026-10-16 | secondary (news) | med | $3M settlement, Great Barrington company | failed (search snippet only) |
| https://www.wwlp.com/news/local-news/berkshire-county/warrior-trading-ordered-to-refund-investors-after-false-gains-claims/amp | 2026-10-16 | secondary (news) | med | Refunds; no-admit settlement; court approval status | failed (search snippet only) |
| https://daytradingtoolkit.com/reviews/warrior-trading-review | 2026-10-16 | commentary (commercial review) | low | Settlement centred on marketing language, not a finding that Cameron's results were fabricated | failed (search snippet only) |
| https://www.financialtechwiz.com/post/ross-cameron-net-worth | 2026-10-16 | commentary | low | $18,810,638 cumulative, Jan 2017–Dec 2025, "audited by an independent CPA" (as reported) | failed (search snippet only) |
| https://www.audible.com/author/Ross-Cameron/B072B7TYHB | 2026-10-16 | primary (author bio) | low-med | Earnings disclaimer; results "NOT typical. Most day traders lose money." | failed (search snippet only) |
| https://www.audible.co.uk/author/Kevin-Davey/B00J34ZNPQ | 2026-10-16 | primary (author bio) | med | 2005 2nd (+148%), 2006 1st (+107%), 2007 2nd (+112%), "real time, real money" contest | failed (search snippet only) |
| https://wiley-vch.e-bookshelf.de/building-winning-algorithmic-trading-systems-website-2633092.html | 2026-10-16 | primary (publisher bio) | med | Same contest results "using algorithmic trading systems" | failed (search snippet only) |
| https://www.luxalgo.com/library/concept/rsi-2/ | 2026-10-16 | commentary | low-med | Connors RSI(2) rules: 200-day MA filter, RSI(2) < 10 | failed (search snippet only) |
| https://backtrex.com/en/backtests/connors-rsi-2-nasdaq-100 | 2026-10-16 | commentary (vendor) | low | RSI(2) on Nasdaq-100: high win rate, low total return | failed (search snippet only) |
| https://quantifiedstrategies.substack.com/p/larry-connors-r3-strategy-it-still-795 | 2026-10-16 | commentary | low | Connors R3 variant rules | failed (search snippet only) |
| https://www.businesswire.com/news/home/20220124005241/en/2021-United-States-Investing-Championship-Winners-%E2%80%94-Minervini-Smashes-Record | 2026-10-16 | primary (organizer press release) | med | Minervini +334.8% (2021, stock division >$1M); 1997 winner +155%; "real money verified competition" | failed (search snippet only) |
| https://completetradersedge.com/mark-minervini-retail-trader-champion/ | 2026-10-16 | commentary | low | 36,000% 5-year "audited" claim (unconfirmed) | failed (search snippet only) |
| https://faculty.haas.berkeley.edu/odean/papers/day%20traders/Day%20Trading%20Skill%20110523.pdf | 2026-10-16 | academic | high (paper) / med (snippet) | Barber-Lee-Liu-Odean: top 500 day traders earn 49.5 (28.1) bps/day before (after) fees in the following year; JFM 2014; Taiwan 1992–2006 | failed (search snippet only) |
| https://www.escholarship.org/content/qt7k75v0qx/qt7k75v0qx.pdf?t=ohrd1z | 2026-10-16 | academic | high/med | Same paper (alternate host) | failed (search snippet only) |
| https://faculty.haas.berkeley.edu/odean/papers/day%20traders/day%20trading%20and%20learning%20110217.pdf | 2026-10-16 | academic | high/med | Aggregate day-trader performance negative; >half of day trading by experienced loss-makers | failed (search snippet only) |
| https://ideas.repec.org/a/oup/rasset/v10y2020i1p61-93..html | 2026-10-16 | academic | high/med | "Learning, Fast or Slow" (RAPS 2020): 97% of day traders likely to lose money in future day trading | failed (search snippet only) |
| https://www.econ.puc-rio.br/uploads/adm/seminarios/Learning_fast_or_slow_180606.pdf | 2026-10-16 | academic | med | Same paper (seminar version) | failed (search snippet only) |
| https://repositorio.fgv.br/items/e87d04fc-4b4c-4a56-ab5a-1c84c1afde1b/full | 2026-10-16 | academic | high/med | Chague-De-Losso-Giovannetti: 97% of >300-day persisters lost money; 0.4% > bank teller (WP version) | failed (search snippet only) |
| https://ideas.repec.org/p/spa/wpaper/2019wpecon47.html | 2026-10-16 | academic | med | Same paper listing | failed (search snippet only) |
| https://www.cxoadvisory.com/investing-expertise/day-trading-a-bust/ | 2026-10-16 | commentary (research summary) | med | 19,646 individuals; 1.1% > min wage, 0.5% > bank teller; caveats on generalisability | failed (search snippet only) |
| https://www.sec.gov/newsroom/press-releases/99-114-day-trading-your-dollars-risk-investor-alert | 2026-10-16 | regulator | n/a | Requested URL for SEC day-trading alert | failed (fetch DNS) |
| https://www.sec.gov/news/press/pressarchive/1999/99-114.txt | 2026-10-16 | regulator | high/med | SEC 99-114, 16 Sep 1999, "Day Trading: Your Dollars at Risk": severe early losses, borrowed money, only risk money you can afford to lose | failed (search snippet only) |
| https://www.sec.gov/files/investor/pubs/daytips.htm | 2026-10-16 | regulator | high/med | Web version of the same alert | failed (search snippet only) |
| https://www.esma.europa.eu/node/84933 | 2026-10-16 | regulator | high/med | 74–89% of retail CFD accounts lose money; avg loss €1,600–€29,000; standardised risk warning; agreed 23 Mar 2018 | failed (search snippet only) |
| https://www.consob.it/documents/1912911/1970971/esma35_43_1000.pdf/6dc9bc30-c528-09dc-9430-398c8df4c3af | 2026-10-16 | regulator | med | ESMA CFD Q&A document (hosted by CONSOB) | failed (search snippet only) |
| (reddit.com — r/algotrading, r/Daytrading) | 2026-10-16 | commentary | n/a | ICT/SMC failed-backtest discussions | failed (WebSearch domain blocked) |

Note: an FTC press-release URL guessed in an earlier draft of this log (…/press-releases/2022/09/…) was **removed** because it was never verified. The search-verified FTC URLs above replace it, and they date the action to April 2022.

## 3. Data sources, exchange documentation, fees

| URL | type | quality | claim |
|---|---|---|---|
| https://docs.kraken.com/api-reference/market-data/get-ohlc-data.md | official docs (search extract) | high | OHLC returns max 720 most-recent entries; older not retrievable; last candle uncommitted |
| https://docs.kraken.com/exchange/guides/general/historical-data | official guide (search extract) | high | intervals; `last`→`since` paging; trades 1000/call |
| https://docs.kraken.com/api-reference/market-data/get-recent-trades.md | official docs (search extract) | high | last 1000 trades default |
| https://docs.kraken.com/api/docs/guides/spot-rest-ratelimits | official docs (search extract) | high | counter 15/20/20; decay 0.33/0.5/1 per s; history calls +2 |
| https://docs.kraken.com/exchange/api-reference/spot-websocket | official docs (search extract) | high | WS v2 recommended; wss://ws.kraken.com/v2 |
| https://docs.kraken.com/exchange/api-reference/spot-websocket-v2/ohlc.md | official docs (search extract) | high | ohlc channel updates on trade events |
| https://apis.io/asyncapis/kraken/kraken-asyncapi/ | third-party spec | low-medium | WS intervals, trade snapshot 50 |
| https://lablab.ai/tech/kraken/kraken-websocket-api | third-party | low | book depths 10–1000 |
| https://docs.kraken.com/api/docs/futures-api/trading/historical-funding-rates | official docs (search extract) | high | funding history endpoint v3 |
| https://docs.kraken.com/api-reference/historical-funding-rates/historical-funding-rates | official docs (search extract) | high | fields timestamp/fundingRate/relativeFundingRate |
| https://download-crypto-currencies-data.readthedocs.io/en/latest/how-to/derivatives.html | third-party | low | ~1y funding retention, hourly (unverified) |
| https://support.kraken.com/articles/360047124832-downloadable-historical-ohlcvt-open-high-low-close-volume-trades-data | official support (search extract) | high | OHLCVT CSV, quarterly, gaps omitted |
| https://www.kraken.com/features/fee-schedule | official (search extract) | high | Tier1 $0+: 0.40%/0.80%; Tier2 0.30/0.60; Tier3 0.22/0.38 |
| https://blog.kraken.com/product/pro/new-kraken-pro-fee-tiers | official blog | high | tiers changed 2026-07-09 |
| https://support.kraken.com/articles/201893638-how-trading-fees-work-on-kraken | official support | high | fee range −0.02% to 0.80% |
| https://finance.yahoo.com/personal-finance/investing/review/kraken-review-130000202.html | review | low | old base tier 0.25%/0.40% |
| https://support.kraken.com/articles/206161568-what-are-the-fees-opening-and-rollover-for-trading-using-margin- | official support (search extract) | high | margin fee on borrowed amount; BTC/USD long 0.025%, short 0.010%; locked rollover |
| https://support.kraken.com/articles/us-margin-fees | official support (search extract) | high | rollover every 4 hours |
| https://www.kraken.com/features/margin-trading/bitcoin | official product page | medium (older) | up to 0.02% open, up to 0.02%/4h rollover |
| https://docs.kraken.com/api/docs/rest-api/get-tradable-asset-pairs | official docs (search extract) | high | XXBTZUSD pair_decimals 1, lot_decimals 8, cost_decimals 5, ordermin 0.0001, costmin 0.5, tick_size 0.1 |
| https://python-kraken-sdk.readthedocs.io/en/stable/04_spot/rest.html | SDK docs | medium | same values |
| https://support.kraken.com/articles/205893708-Minimum-order-size-volume-for-trading | official support | high | BTC min 0.0001 |
| https://apify.com/benthepythondev/kraken-asset-pairs-scraper/examples/kraken-asset-pairs-scraper-sample | third-party scrape | low | ordermin 0.00005 (conflict) |
| https://github.com/binance/binance-public-data | official repo (fetched) | high | Binance Vision contents, columns, µs timestamps 2025+ |
| https://github.com/ff137/bitstamp-btcusd-minute-data | dataset repo (fetched) | high | coverage, zero-volume fill, CC BY-SA 4.0 / CC BY 4.0 |
| https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles | official docs (search extract) | high | granularities; no candles w/o ticks |
| https://bourse.hexdocs.pm/Bourse.CoinbaseCandlePagination.html | third-party | low-medium | 300-candle max |
| https://jentic.com/apis/bitstamp | third-party | low | Bitstamp ohlc step/limit |
| https://www.cryptodatadownload.com/data/bitstamp/ | vendor | medium | minute data needs free account |
| https://tardis.dev/ | vendor | high | data scope |
| https://docs.tardis.dev/node.js-client | vendor docs | high | free first day of month |
| https://docs.ccxt.com/docs/comparisons/ccxt-vs-tardis | third-party | low-medium | $350–$6,000/mo; data from 2019-03-30 |
| https://www.datarade.ai/data-products/kaiko-order-book-snapshot-real-time-centralized-exchanges-tick-by-tick-order-books-depth-kaiko | marketplace | medium | Kaiko pricing on request; history since 2014 |
| https://www.coinapi.io/products/flat-files | vendor | high | $1/GB LOB, $3/GB trades; hourly partitions from 2026-06-09 |
| https://www.tradingview.com/pine-script-docs/faq/strategies/ | official (search extract) | high | process_orders_on_close, repaint advice |
| https://www.tradingview.com/pine-script-docs/concepts/strategies/ | official (search extract) | high | bar magnifier, 200k LTF bars |
| https://www.tradingview.com/pine-script-docs/v4/essential/strategies/ | official legacy | high | O→H→L→C heuristic |
| https://docs.alpaca.markets/docs/about-market-data-api | official docs | high | Basic=IEX ~2.5%, $99 SIP plan |
| https://quantrocket.com/blog/survivorship-bias | vendor blog | medium | assume bias unless delisted included |
| https://nexusfi.com/d/data-providers/norgate-data/ | forum/directory | low-medium | Norgate ~$35/mo, delisted |

## 4. Strategy literature

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

## 5. Methodology references

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

## 6. Fee-change corroboration (lead agent, 2026-10-16)

| URL | Type | Quality | Claim | Accessed |
|---|---|---|---|---|
| https://pricingsaas.com/companies/kraken/diffs/2026W29 | pricing tracker | medium | entry spot tier moved 0.25%/0.40% -> 0.40%/0.80% (week of 2026-07-06) | search extract |
| https://support.kraken.com/articles/201893638-fee-schedule | official support | high | fee range -0.02% maker to 0.80% taker | search extract |
| https://www.datawallet.com/crypto/kraken-fees-explained | secondary | low-medium | redesign effective 2026-07-09 | search extract |
