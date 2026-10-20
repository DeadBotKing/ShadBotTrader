"""فاز ۱۰۰ — دیتاست واقعی 1D برای آموزش gold_trend_score_1d.

منبع: Yahoo Finance — فیوچرز طلای COMEX (GC=F)، کندل روزانه، ~10 سال.
چرا GC=F: نزدیک‌ترین سری آزاد به XAUUSD spot (basis چند دلاری)؛
MT5/Alpari دسترس‌پذیر نیست داخل سندباکس. اپراتور می‌تواند با دیتای
MT5 خودش بازآموزی بدهد — سیم‌کشی فاز ۱۰۰ همین حالا پشتیبانی می‌کند.

مهم (کد = واقعیت): این دیتا از فیوچرز است نه spot MT5 — در گزارش و
WORKLOG مستند می‌شود. مدل v1 در سندباکس با همین دیتا آموزش می‌بیند.

    python scripts/fetch_1d_gold_yahoo.py            # همه‌ی تاریخچه
    python scripts/fetch_1d_gold_yahoo.py --years 10
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

YAHOO_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    "?interval=1d&range={range}"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch REAL daily gold candles (Yahoo GC=F) into the candle store."
    )
    parser.add_argument("--symbol", default="XAUUSD", help="store symbol name")
    parser.add_argument("--range", default="10y", help="Yahoo range (10y = max useful)")
    parser.add_argument("--storage-root", default=str(REPO_ROOT / "datasets"))
    return parser.parse_args(argv)


def fetch_yahoo_daily(symbol: str, rng: str) -> list[dict]:
    url = YAHOO_URL.format(symbol=urllib.parse.quote(symbol), range=rng)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    result = (payload.get("chart", {}).get("result") or [None])[0]
    if result is None:
        error = payload.get("chart", {}).get("error")
        raise RuntimeError(f"Yahoo returned no data: {error}")
    timestamps = result.get("timestamp") or []
    quote = result["indicators"]["quote"][0]
    rows: list[dict] = []
    for index, stamp in enumerate(timestamps):
        values = {key: quote[key][index] for key in ("open", "high", "low", "close", "volume")}
        # ردیف خراب (null یا صفر در OHLC) — بورس گاهی ردیف خالی می‌دهد
        if any(values[key] is None or float(values[key]) <= 0 for key in ("open", "high", "low", "close")):
            continue
        rows.append(
            {
                "time": datetime.fromtimestamp(int(stamp), tz=timezone.utc),
                "open": float(values["open"]),
                "high": float(values["high"]),
                "low": float(values["low"]),
                "close": float(values["close"]),
                "volume": float(values["volume"] or 0.0),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print("=== REAL daily gold candles — Yahoo COMEX GC=F (NOT MT5 spot) ===")
    rows = fetch_yahoo_daily("GC=F", args.range)
    if not rows:
        print("[X] no usable rows")
        return 1
    print(
        f"  fetched : {len(rows):,} candles | "
        f"{rows[0]['time'].date()} .. {rows[-1]['time'].date()}"
    )

    from ShadBotTrader.application.services.dataset_update_service import (
        DatasetUpdateService,
    )
    from ShadBotTrader.domain.market.candle import Candle
    from ShadBotTrader.domain.market.price import Price
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.domain.market.timestamp import Timestamp
    from ShadBotTrader.infrastructure.data.parquet_candle_store import (
        ParquetCandleStore,
    )

    candles = [
        Candle(
            symbol=Symbol(args.symbol),
            timeframe=Timeframe("1D"),
            open_time=Timestamp(row["time"]),
            open_price=Price(Decimal(f"{row['open']:.2f}")),
            high=Price(Decimal(f"{row['high']:.2f}")),
            low=Price(Decimal(f"{row['low']:.2f}")),
            close=Price(Decimal(f"{row['close']:.2f}")),
            volume=Decimal(f"{row['volume']:.0f}"),
        )
        for row in rows
    ]
    store = ParquetCandleStore(Path(args.storage_root))
    result = DatasetUpdateService(store).update(
        args.symbol, "1D", candles, allow_gap=True, backfill=False
    )
    if result.refused:
        print(f"[X] store refused the update: {result.refusal_reason}")
        return 1
    print(f"  stored  : {result.final_count:,} candles → {args.symbol}/1D")

    # آمار تارگت score روی همین دیتا — قبل از آموزش باید دیده شود
    from ShadBotTrader.infrastructure.ai.target_builder import build_trend_score_labels

    labels = build_trend_score_labels(candles, horizon=1)
    scores = labels.scores
    n = len(scores)
    ordered = sorted(scores)
    median = ordered[n // 2]
    mean = sum(scores) / n
    stdev = (sum((s - mean) ** 2 for s in scores) / n) ** 0.5
    above = sum(1 for s in scores if abs(s) > 0.5)
    print(f"  score target (next real 1D candle): n={n:,}")
    print(
        f"    median {median:+.4f} · stdev {stdev:.4f} · "
        f"|score|>0.5: {above:,} ({above / n:.1%})"
    )
    print("PROVENANCE: Yahoo Finance GC=F daily — NOT broker XAUUSD spot (sandbox)")
    return 0


if __name__ == "__main__":
    import urllib.parse

    sys.exit(main())
