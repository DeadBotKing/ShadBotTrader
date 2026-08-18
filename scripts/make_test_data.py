"""Generate a SMALL synthetic dataset for local testing (Phase 40).

The workspace deliberately ships without market data: the operator's
real MT5 history lives in their own repository, and mixing it into the
delivered archive is how two people end up training on different
"XAUUSD". But an empty workspace cannot be exercised at all, so this
script builds a miniature stand-in.

Two safeguards make the fake impossible to mistake for real data:

**It is stored under ``TESTSYM``**, not XAUUSD and not any broker alias
of it. Phase 35 forbade writing generated candles under a real symbol
for exactly this reason, and a test enforces it.

**It is tiny.** A few hundred candles per timeframe — enough to prove
the pipeline runs end to end, far too few to train anything meaningful.
Nobody will confuse a 400-candle series with nine years of gold.

    python scripts/make_test_data.py            # 5M, 1H and 1D
    python scripts/make_test_data.py --candles 800
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

#: Never a real instrument, never an alias of one.
TEST_SYMBOL = "TESTSYM"

#: Minutes per candle for each timeframe this script can build.
STEP_MINUTES = {"5M": 5, "1H": 60, "1D": 1440}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a small synthetic dataset for testing.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default=TEST_SYMBOL)
    parser.add_argument("--timeframes", default="5M,1H,1D")
    parser.add_argument("--candles", type=int, default=600)
    parser.add_argument("--storage-root", default=str(REPO_ROOT / "datasets"))
    parser.add_argument(
        "--features",
        action="store_true",
        help="also compute the feature catalogue for each timeframe",
    )
    return parser.parse_args(argv)


def build_candles(symbol: str, timeframe: str, count: int):
    """A continuous, well-formed series with a little structure in it."""
    from ShadBotTrader.domain.market.candle import Candle
    from ShadBotTrader.domain.market.price import Price
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.domain.market.timestamp import Timestamp

    minutes = STEP_MINUTES[timeframe]
    # Start far enough back that the newest candle is not in the future.
    start = datetime.now(timezone.utc).replace(
        second=0, microsecond=0, minute=0, hour=0
    ) - timedelta(minutes=minutes * count)

    out = []
    price = 2000.0
    for index in range(count):
        # A slow wave plus a faster ripple: enough variation that the
        # indicators produce something other than a straight line.
        drift = math.sin(index / 60.0) * 18.0
        ripple = math.sin(index / 7.0) * 3.0
        open_ = price
        close = 2000.0 + drift + ripple
        high = max(open_, close) + 1.6
        low = min(open_, close) - 1.6
        out.append(
            Candle(
                symbol=Symbol(symbol),
                timeframe=Timeframe(timeframe),
                open_time=Timestamp(start + timedelta(minutes=minutes * index)),
                open_price=Price(Decimal(f"{open_:.2f}")),
                high=Price(Decimal(f"{high:.2f}")),
                low=Price(Decimal(f"{low:.2f}")),
                close=Price(Decimal(f"{close:.2f}")),
                volume=Decimal(str(100 + (index % 40))),
            )
        )
        price = close
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    from ShadBotTrader.application.services.dataset_update_service import (
        DatasetUpdateService,
    )
    from ShadBotTrader.infrastructure.data.parquet_candle_store import (
        ParquetCandleStore,
    )

    root = Path(args.storage_root)
    timeframes = [item.strip().upper() for item in args.timeframes.split(",") if item.strip()]
    unknown = [item for item in timeframes if item not in STEP_MINUTES]
    if unknown:
        print(f"[X] Cannot build {', '.join(unknown)}. Known: {', '.join(STEP_MINUTES)}")
        return 1

    print("=== synthetic test data (NOT market data) ===")
    print(f"symbol {args.symbol} | {args.candles} candles per timeframe")

    store = ParquetCandleStore(root)
    for timeframe in timeframes:
        candles = build_candles(args.symbol, timeframe, args.candles)
        result = DatasetUpdateService(store).update(
            args.symbol, timeframe, candles, allow_gap=True, backfill=False
        )
        status = "REFUSED" if result.refused else f"{result.final_count:,} stored"
        print(f"  {timeframe:>3}: {status}")

    if args.features:
        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.feature_cli import _build_service
        from ShadBotTrader.infrastructure.feature.standard_catalog import (
            standard_feature_set,
        )

        for timeframe in timeframes:
            service, _, _ = _build_service(root)
            outcome = service.compute_set(
                feature_set=standard_feature_set(),
                symbol=Symbol(args.symbol),
                timeframe=Timeframe(timeframe),
                candles=store.query(Symbol(args.symbol), Timeframe(timeframe)),
                source_dataset_id=f"synthetic.{args.symbol}.{timeframe}",
                dataset_version=1,
            )
            kept = sum(1 for item in outcome.outcomes if not item.quarantined)
            print(f"  {timeframe:>3}: {kept}/{len(outcome.outcomes)} features")

    print("\nThis data is synthetic. It exercises the pipeline; it teaches")
    print("the models nothing. Real history comes from Fetch market data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
