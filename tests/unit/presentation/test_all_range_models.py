"""فاز ۹۶-و — لیست مدل‌های رنج /data از همهٔ تایم‌فریم‌ها.

لیست هاردکدِ 1D/1H مدل 4H تازه‌آموزش‌شده را مخفی می‌کرد؛
``all_range_models`` هر مدل رنج ذخیره‌شده را برمی‌گرداند (یک رکورد per
model_id، آخرین نسخه) و لیست دراپ‌داون هم تایم‌فریم را نشان می‌دهد.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue, ModelRecord
from ShadBotTrader.presentation.gateway.range_forecast_inspector import (
    RangeForecastInspector,
)


def _record(model_id: str, version: int, timeframe: str, horizon: int) -> ModelRecord:
    return ModelRecord(
        model_id=model_id,
        role="range",
        symbol="XAUUSD",
        timeframe=timeframe,
        version=version,
        horizon=horizon,
        trained_at=datetime(2026, 9, 1, tzinfo=timezone.utc).isoformat(),
    )


class TestAllRangeModels:
    def test_every_timeframe_appears(self, tmp_path):
        catalogue = ModelCatalogue(tmp_path)
        catalogue.write(_record("gold_range_1d", 1, "1D", 5))
        catalogue.write(_record("gold_range_4h", 1, "4H", 5))
        catalogue.write(_record("gold_range_1h", 2, "1H", 12))

        models = RangeForecastInspector(tmp_path).all_range_models()
        ids = [m["model_id"] for m in models]
        assert "gold_range_4h" in ids  # قبلاً مخفی می‌شد
        assert ids == sorted(ids)
        by_id = {m["model_id"]: m for m in models}
        assert by_id["gold_range_4h"]["timeframe"] == "4H"
        assert by_id["gold_range_1h"]["version"] == 2  # آخرین نسخه

    def test_signal_models_are_excluded(self, tmp_path):
        catalogue = ModelCatalogue(tmp_path)
        catalogue.write(
            ModelRecord(
                model_id="gold_signal_5m",
                role="signal",
                symbol="XAUUSD",
                timeframe="5M",
                horizon=5,
            )
        )
        models = RangeForecastInspector(tmp_path).all_range_models()
        assert [m["model_id"] for m in models] == []

    def test_empty_catalogue_returns_empty_list(self, tmp_path):
        assert RangeForecastInspector(tmp_path).all_range_models() == []
