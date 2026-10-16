> **Provenance.** Researched on 2026-10-16 by a research sub-agent using web search; reviewed and integrated by the lead agent. Direct page fetches of most primary sites (Kraken, TradingView, YouTube, TJR, SEC, FTC) failed from this environment (DNS/proxy policy), so many facts come from search-engine extracts of the cited pages and are labelled accordingly. Treat "unverified" items as unverified.

# Data Sources for Realistic Backtesting (crypto + equities)

Compiled 2026-10-16. Status: complete (see "unverified" markers).

**Access caveat (important for auditing):** from this environment WebFetch of `docs.kraken.com`, `support.kraken.com`, `api.kraken.com` all failed with DNS errors (`getaddrinfo ENOTFOUND`). All Kraken facts below therefore come from **web-search-engine extracts of the official Kraken pages** (URLs cited are the official pages that the search engine read), not from a direct page fetch by me. Treat every Kraken number as "verified via search extract of official page; re-check live before trading". Items I could not see at all are marked **unverified**.

---

## 1. Kraken Spot REST API

### 1.1 OHLC endpoint (`GET /0/public/OHLC`)
- Official reference: https://docs.kraken.com/api-reference/market-data/get-ohlc-data.md (also linked as https://docs.kraken.com/api/docs/rest-api/get-ohlc-data).
- **720-candle limit: YES.** Per the official reference (search extract): returns up to **720 of the most recent entries**; **older data cannot be retrieved regardless of `since`**; the last array entry is the **current, not-yet-closed candle** and is always included.
- Intervals (minutes): 1, 5, 15, 30, 60, 240, 1440, 10080, 21600 — per Kraken's historical-data guide https://docs.kraken.com/exchange/guides/general/historical-data (search extract).
- Practical consequence: with 1-minute candles you get only ~12 hours of history (720 min); with daily candles ~2 years. Use the response `last` value as the next `since` for polling forward — but you cannot page backwards past the 720-entry window (same guide).
- Auth: none (public).
- Each OHLC row (per Kraken docs, widely known schema): time, open, high, low, close, vwap, volume, count. *Field list not re-seen in this session's extracts — treat as unverified-by-me.*
- **Backtest suitability:** unusable alone for multi-month intraday history. Must be combined with the Trades endpoint (rebuild candles) or Kraken's downloadable OHLCVT files (section 1.6).

### 1.2 Trades endpoint (`GET /0/public/Trades`) — the route to full history
- Official reference: https://docs.kraken.com/api-reference/market-data/get-recent-trades.md
- Returns **the last 1000 trades by default** (official reference, search extract). The historical-data guide describes trade ticks at up to 1000 trades per call, no authentication, and how to paginate for bulk collection (https://docs.kraken.com/exchange/guides/general/historical-data).
- Pagination: response field `last` is used as the next `since` cursor. Exact unit of `since` (nanosecond timestamp vs. trade ID) and the max `count` were **unverified** in this session (the search extract did not include the full parameter list).
- Unlike OHLC, the Trades endpoint lets you walk forward from an early `since` to reconstruct full tick history (third-party downloader confirms Kraken provides full paginated history: https://download-crypto-currencies-data.readthedocs.io/en/v2.3.3/histo_dl.kraken.html). Expect very many calls for liquid pairs (1000 trades/call), so rate limits dominate run time.
- Trade records include price, volume, time, side (buy/sell) and order type (market/limit) — lets you build signed trade-flow imbalance. *Field list: unverified-by-me in this session.*

### 1.3 Rate limits / API call counter
Official: https://docs.kraken.com/api/docs/guides/spot-rest-ratelimits (search extract)
| Verification tier | Max counter | Decay |
|---|---|---|
| Starter | 15 | −0.33 / s |
| Intermediate | 20 | −0.5 / s |
| Pro | 20 | −1 / s |
- Counter is per API key; most private calls +1; **ledger/trade-history calls +2**; exceeding max → `EAPI:Rate limit exceeded`.
- AddOrder/CancelOrder use a **separate trading (matching-engine) rate limiter**, not this counter.
- Master and subaccounts share trading limits per the master's tier.
- Public-endpoint (OHLC/Trades) per-IP limits: **unverified** (not in extract). Practical rule used by most downloaders is ~1 req/s; treat as an assumption.

### 1.4 WebSocket v2 (`wss://ws.kraken.com/v2`)
- Overview: https://docs.kraken.com/exchange/api-reference/spot-websocket — v2 recommended for new integrations; v1 maintained for existing clients.
- `ohlc` channel: https://docs.kraken.com/exchange/api-reference/spot-websocket-v2/ohlc.md — streams OHLC for an interval; accepts list of symbols; **updates generated on trade events** (so no update in a minute with no trades). Intervals 1, 5, 15, 30, 60, 240, 1440, 10080, 21600 (AsyncAPI summary https://apis.io/asyncapis/kraken/kraken-asyncapi/ — third-party).
- `trade` channel: side, qty, price, order type, trade ID, RFC3339 timestamp; optional snapshot of last 50 trades — **third-party summaries only** (https://apis.io/asyncapis/kraken/kraken-asyncapi/), official page not seen → unverified.
- `book` channel: depth 10/25/100/500/1000 with CRC32 checksum — **third-party summary only** (https://lablab.ai/tech/kraken/kraken-websocket-api); official book page not seen → unverified.
- **Backtest suitability:** WS is forward-only. It is the only free way to build your own L2 history on Kraken — you must record it yourself (no historical L2 from Kraken for free).

### 1.5 Kraken Futures — funding-rate history
- Official reference: https://docs.kraken.com/api/docs/futures-api/trading/historical-funding-rates and https://docs.kraken.com/api-reference/historical-funding-rates/historical-funding-rates
- Base server `https://futures.kraken.com/derivatives/api/v3`; path `historical-funding-rates` (API reference) / `historicalfundingrates` (guide), `symbol` = perpetual e.g. `PF_BTCUSD` (or legacy `PI_XBTUSD`). Returns `rates` list sorted ascending with `timestamp`, `fundingRate`, `relativeFundingRate`. (search extracts)
- There is **no v4** of this endpoint in the results (the user prompt's `/v4/` path is not supported by the docs).
- Funding cadence (hourly?) and retention (~1 year per third-party guide https://download-crypto-currencies-data.readthedocs.io/en/latest/how-to/derivatives.html) → **unverified** against official docs.

### 1.6 Kraken downloadable historical OHLCVT / trades CSVs
- Official support article: https://support.kraken.com/articles/360047124832-downloadable-historical-ohlcvt-open-high-low-close-volume-trades-data (search extract; article last updated 2026-04-26).
- CSV OHLCVT for **every pair from the start of each market**; "T" = trade **count** per interval (not tick records).
- Intervals in ZIPs: 1, 5, 15, 30, 60, 240, 720, 1440 min.
- **Quarterly** incremental ZIP updates; full history (to 30 June 2026 in one version of the page) split into ~2 GB parts.
- **Intervals with no trades are omitted** — missing rows mean no trades (do NOT forward-fill volume; fill price flat with zero volume only if your engine needs a regular grid).
- A separate "Time and Sales" (tick) download has historically been offered by Kraken; it was **not** visible in this session's extract → unverified.
- Hosted as downloads (historically Google Drive links) — no API; licensing terms **unverified**.
- **Backtest suitability:** best free source for Kraken-native bars; lags up to one quarter → stitch with REST Trades for the recent tail.

### 1.7 Kraken Pro spot fee schedule (official)
- Official: https://www.kraken.com/features/fee-schedule ; change announcement https://blog.kraken.com/product/pro/new-kraken-pro-fee-tiers (tiers changed **9 July 2026**; tier now = best of spot volume, futures volume, or assets-on-platform).
- Current table per search extract of the official page:
| Tier | 30-day volume | Maker | Taker |
|---|---|---|---|
| Tier 1 (lowest) | $0+ | **0.40%** | **0.80%** |
| Tier 2 | $2.5K+ | 0.30% | 0.60% |
| Tier 3 | $10K+ (or $20K AoP) | 0.22% | 0.38% |
| top ("Pro 5") | $500M+ | rebates (−0.02% maker on some tables) | — |
- Help-center range: −0.02% (maker) to 0.80% (taker) (https://support.kraken.com/articles/201893638-how-trading-fees-work-on-kraken). Stablecoin/FX pairs and Buy-Crypto purchases do not count toward volume.
- **Older (pre-July-2026) lowest tier was 0.25% maker / 0.40% taker** (<$10K), still quoted by many reviews (e.g. https://finance.yahoo.com/personal-finance/investing/review/kraken-review-130000202.html). **Use 0.40%/0.80% as the conservative current base tier** and verify live.
- Round-trip cost at lowest tier, taker both sides: 1.60% of notional — this alone kills most intraday strategies on small accounts.

### 1.8 Kraken margin fees (official)
- Official: https://support.kraken.com/articles/206161568-what-are-the-fees-opening-and-rollover-for-trading-using-margin- (updated 2026-07-28 per extract); US: https://support.kraken.com/articles/us-margin-fees ; https://www.kraken.com/features/margin-trading/bitcoin
- Fees charged on the **amount borrowed** (collateral not deducted). Normal trade fee applies to opening and closing volume.
- **Opening fee + rollover fee, rollover charged every 4 hours** while open (US margin fees page).
- BTC/USD examples in the official article: **long ≈ 0.025%** (on USD borrowed), **short ≈ 0.010%** (on BTC borrowed); rollover rate is **locked at execution**; rates vary with market conditions.
- Bitcoin margin product page (older): **up to 0.02% to open, up to 0.02% per 4 hours rollover**. Spot-margin opening fee range 0.01%–0.05% depending on pair.
- Liquidation fee: 2% (July 2026 version; earlier 3%).
- Backtest implication: at 0.02%/4h, rollover ≈ 0.12%/day ≈ 44%/yr on borrowed notional (arithmetic from the "up to" figure; actual rate varies) — overnight leveraged holds are expensive.

### 1.9 XBT/USD order minimums & precision (AssetPairs)
- Official endpoint docs: https://docs.kraken.com/api/docs/rest-api/get-tradable-asset-pairs ; live data: `https://api.kraken.com/0/public/AssetPairs?pair=XBTUSD` (could not be fetched here).
- Values shown in the official docs example for `XXBTZUSD` (search extract; same in python-kraken-sdk docs https://python-kraken-sdk.readthedocs.io/en/stable/04_spot/rest.html):
| Field | Value |
|---|---|
| altname / wsname | XBTUSD / XBT/USD |
| pair_decimals (price precision) | **1** |
| tick_size | **0.1** USD |
| lot_decimals (volume precision) | **8** |
| cost_decimals | 5 |
| ordermin | **0.0001** BTC |
| costmin | **0.5** USD |
- Support article also says BTC minimum = 0.0001 BTC (https://support.kraken.com/articles/205893708-Minimum-order-size-volume-for-trading, dated 2026-02-03). A third-party Apify scrape shows 0.00005 (https://apify.com/benthepythondev/kraken-asset-pairs-scraper/examples/kraken-asset-pairs-scraper-sample) → minimum may have changed; **query the live endpoint before trading**.

---

## 2. Binance public data (data.binance.vision)
- Official repo: https://github.com/binance/binance-public-data (fetched).
- Spot and Futures (USD-M, COIN-M): `aggTrades`, `klines`, `trades`; **daily** files available next day, **monthly** files on first Monday of month; each zip has a `.CHECKSUM` (SHA-256).
- 16 kline intervals 1s → 1mo. Kline columns: Open time, O, H, L, C, Volume, Close time, Quote asset volume, Number of trades, Taker buy base volume, Taker buy quote volume, Ignore → **taker-buy volume gives a free trade-flow imbalance proxy at bar level**.
- **Spot timestamps are in microseconds from 2025-01-01** (ms before) — a classic parsing bug.
- Archived files can be revised (fixes listed 2022-04-21, 2022-08-08).
- Repo code MIT; data use governed by separate Terms and Conditions (not read → unverified).
- Not on README page: bookTicker/bookDepth/fundingRate/metrics (may exist in bucket; **unverified**).
- No auth, no rate limit for bulk files (static downloads). Binance is a different venue from Kraken — prices/microstructure differ; US persons cannot trade binance.com.

---

## 3. GitHub dataset: ff137/bitstamp-btcusd-minute-data
- https://github.com/ff137/bitstamp-btcusd-minute-data (fetched).
- Bitstamp **BTC/USD 1-minute** OHLCV. Bulk history **2012-01-01 → 2025-01-07** (`data/historical/btcusd_bitstamp_1min_2012-2025.csv.gz`); daily updates from 2025-01-07 onward via a **GitHub Action at midnight UTC** fetching the **Bitstamp API** (`data/updates/btcusd_bitstamp_1min_latest.csv`).
- Columns: `timestamp, open, high, low, close, volume`; `timestamp` = UTC open of `[t, t+60s)`.
- **Missing minutes are filled with flat zero-volume candles** (integrity script guarantees 1 row/minute). Zero-volume rows are ambiguous (low liquidity vs missing record vs outage); provenance file is "best-effort". Longest outage: 108 h from 5 Jan 2015 (Bitstamp hot-wallet incident).
- **Licensing:** historical portion **CC BY-SA 4.0**, attribution "Zielak (mczielinski), Bitcoin Historical Data, Kaggle" (Kaggle dataset version 706); daily updates **CC BY 4.0**, suggested attribution "Bitstamp BTC/USD minute data, github.com/ff137/bitstamp-btcusd-minute-data"; combined artifacts inherit **CC BY-SA 4.0** (share-alike); code is MIT (code only).
- Before 2026-08-28 updates rewrote git history — old clones need a one-time reset.
- **Backtest suitability:** good for long-horizon BTC intraday research (14 years). Caveats: Bitstamp ≠ Kraken venue; no trade count/VWAP/side; filled candles must be masked (exclude zero-volume minutes from signal generation and fills); pre-2014 liquidity is very thin.

---

## 4. Coinbase Exchange candles
- Official: https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles (search extract).
- `granularity` must be one of {60, 300, 900, 3600, 21600, 86400} seconds; otherwise rejected.
- Max candles per request: the official page text says a request exceeding the maximum data points is rejected (number rendered as a template placeholder in the extract); the **300-candle maximum** is stated by third-party docs (https://bourse.hexdocs.pm/Bourse.CoinbaseCandlePagination.html) → official number **unverified by me**, but consistent with the task brief.
- Paging: split range into multiple start/end requests. **No candle published for intervals with no ticks.** Row format `[time, low, high, open, close, volume]` (note low/high before open/close — common parsing bug).
- Public, no auth. Rate limits: **unverified** in this session.

## 5. Bitstamp API
- `/api/v2/ohlc/{currency_pair}/` with `step` (60 s … 3 days) and `limit` — per third-party pages (https://jentic.com/apis/bitstamp ; example with limit=1000, step=300 at https://blog.devgenius.io/maximize-your-financial-data-how-to-retrieve-and-manage-a-large-ohlc-dataset-from-the-bitstamp-api-f8d8aa156b43). Official Bitstamp docs were not reached → max `limit` and rate limits **unverified**.
- Bitstamp is the source of the ff137 dataset's daily updates (section 3).

## 6. CryptoDataDownload
- https://www.cryptodatadownload.com/data/bitstamp/ — daily, hourly and minute CSVs; **minute data requires a free registered account**. API/python examples: https://www.cryptodatadownload.com/blog/posts/historical-bitstamp-ohlcv-data-api-python/
- Kraken coverage and licensing terms: **unverified**. Aggregated third-party re-publication of exchange data; check gaps/duplicates and timezone; no L2.

## 7. Tardis.dev (paid tick / L2)
- https://tardis.dev/ — tick-by-tick order-book snapshots & incremental updates, trades, open interest, funding, options chains, liquidations; downloadable CSV + Python/Node clients.
- **Free: first day of each month** for replay without API key (https://docs.tardis.dev/node.js-client ; also https://nautilustrader.io/docs/latest/integrations/tardis/).
- Pricing: $350–$6,000/month per a third-party comparison (https://docs.ccxt.com/docs/comparisons/ccxt-vs-tardis) → **unverified on tardis.dev**. Earliest feeds from 2019-03-30 per same page.
- **Suitability:** the practical choice for order-book-imbalance / queue-position / spread-aware backtests (category D strategies). Includes Kraken (exchange list not re-verified here).

## 8. Kaiko / CoinAPI (paid)
- **Kaiko:** no public pricing (contact sales — https://www.datarade.ai/data-products/kaiko-order-book-snapshot-real-time-centralized-exchanges-tick-by-tick-order-books-depth-kaiko). Order-book snapshots (2×/min, within 10% of mid) with history since 2014 per Datarade listing; tick-level books with shorter rolling history. Also resold by Deutsche Börse (https://www.mds.deutsche-boerse.com/mds-en/historical-data/marketplace/digital-assets). Institutional; license restricts redistribution (terms unverified).
- **CoinAPI Flat Files** (https://www.coinapi.io/products/flat-files): usage-based — L2/L3 order book **$1/GB**, trades **$3/GB**, quotes **$1/GB** (pay-as-you-go, per extract; verify). Gzip CSV, S3-compatible layout; from **2026-06-09** new trades/quotes/LOB files are **hourly partitions** (previously daily T+1). 380+ exchanges; keeps delisted assets (https://www.coinapi.io/blog/historical-data-for-delisted-crypto-coins).

## 9. TradingView / Pine Script strategy tester
- FAQ: https://www.tradingview.com/pine-script-docs/faq/strategies/ ; concepts: https://www.tradingview.com/pine-script-docs/concepts/strategies/ (direct fetch failed with DNS error; facts from search extracts of these official pages).
- **Default fill timing:** with `process_orders_on_close=false` (default), an order generated on a bar's close is filled at the **next bar's open** at the earliest. `process_orders_on_close=true` fills on the same close — the FAQ warns this can be unrealistic/repaint because a closed bar can't be traded.
- **Intrabar path assumption (broker emulator):** fills anywhere inside the bar's range, no gaps assumed. Legacy (v4) docs: if high is closer to open than low → assumes **open→high→low→close**, else **open→low→high→close** (https://www.tradingview.com/pine-script-docs/v4/essential/strategies/). Current docs describe inferring intrabar movement from OHLC; exact current rule → treat legacy rule as the likely default (unverified for v6).
- **Bar magnifier** (`use_bar_magnifier=true`, "Bar detalization" in Properties): uses lower-timeframe data for intrabar fills on historical bars; **max 200,000 lower-timeframe bars**, so early history may lack intrabar coverage. Plan restrictions (premium) → **unverified** in this session.
- To avoid repainting: set `calc_on_every_tick`, `calc_on_order_fills`, `process_orders_on_close` to false.
- Slippage/commission are user-set strategy properties (https://www.tradingview.com/support/solutions/43000628599-strategy-properties/); defaults are zero-ish → always set them.
- **Suitability:** quick prototyping only. Weaknesses for rigorous work: hidden intrabar assumption when stop and target are both inside one bar; no order-book/queue model; easy to overfit via the UI; limited history on low timeframes; no built-in multiple-testing control.

## 10. Stock data
- **Alpaca** (https://docs.alpaca.markets/docs/about-market-data-api): Basic (free) = real-time **IEX only (~2.5% of volume)**; Algo Trader Plus **$99/month** = all US exchanges (SIP, 100%). `feed` parameter switches. Older page lists 200 req/min historical on free vs 10,000/min paid (https://alpaca.markets/docs/market-data). IEX-only bars have systematically lower volume and different highs/lows than consolidated → **do not backtest ORB/RVOL on IEX-only bars**. History start date: unverified.
- **Polygon.io** (rebranded "Massive" per brief) flat files: **unverified** in this session (no official page seen).
- **IEX Cloud:** shutdown (Aug 2024) **unverified** in this session.
- **Yahoo Finance / yfinance:** unofficial, no SLA; datasets that do not explicitly include delisted names should be assumed survivorship-biased (https://quantrocket.com/blog/survivorship-bias).
- **Survivorship-bias-free:** Norgate Data — listed + delisted US stocks and historical index constituents; US Stocks package ~$35/month per NexusFi (https://nexusfi.com/d/data-providers/norgate-data/, third-party; https://concretumgroup.com/the-complete-norgate-data-toolkit-three-python-workflows-every-quant-researcher-needs/). **CRSP** (academic standard, delisting returns): not verified in this session; delisting-return handling discussed at https://alphaarchitect.com/2016/08/dealing-with-delistings-a-critical-aspect-for-stock-selection-research/.
- Low-float/penny-stock work additionally needs: halt (LULD) history, corporate-action/dilution filings (SEC EDGAR), borrow availability/fees, and quote (NBBO) data for spreads — none of which come with free bar data.

## 11. Suitability summary (realistic backtesting)
| Source | Granularity | History | Cost | Use for |
|---|---|---|---|---|
| Kraken OHLC REST | 1m–15d | last 720 bars only | free | live/paper bars only |
| Kraken Trades REST | tick | full (paged, slow) | free | rebuild Kraken bars, trade-flow |
| Kraken OHLCVT ZIPs | 1m–1d | inception→last quarter | free | main Kraken bar history |
| Kraken WS v2 | tick/L2 | forward only | free | record own L2 |
| Kraken Futures funding | per funding period | ~1y? (unverified) | free | funding-rate signals |
| Binance Vision | 1s–1mo, trades | 2017+ | free | cross-venue, taker-flow proxy |
| Coinbase candles | 1m–1d | paged 300/req | free | cross-venue check |
| ff137 Bitstamp 1m | 1m | 2012→now | free, CC BY-SA | long BTC intraday research |
| Tardis | tick + L2 | 2019+ | $$ | order-book strategies |
| CoinAPI / Kaiko | tick + L2 | varies | $$–$$$ | institutional |
| TradingView | bar (+magnifier) | plan-limited | freemium | prototyping only |
| Norgate/CRSP | daily (Norgate), daily/monthly (CRSP) | decades incl. delisted | $–$$$ | equity survivorship-free tests |

---

## Sources
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

---

## 12. What was actually accessed and tested from this environment (2026-10-16)

| Endpoint / host | Result | How verified |
|---|---|---|
| `api.kraken.com` (REST public: Time, OHLC) | **BLOCKED** — proxy answered 403 to CONNECT | `curl` + proxy status log |
| `futures.kraken.com`, `docs.kraken.com`, `support.kraken.com` | **BLOCKED** (403 / DNS) | `curl`, WebFetch |
| `api.binance.com`, `data.binance.vision`, `api.exchange.coinbase.com` | **BLOCKED** | `curl` |
| `www.cryptodatadownload.com`, `stooq.com`, Yahoo Finance, Kaggle, Hugging Face | **BLOCKED** | `curl` |
| `raw.githubusercontent.com` / `github.com` | **reachable** | dataset downloaded, SHA-256 verified |
| `ff137/bitstamp-btcusd-minute-data` @ `b1d538ca` | **used** — 93.8 MB history + 52.0 MB updates | SHA-256 of the historical file matches the maintainer's published manifest (`1be15206…`) |

Consequences:

* **No Kraken API call was ever tested against the live exchange.** The Kraken client's
  request signing was verified only against Kraken's published documentation example
  (unit test), and its REST handling only against mocked responses.
* Live-feed paper trading (Kraken OHLC polling) could not be run here; paper trading was
  validated in **replay mode** on historical bars (see `test_report.md`).
* The research dataset is Bitstamp, not Kraken: prices differ slightly between venues, and
  Kraken's own liquidity/spreads were not measured.

To enable the Kraken feed, the environment's network policy must allow `api.kraken.com`
(cloud environment settings → Network access → Allowed domains).
