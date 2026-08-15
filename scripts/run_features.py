"""Demo run of the Feature Platform without installing the package.

Ingests a sample dataset (via the Data Platform) if needed, then computes
the standard FX feature set over it and prints a summary:

    python scripts/run_features.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ShadBotTrader.application.services.feature_computation_service import (  # noqa: E402
    FeatureComputationService,
)
from ShadBotTrader.core.events.event_bus import EventBus  # noqa: E402
from ShadBotTrader.data_cli import build_service as build_data_service  # noqa: E402
from ShadBotTrader.data_cli import generate_sample  # noqa: E402
from ShadBotTrader.domain.market.symbol import Symbol  # noqa: E402
from ShadBotTrader.domain.market.timeframe import Timeframe  # noqa: E402
from ShadBotTrader.infrastructure.feature.calculator_registry import (  # noqa: E402
    CalculatorRegistry,
)
from ShadBotTrader.infrastructure.feature.in_memory_feature_registry import (  # noqa: E402
    InMemoryFeatureRegistry,
)
from ShadBotTrader.infrastructure.feature.parquet_feature_store import (  # noqa: E402
    ParquetFeatureStore,
)
from ShadBotTrader.infrastructure.feature.standard_catalog import (  # noqa: E402
    standard_feature_set_v1,
)

SYMBOL = "XAUUSD_i"
TIMEFRAME = "5M"
ROWS = 300


def main() -> int:
    storage_root = REPO_ROOT / "datasets"
    sample_path = storage_root / "samples" / f"{SYMBOL}_{TIMEFRAME}.csv"

    # 1) اطمینان از وجود داده (Data Platform)
    if not sample_path.exists():
        generate_sample(SYMBOL, TIMEFRAME, ROWS, sample_path)
    data_service, candle_store, _ = build_data_service(storage_root)
    candles = candle_store.query(Symbol(SYMBOL), Timeframe(TIMEFRAME))
    if not candles:
        data_service.ingest(SYMBOL, TIMEFRAME, str(sample_path))
        candles = candle_store.query(Symbol(SYMBOL), Timeframe(TIMEFRAME))

    print("=== Feature Platform demo ===")
    print(f"Computing {standard_feature_set_v1().name} over {len(candles)} candles ...")

    # 2) محاسبه‌ی فیچرها
    store = ParquetFeatureStore(storage_root)
    registry = InMemoryFeatureRegistry()
    event_bus = EventBus()
    computed_events: list = []
    event_bus.subscribe("FeatureComputed", lambda e: computed_events.append(e))
    service = FeatureComputationService(
        calculator_resolver=CalculatorRegistry(),
        registry=registry,
        repository=store,
        event_bus=event_bus,
    )

    result = service.compute_set(
        feature_set=standard_feature_set_v1(),
        symbol=Symbol(SYMBOL),
        timeframe=Timeframe(TIMEFRAME),
        candles=candles,
        source_dataset_id=f"csv.market_candle.{SYMBOL}.{TIMEFRAME}.L3_normalized",
        dataset_version=1,
    )

    print(f"\nFeature set: {result.set_name}")
    print(f"Symbol/timeframe: {result.symbol} {result.timeframe}")
    print(f"Computed features: {sum(1 for o in result.outcomes if not o.quarantined)}")
    print(f"Quarantined: {len(result.quarantined_ids)}")
    print()
    for outcome in result.outcomes:
        status = "QUARANTINED" if outcome.quarantined else f"v{outcome.version}"
        live = "live" if outcome.live_compatible else "research"
        print(
            f"  {outcome.feature_id:<20} {status:<12} "
            f"available={outcome.available_count:<5} score={outcome.quality.score.overall} [{live}]"
        )

    # 3) نمونه‌ی خروجی یک فیچر
    sma = store.load("sma_20", 1)
    if sma:
        available = [p for p in sma.points if p.value is not None]
        first, last = available[0], available[-1]
        print(f"\nSample sma_20: first={first.value:.4f} last={last.value:.4f}")
    print("\nFeature Platform demo finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
