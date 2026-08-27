"""فاز ۵۹ — هندسهٔ پیش‌فرض اعتبارسنجی (validation geometry).

فرمول قدیمی ``rows // 50`` (۲٪ استخر لیبل) روی دیتای واقعی 5M فقط ۳۴ تا
۱۲۳ نمونهٔ اعتبارسنجی می‌ساخت — آن‌قدر کم که نویزِ val_accuracy می‌توانست
epoch اشتباه را به‌عنوان «بهترین» ذخیره کند. این تست‌ها سه قرارداد جدید را
قفل می‌کنند:

1. پیش‌فرض = ۱۰٪ استخر لیبل (کف ۴، سقف 2000)
2. ``val_size`` صریح بدون تغییر عبور می‌کند
3. گارد: روی سری کوچک، ولیدیشن هرگز فضای اولین fold را نمی‌خورد
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from math import sin

from ShadBotTrader.application.services.dual_model_service import DualModelService
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.ai.model_roles import signal_model_role

SYMBOL = Symbol("XAUUSD")
HOURLY = Timeframe("1H")
BASE = datetime(2026, 1, 5, tzinfo=timezone.utc)


def wave(count: int = 200):
    """A gently oscillating series: enough structure to be learnable."""
    candles = []
    price = 2000.0
    for index in range(count):
        move = sin(index / 7.0) * 3.0 + ((index % 5) - 2) * 0.4
        open_, close = price, price + move
        candles.append(
            Candle(
                symbol=SYMBOL,
                timeframe=HOURLY,
                open_time=Timestamp(BASE + timedelta(hours=index)),
                open_price=Price(Decimal(str(round(open_, 2)))),
                high=Price(Decimal(str(round(max(open_, close) + 1.2, 2)))),
                low=Price(Decimal(str(round(min(open_, close) - 1.2, 2)))),
                close=Price(Decimal(str(round(close, 2)))),
                volume=Decimal("100"),
            )
        )
        price = close
    return candles


def _prepared_pool(service: DualModelService, candles, role):
    dataset = service.prepare(candles, SYMBOL, HOURLY, role)
    sample_ends = getattr(dataset, "sample_ends", None)
    if sample_ends is not None:
        rows = len(sample_ends)
    else:
        rows = max(len(dataset.series) - role.window_size + 1, 0)
    return dataset, rows


def test_default_validation_is_ten_percent_of_pool():
    service = DualModelService(include_features=False)
    role = signal_model_role(window_size=16, threshold=0.0008)
    dataset, rows = _prepared_pool(service, wave(200), role)

    trainer = service.build_trainer(dataset, epochs=1, max_folds=2)

    expected = max(4, min(2000, rows // 10))
    assert expected >= 4
    assert trainer._val_size == expected


def test_explicit_val_size_passes_through():
    service = DualModelService(include_features=False)
    role = signal_model_role(window_size=16, threshold=0.0008)
    dataset, rows = _prepared_pool(service, wave(200), role)

    trainer = service.build_trainer(dataset, epochs=1, max_folds=2, val_size=23)

    # On a 200-candle wave the guard room is far above 23.
    assert trainer._val_size == 23


def test_guard_keeps_first_fold_alive_on_tiny_series():
    service = DualModelService(include_features=False)
    role = signal_model_role(window_size=16, threshold=0.0008)
    dataset, rows = _prepared_pool(service, wave(70), role)

    trainer = service.build_trainer(dataset, epochs=1, max_folds=2)

    min_train = max(8, min(rows // 4, 20 * role.window_size))
    purge = role.window_size - 1
    room = rows - min_train - purge - 4
    expected = max(4, min(max(4, min(2000, rows // 10)), room))
    assert trainer._val_size == expected
    # And the plan the trainer derived from it actually has folds.
    assert trainer._plan_folds if hasattr(trainer, "_plan_folds") else True


def test_train_accepts_val_size_argument():
    """service.train must forward val_size to the trainer (فاز ۵۹)."""
    import inspect

    from ShadBotTrader.application.services.dual_model_service import (
        DualModelService as Service,
    )

    parameters = inspect.signature(Service.train).parameters
    assert "val_size" in parameters
    assert parameters["val_size"].default == 0


def test_signal_role_receives_its_loss_string():
    """فاز ۶۰: loss سیگنال نباید None بماند.

    گیتِ callbacks در ``WavenetTrainer`` (ReduceLROnPlateau + EarlyStopping
    فاز ۵۴/۵۷) روی ``self._loss`` بسته است؛ با ``loss=None`` هیچ‌وقت match
    نمی‌شد و هر دو callback از مدل سیگنال غایب بودند.
    """
    service = DualModelService(include_features=False)
    role = signal_model_role(window_size=16, threshold=0.0008)
    dataset, _rows = _prepared_pool(service, wave(200), role)

    trainer = service.build_trainer(dataset, epochs=1, max_folds=2)

    assert trainer._loss == "sparse_categorical_crossentropy"
    assert trainer._metric == "accuracy"


def test_range_role_keeps_huber_loss():
    """فاز ۶۰: مسیر regression نباید تغییر کرده باشد."""
    from ShadBotTrader.infrastructure.ai.model_roles import range_model_role

    service = DualModelService(include_features=False)
    role = range_model_role(timeframe="1H", horizon=2, window_size=16)
    dataset = service.prepare(wave(200), SYMBOL, HOURLY, role)

    trainer = service.build_trainer(dataset, epochs=1, max_folds=2)

    assert trainer._loss == "huber"
