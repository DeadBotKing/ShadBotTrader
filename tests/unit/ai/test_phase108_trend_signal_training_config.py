"""Phase 108 — service/trainer wiring for trend_signal class weights."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ShadBotTrader.application.services.dual_model_service import DualModelService
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.ai.model_roles import trend_signal_model_role

SYMBOL = Symbol("XAUUSD")
TF = Timeframe("5M")
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def candle(index: int, close: float = 100.0) -> Candle:
    return Candle(
        symbol=SYMBOL,
        timeframe=TF,
        open_time=Timestamp(BASE + timedelta(minutes=5 * index)),
        open_price=Price(Decimal(str(close))),
        high=Price(Decimal(str(close + 1))),
        low=Price(Decimal(str(close - 1))),
        close=Price(Decimal(str(close))),
        volume=Decimal("1"),
    )


def candles(count: int = 340) -> list[Candle]:
    return [candle(i, 100 + (i % 7) * 0.1) for i in range(count)]


def test_build_trainer_receives_class_weight_mode():
    service = DualModelService(include_features=False)
    role = trend_signal_model_role(timeframe="5M", window_size=16, label_horizon=4)
    dataset = service.prepare(candles(), SYMBOL, TF, role)

    trainer = service.build_trainer(dataset, class_weight_mode="auto")

    assert trainer._class_weight_mode == "auto"


def test_definition_records_class_weight_mode():
    service = DualModelService(include_features=False)
    role = trend_signal_model_role(timeframe="5M", window_size=16, label_horizon=4)
    dataset = service.prepare(candles(), SYMBOL, TF, role)

    definition = service.definition_for(role, dataset, class_weight_mode="auto")

    assert definition.hyperparameters["class_weight_mode"] == "auto"
