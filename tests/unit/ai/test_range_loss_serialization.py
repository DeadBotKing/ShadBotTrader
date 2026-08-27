"""فاز ۷۰ — باگ ۵۱: serialize/deserialize مدل رنج.

ریشه: کلاس‌های _RangeLoss/_Seq2SeqMAE داخل _build_compiled تعریف می‌شدند
(local) → custom_objects() با getattr ماژول نمی‌دیدشان → load هر مدل رنج
با «Could not locate class '_RangeLoss'» شکست می‌خورد (۸۱۱ بار در بکتست
کاربر — رنج هرگز اجرا نشد و TP/SL هیچ‌وقت رسم نشد).

قفل‌ها:
1. range_custom_objects همهٔ نام‌های تاریخی را پوشش می‌دهد
2. wavenet.custom_objects شامل آنهاست
3. get_config/from_config: round-trip instance با تنظیمات
4. انتها-به-انتها (TF): build → serialize → deserialize مدل seq2seq رنج
"""

from __future__ import annotations

import pytest

from ShadBotTrader.infrastructure.ai.wavenet.wavenet import custom_objects
from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
    range_custom_objects,
)


def test_range_custom_objects_covers_historical_names():
    mapping = range_custom_objects()
    for name in (
        "RangeLoss",
        "_RangeLoss",
        "Seq2SeqMAE",
        "_Seq2SeqMAE",
        "ShadBotTrader>RangeLoss",
        "ShadBotTrader>_RangeLoss",
        "ShadBotTrader>Seq2SeqMAE",
        "ShadBotTrader>_Seq2SeqMAE",
    ):
        assert name in mapping, name


def test_wavenet_custom_objects_includes_range_classes():
    mapping = custom_objects()
    classes = range_custom_objects()
    assert mapping["_RangeLoss"] is classes["_RangeLoss"]
    assert mapping["_Seq2SeqMAE"] is classes["_Seq2SeqMAE"]


def test_range_loss_config_round_trip():
    classes = range_custom_objects()
    loss_cls = classes["RangeLoss"]

    loss = loss_cls(seq2seq=True, delta=0.007, w_huber=2.0)
    cfg = loss.get_config()
    assert cfg["seq2seq"] is True
    assert cfg["delta"] == 0.007

    restored = loss_cls.from_config(cfg)
    assert restored._seq2seq is True
    assert restored._delta == 0.007
    assert restored._w == (2.0, 6.0, 1.0)


def test_end_to_end_serialize_deserialize_range_model():
    """سناریوی باگ ۵۱ با TF واقعی: build → save → load مدل seq2seq رنج."""
    pytest.importorskip("tensorflow")

    from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
        _build_compiled,
        _deserialize_model,
        _serialize_model,
    )

    model = _build_compiled(
        window_size=16,
        n_features=6,
        output_units=2,
        output_activation="linear",
        learning_rate=1e-3,
        seed=42,
        n_filters=8,
        n_layers_per_block=2,
        n_blocks=1,
        depth_multiplier=2,
        loss="huber",
        metric="mae",
        seq2seq=True,
        horizon=1,
    )
    payload = _serialize_model(model)
    restored = _deserialize_model(payload)
    assert restored.output_shape == (None, 16, 2)
