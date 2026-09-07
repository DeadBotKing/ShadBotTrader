"""فاز ۱۰۰ — ارزیابی صادقانه gold_trend_score_1d v1.

چه چیزی اندازه می‌گیریم (واقعیت، نه آرزو):
  1. MAE مدل در برابر پیش‌بینی ثابت (میانه) روی همان تاریخچه
  2. دقت جهت: آیا sign(score پیش‌بینی) با sign(score واقعی) فردا می‌خواند؟
  3. همبستگی پیش‌بینی/واقعیت — آیا هرگونه رتبه‌بندی می‌شناسد؟
  4. خروجی زندهٔ inspector (/data) برای کندل روزانهٔ بعدی — مسیر inference

    PYTHONPATH=src python scripts/evaluate_trend_score_1d.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

STORAGE = REPO_ROOT / "datasets"
MODEL_ID = "gold_trend_score_1d"
WINDOW = 150


def main() -> int:
    import numpy as np

    from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.infrastructure.ai.data_windowing import (
        input_scale_range_for_model,
        minmax_scale_window,
    )
    from ShadBotTrader.infrastructure.ai.feature_matrix import build_feature_matrix
    from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import (
        FilesystemArtifactStore,
    )
    from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue
    from ShadBotTrader.infrastructure.ai.target_builder import build_trend_score_labels
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import _deserialize_model
    from ShadBotTrader.infrastructure.data.parquet_candle_store import ParquetCandleStore

    print("=== ارزیابی gold_trend_score_1d v1 — واقعیت بدون آرایش ===")

    # ── داده و تارگت ─────────────────────────────────────────────────
    store = ParquetCandleStore(STORAGE)
    candles = store.query(Symbol("XAUUSD"), Timeframe("1D"))
    first_day = str(candles[0].open_time.value)[:10]
    last_day = str(candles[-1].open_time.value)[:10]
    print(f"candles: {len(candles):,} | {first_day} .. {last_day}")

    labels = build_trend_score_labels(candles, horizon=1)
    actual = np.array(labels.scores)
    print(
        f"targets: n={len(actual):,} | median {np.median(actual):+.4f} | stdev {actual.std():.4f}"
    )

    catalogue = ModelCatalogue(STORAGE)
    version = catalogue.latest_version(MODEL_ID)
    record = catalogue.read(MODEL_ID, version)
    if record is None:
        print("[X] model record not found")
        return 1
    artifact = FilesystemArtifactStore(STORAGE).load(
        ModelId(record.model_id), ModelVersion(record.version)
    )
    if artifact is None:
        print("[X] artifact weights missing")
        return 1
    model = _deserialize_model(artifact.payload)
    input_scale_range = input_scale_range_for_model(
        record.model_id, getattr(record, "input_scale_range", None)
    )
    print(f"model: {record.model_id} v{record.version} (trained {str(record.trained_at)[:10]})")
    print(f"input scale: [{input_scale_range[0]:+.1f}, {input_scale_range[1]:+.1f}]")

    # ── پیش‌بینی روی کل تاریخچه (window=150، stride 1) ────────────────
    from ShadBotTrader.infrastructure.feature.calculator_registry import (
        CalculatorRegistry,
    )
    from ShadBotTrader.infrastructure.feature.standard_catalog import (
        standard_feature_set_v1,
    )

    matrix = build_feature_matrix(
        candles=candles,
        symbol=Symbol("XAUUSD"),
        timeframe=Timeframe("1D"),
        feature_set=standard_feature_set_v1(),
        resolver=CalculatorRegistry(),
        include_features=True,
        causal_only=True,
        model_role="range",
    )
    rows = np.array([list(r) for r in matrix.rows], dtype=np.float32)
    index_of_row = list(matrix.source_index)
    label_row_of_candle = dict(zip(labels.source_index, range(len(labels.scores)), strict=True))

    n_windows = len(rows) - WINDOW + 1
    preds: list[float] = []
    batch = 64
    for start in range(0, n_windows, batch):
        chunk = [
            minmax_scale_window([list(r) for r in rows[w : w + WINDOW]], input_scale_range)
            for w in range(start, min(start + batch, n_windows))
        ]
        x = np.array(chunk, dtype=np.float32)
        out = model.predict(x, verbose=0)  # [b, window, 1]
        preds.extend(float(out[i, -1, 0]) for i in range(out.shape[0]))
    preds_array = np.array(preds)

    # هم‌ترازی: پنجرهٔ w به کندل index_of_row[w+WINDOW-1] ختم می‌شود؛
    # تارگت آن score کندل بعدی است → لیبل با source_index همان کندل
    pair_pred: list[float] = []
    pair_actual: list[float] = []
    for w in range(n_windows):
        candle_idx = index_of_row[w + WINDOW - 1]
        li = label_row_of_candle.get(candle_idx)
        if li is None:
            continue
        pair_pred.append(preds_array[w])
        pair_actual.append(actual[li])
    pair_pred_arr = np.array(pair_pred)
    pair_actual_arr = np.array(pair_actual)
    print(f"paired windows: {len(pair_pred_arr):,}")

    # ── 1. MAE در برابر ثابت ────────────────────────────────────────
    mae_model = float(np.mean(np.abs(pair_pred_arr - pair_actual_arr)))
    const = float(np.median(pair_actual_arr))
    mae_const = float(np.mean(np.abs(np.full_like(pair_actual_arr, const) - pair_actual_arr)))
    skill = (mae_const - mae_model) / mae_const
    print(f"\n[1] MAE model        : {mae_model:.4f}")
    print(f"    MAE const({const:+.4f}): {mae_const:.4f}  → skill {skill:+.1%}")

    # ── 2. دقت جهت ──────────────────────────────────────────────────
    print("\n[2] sign accuracy (prediction sign vs actual sign):")
    for name, mask in (
        ("all days       ", np.ones(len(pair_pred_arr), dtype=bool)),
        ("|actual| > 0.3 ", np.abs(pair_actual_arr) > 0.3),
        ("|actual| > 0.5 ", np.abs(pair_actual_arr) > 0.5),
    ):
        if mask.sum() == 0:
            continue
        hits = float(np.mean(np.sign(pair_pred_arr[mask]) == np.sign(pair_actual_arr[mask])))
        up = float(np.mean(np.sign(pair_actual_arr[mask]) == 1))
        dominant = max(up, 1.0 - up)
        print(f"    {name}: {hits:.1%}  (dominant-class base {dominant:.1%}) n={int(mask.sum()):,}")

    # ── 3. همبستگی ──────────────────────────────────────────────────
    corr = float(np.corrcoef(pair_pred_arr, pair_actual_arr)[0, 1])
    print(f"\n[3] corr(pred, actual): {corr:+.4f}")
    print(
        f"    pred spread : stdev {pair_pred_arr.std():.4f}"
        f"  (target stdev {pair_actual_arr.std():.4f})"
    )

    # ── 4. خروجی زندهٔ inspector — همان مسیر /data ───────────────────
    print("\n[4] inspector forecast (همان مسیر /data):")
    from ShadBotTrader.presentation.gateway.range_forecast_inspector import (
        RangeForecastInspector,
    )

    inspector = RangeForecastInspector(STORAGE)
    path = inspector.forecast_at(
        symbol="XAUUSD",
        timeframe="1D",
        model_id=MODEL_ID,
        bar_index=len(candles) - 1,
    )
    point = path.points[0]
    print(f"    score     : {point['score']:+.4f} → {point['direction']}")
    print(f"    close ref : {path.anchor_close:.2f}")

    if mae_model < mae_const * 0.995:
        verdict = "مدل از ثابت بهتر است — لبهٔ ضعیف ولی موجود"
    else:
        verdict = "بدون لبه — همگرا به میانگین؛ دقیقاً همان انتظار پروپوزال"
    print(f"\nVERDICT: {verdict}")
    print(
        "لبهٔ عملیاتی: فیلترهای session/trend بکتست‌شده (WR 36-49%)"
        " + این score فقط به‌عنوان گیت ثانویه."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
