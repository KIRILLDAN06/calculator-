# Candidate Specifications (exact mechanical rules)

Every rule below is implemented verbatim in `src/qtrade/strategies/` and executed by the engine
in `src/qtrade/backtest/engine.py`. **All parameter values are experimental assumptions** chosen
before testing (pre-registered in `backtest_methodology.md`), not proven settings.

## Common conventions (all candidates)

| Item | Rule |
|---|---|
| Market | BTC/USD spot (Bitstamp prices; Kraken-modelled costs and order rules) |
| Bars | Complete bars only, labelled by open time (UTC); a bar is evaluated only after it closes |
| Decision → action | Signal at close of bar *t* → order active from open of bar *t+1* |
| Position | One position at a time, no pyramiding; entry signals while a position or entry order is open are ignored (logged) |
| Sizing | qty = 0.5% × equity / \|entry reference − stop\|, capped at 1.0× equity notional and 5% of the signal bar's traded USD volume; floored to 1e-8 BTC; rejected below 0.0001 BTC |
| Prohibited entries | stale bar (incomplete or zero trades), daily loss ≥ 3% (UTC day), ≥ 4 entries that UTC day, invalid stop side |
| Fills | market: next open ± slippage, taker; limit: only if traded *through*, maker, no slippage; stop: min(open, stop) for longs / max for shorts, ± slippage, taker; stop wins if stop and target share a bar; on a limit-entry fill bar the target is ignored |
| Shorts | margin: opening fee + rollover pro rata per bar |
| Session clock | America/New_York, DST-aware (`tz_convert`) |

---

## C1 — `donchian_trend` (simple trend benchmark), 1h bars

**Hypothesis.** BTC trends persist after breaking multi-day ranges (time-series momentum).
**Favourable regime:** sustained trends (2017, 2020-21, 2024). **Unfavourable:** ranges/whipsaw.

State machine (evaluated at each 1h close *t*):

1. `HH = max(high[t-48 … t-1])`, `LL = min(low[t-48 … t-1])` (previous 48 bars, excluding *t*).
2. **Long entry** if `close[t] > HH[t]` and NOT `close[t-1] > HH[t-1]` (first close above; cross event).
   **Short entry** mirror (`close < LL`, first close below).
3. Initial stop = `close[t] ∓ 2.0 × ATR24[t]` (Wilder ATR, 24 bars). No profit target.
4. Trailing (tighten-only, effective next bar): long stop = max(stop, min(low[t-23 … t])); short mirror.
5. Exit only via stop (initial or trailing). Re-entry allowed on the next cross event.

Grid: entry_n ∈ {24, 48, 96} × stop_atr ∈ {2, 3}.

## C2 — `bollinger_mr` (mean reversion), 15m bars

**Hypothesis.** Short-horizon overextensions revert when trend strength is low.
**Favourable:** ranging, liquid markets. **Unfavourable:** trend days, volatility expansion.

1. `mid = SMA20(close)`, `z = (close − mid) / σ20` (population σ), `ADX14` (Wilder).
2. **Long** if `z[t] < −2.5` and `z[t-1] ≥ −2.5` (cross) and `ADX14[t] < 25`; **short** mirror (`z > +2.5`).
3. Stop = `close[t] ∓ 2.0 × ATR14`; target = `mid[t]` (fixed at signal time).
4. Time exit: close at the open after 16 bars (4 h) in the trade.

Grid: z ∈ {2.0, 2.5, 3.0} × adx_max ∈ {20, 25, 100 (= filter off)}.

## C3 — `intraday_momentum` (first → last half-hour), 30m bars

**Hypothesis (adapted from equity "market intraday momentum").** The first half-hour return of
the UTC day predicts the last half-hour return. **Data:** 30m bars. Crypto has no closing auction,
so the UTC day boundary is an **experimental assumption**.

1. `r1 = close/open − 1` of the 00:00–00:30 UTC bar of the same UTC day (must exist).
2. At the close of the 23:00–23:30 bar: direction = sign(r1). Mode `both`: also require
   sign(23:00 bar return) = sign(r1).
3. Enter at 23:30 open; exit at the next open (00:00 UTC) — 1 bar hold. Stop = `close ∓ 2 × ATR48` (sizing / protection).

Grid: mode ∈ {first, both}.

## C4 — `orb` (opening-range breakout on the US cash session), 5m bars

**Hypothesis.** The US equity open concentrates information flow; BTC's direction after breaking
the first 15 minutes' range persists into the session (adapted from Zarattini & Aziz' QQQ ORB).

1. Opening range (OR) = high/low of bars in [09:30, 09:45) ET; all 3 bars must be present.
2. Eligible bars: start ≥ 09:45 ET and end ≤ 15:00 ET, Monday–Friday.
3. **Entry**: the first eligible bar of the day whose **close** > OR high (long) or < OR low (short).
   Only one entry per day (the first breakout, either direction).
4. Stop: opposite side of the OR (`stop_mode=opposite`) or `close ∓ ATR14` (`atr`). Target: none
   (`rr=None`) or `rr × risk`.
5. Exit at the open at 16:00 ET (signal on the 15:55 bar), with a max-hold backstop.

Grid: or_minutes ∈ {15, 30} × stop_mode ∈ {opposite, atr} × rr ∈ {none, 2}.

## C5 — `sweep_fvg` (liquidity sweep → market-structure shift → FVG; TJR/SMC-style), 5m bars

**Hypothesis (from public educational material; see `trader_analysis.md`).** Resting liquidity
above prior highs / below prior lows is "swept" around the New York open; a reversal confirmed by
a structure break and a fair-value-gap retracement continues in the new direction.
**Important:** this is an operational interpretation, not TJR's complete or endorsed system; TJR
describes his approach as discretionary and apparently applies it to index futures, not BTC.

Per New-York day *D* (bearish side; bullish is the mirror image):

1. **Levels** (all complete before 09:30 ET):
   PDH = high of NY calendar day *D−1*; Asia high = high of 20:00–24:00 ET on *D−1*;
   London high = high of 02:00–05:00 ET on *D*.
   A level is **untaken** if no price traded above it between its formation and 09:30
   (PDH and Asia: 00:00–09:30 on *D*; London: 05:00–09:30). Only untaken levels are used.
2. **Sweep:** a bar starting in [09:30, 11:30) ET has `high > level` (the highest swept level is
   used; swept levels are removed). Sweep extreme = running max high.
   **Confirmed** if a bar closes back below the level within 3 bars (incl. the sweep bar);
   otherwise the sweep failed (acceptance) and is discarded.
   The **reference swing low** = most recent *confirmed* 2-bar fractal low as of the bar before the sweep
   (a fractal at bar *j* is only known at bar *j+2*). It must lie below the level.
3. **Market-structure shift (MSS):** within 12 bars after confirmation, a bar **closes** below the
   reference swing low. Abort if a bar closes back above the swept level or the deadline passes.
4. **FVG:** the most recent bearish three-bar gap `low[k−2] > high[k]` with bars k−2…k between the
   sweep bar and the MSS bar. Zone = [high[k], low[k−2]].
5. **Entry:** sell limit at the zone's lower edge (`edge`) or midpoint (`mid`), active 12 bars,
   only if the MSS close is below the limit (non-marketable) and risk ≥ 10 bp.
6. **Stop** = sweep extreme × (1 + 5 bp). **Target** = limit − 2 × (stop − limit).
7. **Exit** at the open at 16:00 ET if neither stop nor target has filled. Max one setup per day; weekdays only.

Grid: entry ∈ {edge, mid} × rr ∈ {2, 3} × window_end ∈ {11:00, 11:30}.

Known ambiguities (each an experimental assumption): session boundaries; PDH on the calendar
day vs. the futures session; close-based (not wick) reclaim and BOS; fractal width; FVG wick-to-wick
definition; edge vs. midpoint entry; no SMT divergence filter (needs a second correlated
instrument); no daily-bias filter; no partial exits. Instrument transfer (index futures → BTC) is untested.

---

## Controls and benchmarks

| Id | Definition |
|---|---|
| Buy-and-hold | buy at the period's first open (taker + slippage), sell at its last close |
| No-trade | 0% return |
| Random-entry control | `random_entry`: per-bar entry probability matched to the candidate's signal count in the same period, random direction, stop 2×ATR14, target 2R, max hold = candidate's median hold; C4/C5 controls restricted to the same NY window, weekdays, flat at 16:00 ET; 200 seeds |
