"""Paper-trading entry point (simulated orders only; never real money).

Replay mode (works offline, used for validation in this environment)::

    python -m qtrade.paper_trade --config configs/paper.yaml --replay-start 2026-09-01 --replay-end 2026-10-15

Live-feed mode polls Kraken's public OHLC endpoint and trades against the
simulated exchange (requires network access to api.kraken.com)::

    python -m qtrade.paper_trade --config configs/paper.yaml --feed kraken
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd

from qtrade.config import ConfigError, load_config
from qtrade.data.bars import timeframe_minutes
from qtrade.data.pipeline import load_bars
from qtrade.execution.feeds import KrakenOHLCFeed, ReplayFeed
from qtrade.execution.kraken import KrakenPublicClient
from qtrade.execution.simulator import SimulatedExchange
from qtrade.paper import Alerter, PaperTrader
from qtrade.strategies import make_strategy


def build_trader(cfg: dict, feed_kind: str, replay_start: str | None = None, replay_end: str | None = None,
                 fresh: bool = False) -> tuple[PaperTrader, pd.DatetimeIndex | None]:
    strat = make_strategy(cfg["strategy"]["name"], cfg["strategy"].get("params", {}))
    tf = timeframe_minutes(strat.timeframe)
    pcfg = cfg["paper"]
    if fresh:
        for key in ("state_file", "exchange_state_file"):
            Path(pcfg[key]).unlink(missing_ok=True)
    ex = SimulatedExchange(cfg, float(cfg["capital"]["initial_equity"]), tf)
    warm = pd.Timedelta(minutes=tf * strat.warmup_bars * 2)
    if feed_kind == "replay":
        start = pd.Timestamp(replay_start, tz="UTC")
        bars = load_bars(strat.timeframe, cfg["data"]["clean_dir"], start=(start - warm).isoformat(), end=replay_end)
        feed = ReplayFeed(bars, tf)
        idx = bars.index
    else:
        hist = load_bars(strat.timeframe, cfg["data"]["clean_dir"])
        hist = hist[hist.index >= hist.index[-1] - warm]
        feed = KrakenOHLCFeed(KrakenPublicClient(), tf, history=hist)
        idx = None
    trader = PaperTrader(cfg, strat, feed, ex, pcfg["state_file"], Alerter(pcfg["alerts_file"]),
                         window_bars=strat.warmup_bars * 2, kill_file=pcfg.get("kill_file"),
                         exchange_state_path=pcfg["exchange_state_file"])
    return trader, idx


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--feed", choices=["replay", "kraken"])
    ap.add_argument("--replay-start")
    ap.add_argument("--replay-end")
    ap.add_argument("--fresh", action="store_true", help="discard saved paper state first")
    ap.add_argument("--max-steps", type=int, default=None, help="live-feed mode: stop after N polls")
    args = ap.parse_args(argv)
    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2
    if cfg["mode"] != "paper":
        print("paper_trade requires mode: paper", file=sys.stderr)
        return 2
    Path(cfg["paper"]["log_file"]).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s",
                        handlers=[logging.FileHandler(cfg["paper"]["log_file"]), logging.StreamHandler()])
    feed_kind = args.feed or cfg["paper"].get("feed", "replay")
    trader, idx = build_trader(cfg, feed_kind, args.replay_start, args.replay_end, args.fresh)
    if feed_kind == "replay":
        if not args.replay_start:
            print("--replay-start is required for replay mode", file=sys.stderr)
            return 2
        end = pd.Timestamp(args.replay_end, tz="UTC") if args.replay_end else idx[-1]
        reps = trader.run_replay(pd.Timestamp(args.replay_start, tz="UTC"), end, bar_index=idx)
        summary = {
            "steps": len(reps), "trades": len(trader.state["trades"]),
            "net_pnl": sum(t["net_pnl"] for t in trader.state["trades"]),
            "final_equity": trader.ex.equity(), "position": trader.ex.position(),
            "alerts": len(trader.alert.sent), "halted": trader.risk.state.halted,
        }
        print(json.dumps(summary, indent=2))
        return 0
    steps = 0
    while args.max_steps is None or steps < args.max_steps:
        rep = trader.step(pd.Timestamp.now(tz="UTC"))
        logging.info("step %s new_bars=%d actions=%s alerts=%s", rep.now, rep.new_bars, rep.actions, rep.alerts)
        steps += 1
        time.sleep(float(cfg["paper"]["poll_seconds"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
