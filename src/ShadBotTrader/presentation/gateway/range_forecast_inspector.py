"""فاز ۸۵ — پیش‌بینی رنج برای هر کندل انتخابی روی /data.

اپراتور مدل (مثلاً gold_range_1h h12) و دیتاست را انتخاب می‌کند؛ با
کلیک روی هر کندل، ۱۲ کندل بعدیِ همان کندل به مدل داده می‌شود و مسیر
high/low آینده (بر اساس سطرهای seq2seq) برگردانده می‌شود.

علیت: پنجره فقط کندل‌های [index-149 .. index] را می‌بیند — هیچ چیزی
بعد از کندل انتخابی. برچسب‌های آینده ساخته نمی‌شوند.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe


@dataclass
class RangeForecastPath:
    """مسیر قیمتِ پیش‌بینی‌شده برای horizon کندل بعد از یک کندل انتخابی."""

    model_id: str
    model_version: int
    timeframe: str
    horizon: int
    anchor_time: str
    anchor_close: float
    reference_close: float  # closeِ آخرین کندلِ پنجره (= کندل انتخابی)
    points: List[Dict[str, Any]] = field(default_factory=list)
    # هر نقطه: {"k": 1..horizon, "high": $, "low": $}
    # فاز ۹۵: برای مدل ATR هر نقطه high_atr_mult/low_atr_mult هم دارد
    warning: str = ""
    # فاز ۹۵: واحد تارگت مدل ("pct" یا "atr") و ATR مرجع
    target_units: str = "pct"
    atr_reference: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_version": self.model_version,
            "timeframe": self.timeframe,
            "horizon": self.horizon,
            "anchor_time": self.anchor_time,
            "anchor_close": self.anchor_close,
            "reference_close": self.reference_close,
            "points": self.points,
            "warning": self.warning,
            "target_units": self.target_units,
            "atr_reference": self.atr_reference,
        }


class RangeForecastInspector:
    """Loads one saved range model and forecasts from any stored bar."""

    def __init__(self, storage_root: str | Path = "datasets") -> None:
        self._root = Path(storage_root)
        self._predictor: Any = None
        self._predictor_key: tuple | None = None
        self._feature_set: Any = None
        self._resolver: Any = None

    # ------------------------------------------------------------- models --
    def available_models(self, timeframe: str) -> List[Dict[str, Any]]:
        """Every stored range model for ``timeframe`` (id + horizon)."""
        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        catalogue = ModelCatalogue(self._root)
        out: List[Dict[str, Any]] = []
        for record in catalogue.list_all():
            if record is None or record.role != "range":
                continue
            if (record.timeframe or "").upper() != timeframe.upper():
                continue
            out.append(
                {
                    "model_id": record.model_id,
                    "version": record.version,
                    "horizon": int(record.horizon or 1),
                    "trained_at": (record.trained_at or "")[:10],
                }
            )
        # یک رکورد per model_id (آخرین نسخه)
        seen: Dict[str, Dict[str, Any]] = {}
        for item in sorted(out, key=lambda i: (i["model_id"], i["version"])):
            seen[item["model_id"]] = item
        return sorted(seen.values(), key=lambda item: item["model_id"])

    def all_range_models(self, timeframe: str = "") -> List[Dict[str, Any]]:
        """فاز ۹۶-و/۹۸/۹۸-ب: مدل‌های رنج و ترند، فیلترشده بر اساس تایم‌فریم.

        ``timeframe`` خالی = همه؛ مقدار (مثل ``5M``) = فقط مدل‌های
        هم‌تایم‌فریم — مدل روی سری ناهم‌تایم‌فریم بی‌معناست و خروجی
        ثابت/بی‌ربط می‌دهد (اجرای واقعی: trend_score_5m روی 1D).
        """
        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        tf_upper = timeframe.strip().upper() if timeframe else ""
        catalogue = ModelCatalogue(self._root)
        out: List[Dict[str, Any]] = []
        for record in catalogue.list_all():
            if record is None:
                continue
            is_trend = record.model_id.startswith("gold_trend_")
            if not is_trend and record.role != "range":
                continue
            record_tf = (record.timeframe or "").upper()
            if tf_upper and record_tf != tf_upper:
                continue  # فقط مدل‌های هم‌تایم‌فریم با سری فعال
            kind = "trend" if is_trend else "range"
            out.append(
                {
                    "model_id": record.model_id,
                    "version": record.version,
                    "horizon": int(record.horizon or 1),
                    "trained_at": (record.trained_at or "")[:10],
                    "timeframe": record_tf,
                    "kind": kind,
                }
            )
        seen: Dict[str, Dict[str, Any]] = {}
        for item in sorted(out, key=lambda i: (i["model_id"], i["version"])):
            seen[item["model_id"]] = item
        return sorted(seen.values(), key=lambda item: item["model_id"])

    # ---------------------------------------------------------- forecast --
    def forecast_at(
        self,
        symbol: str,
        timeframe: str,
        model_id: str,
        bar_index: int,
        chart_candles: int = 500,
    ) -> RangeForecastPath:
        """Predict the next ``horizon`` bars after the bar at ``bar_index``.

        ``bar_index`` is the global index inside the stored series (the
        same index the /data chart exposes as ``i``).
        """
        from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
        from ShadBotTrader.infrastructure.ai.dual_predictor import RangePredictor
        from ShadBotTrader.infrastructure.ai.feature_matrix import build_feature_matrix
        from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import (
            FilesystemArtifactStore,
        )
        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue
        from ShadBotTrader.infrastructure.data.parquet_candle_store import (
            ParquetCandleStore,
        )

        catalogue = ModelCatalogue(self._root)
        version = catalogue.latest_version(model_id)
        record = catalogue.read(model_id, version) if version else None
        if record is None:
            raise ValidationError(f"No saved model called {model_id!r}.")

        horizon = max(int(record.horizon or 1), 1)
        window_size = int(record.window_size or 150)

        store = ParquetCandleStore(self._root)
        candles = store.query(Symbol(symbol), Timeframe(timeframe))
        candles = sorted(candles, key=lambda c: c.open_time.value)

        if bar_index < window_size - 1 or bar_index >= len(candles):
            raise ValidationError(
                f"Bar index {bar_index} needs at least {window_size} previous "
                f"candles and must exist (stored: {len(candles)})."
            )

        anchor = candles[bar_index]
        out = RangeForecastPath(
            model_id=record.model_id,
            model_version=record.version,
            timeframe=record.timeframe or timeframe,
            horizon=horizon,
            anchor_time=str(anchor.open_time.value),
            anchor_close=float(anchor.close.amount),
            reference_close=float(anchor.close.amount),
        )

        # باگ ۵۶ (فاز ۹۰): پنجره باید شامل warmup فیچرها هم باشد.
        # build_feature_matrix سطرهای warm-up را حذف می‌کند؛ پس اگر فقط
        # window_size کندل بدهیم، بعد از حذف warmup کمتر از window_size
        # سطر می‌ماند (اجرای کاربر: 73 از 150). راه: پنجرهٔ گسترش‌یافته
        # = window_size + 400 (پوشش EMA200 و طولانی‌ترین فیچر) — بعد
        # از build، از انتها window_size سطر برمی‌داریم.
        WARMUP_PAD = 400
        window_candles = candles[max(0, bar_index - window_size + 1 - WARMUP_PAD) : bar_index + 1]
        if len(window_candles) < window_size:
            raise ValidationError("not enough candles for one window")

        feature_set = self._feature_set
        resolver = self._resolver
        if feature_set is None:
            from ShadBotTrader.infrastructure.feature.calculator_registry import (
                CalculatorRegistry,
            )
            from ShadBotTrader.infrastructure.feature.standard_catalog import (
                standard_feature_set_v1,
            )

            feature_set = standard_feature_set_v1()
            resolver = CalculatorRegistry()
            self._feature_set = feature_set
            self._resolver = resolver

        matrix = build_feature_matrix(
            candles=window_candles,
            symbol=Symbol(symbol),
            timeframe=Timeframe(timeframe),
            feature_set=feature_set,
            resolver=resolver,
            include_features=True,
            causal_only=True,
            model_role="range",
        )
        if len(matrix) < window_size:
            raise ValidationError(
                f"Feature matrix has {len(matrix)} rows even after warmup pad; "
                f"model needs {window_size}."
            )

        artifact = FilesystemArtifactStore(self._root).load(
            ModelId(record.model_id), ModelVersion(record.version)
        )
        if artifact is None:
            raise ValidationError(f"weights for {record.model_id} v{record.version} missing")

        predictor = RangePredictor(
            horizon=horizon,
            timeframe=record.timeframe or timeframe,
            target_units=getattr(record, "target_units", "pct") or "pct",
        )
        window_rows = [list(row) for row in matrix.rows[-window_size:]]

        # فاز ۹۵: مدل ATR برای تبدیل ضرایب به قیمت به ATR(14) همان کندل
        # نیاز دارد — فقط از تاریخچهٔ تا کندل انتخابی (علیت).
        target_units = predictor.target_units
        atr_reference_value = 0.0
        if target_units == "atr":
            from ShadBotTrader.infrastructure.ai.target_builder import atr_from_candles

            atr_value = atr_from_candles(candles[: bar_index + 1], period=14)
            if atr_value is None or atr_value <= 0:
                raise ValidationError(
                    "ATR(14) is not available at the selected candle; cannot "
                    "convert the ATR-unit forecast into prices"
                )
            atr_reference_value = float(atr_value)
        out.target_units = target_units
        out.atr_reference = atr_reference_value

        # ‼️ برای گرفتن کل مسیر (نه فقط worst-case) از خروجی خام استفاده می‌کنیم
        model = predictor._load(artifact) if hasattr(predictor, "_load") else None
        if model is None:
            from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
                _deserialize_model,
            )

            model = _deserialize_model(artifact.payload)

        import numpy as np

        from ShadBotTrader.infrastructure.ai.data_windowing import minmax_scale_window

        x = np.array([minmax_scale_window(window_rows)], dtype=np.float32)
        raw = model.predict(x, verbose=0)[0]  # [window, horizon*2]
        if raw.ndim != 2 or raw.shape[0] < 2:
            raise ValidationError(f"Unexpected model output shape {raw.shape}")
        n_pairs = raw.shape[-1] // 2

        last_step = raw[-1]
        reference = float(anchor.close.amount)

        for k in range(horizon):
            raw_high = float(last_step[k * 2])
            raw_low = float(last_step[k * 2 + 1])
            if target_units == "atr":
                # فاز ۹۵: خروجی مدل ضرایب ATR است — قیمت = close + mult×ATR
                high_price = reference + raw_high * atr_reference_value
                low_price = reference + raw_low * atr_reference_value
                high_off = raw_high * atr_reference_value / reference
                low_off = raw_low * atr_reference_value / reference
                out.points.append(
                    {
                        "k": k + 1,
                        "high": high_price,
                        "low": low_price,
                        "high_offset": high_off,
                        "low_offset": low_off,
                        "high_atr_mult": raw_high,
                        "low_atr_mult": raw_low,
                    }
                )
            else:
                out.points.append(
                    {
                        "k": k + 1,
                        "high": reference * (1.0 + raw_high),
                        "low": reference * (1.0 + raw_low),
                        "high_offset": raw_high,
                        "low_offset": raw_low,
                    }
                )

        if horizon > n_pairs:
            out.warning = f"model outputs {n_pairs} steps but record horizon is {horizon}"
        return out
