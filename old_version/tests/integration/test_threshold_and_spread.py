"""Phase 45 — the signal threshold is a form field, and the spread is real.

Two operator requests, both about the same underlying question: what
counts as a profitable move?

    "put the threshold in the options so I can change it, and make the
     unit percent"
    "and make it read the spread from MetaTrader during live trading,
     because I checked and the spread is floating"

The second matters more than it looks. The threshold that labels a bar
BUY must exceed the round-trip cost, or the model is trained to chase
moves that cannot survive the spread. With the old hard-coded
``Decimal("4")`` on gold at 4,376, a 0.08% signal (3.50 USD) was
LOSS-MAKING by 0.50 USD before it began.
"""

from decimal import Decimal

import pytest

from ShadBotTrader.presentation.commands.commands import Command, CommandKind
from ShadBotTrader.presentation.commands.handlers import (
    descriptors,
    percent_to_fraction,
)


def field_of(kind, name, root="datasets"):
    descriptor = next(item for item in descriptors(root) if item.kind is kind)
    return next(item for item in descriptor.fields if item.name == name)


# ------------------------------------------------------- the threshold --
class TestTheThresholdIsAPercentField:
    @pytest.mark.parametrize("kind", [CommandKind.TRAIN_DUAL_MODELS, CommandKind.TRAIN_MODEL])
    def test_both_training_buttons_expose_it(self, kind, tmp_path):
        field = field_of(kind, "threshold_pct", tmp_path)

        assert field.kind == "number"

    def test_a_fresh_model_starts_at_the_platform_default(self, tmp_path):
        field = field_of(CommandKind.TRAIN_DUAL_MODELS, "threshold_pct", tmp_path)

        assert field.default == "0.08"

    def test_retraining_starts_blank_so_the_saved_threshold_can_be_inherited(self, tmp_path):
        field = field_of(CommandKind.TRAIN_MODEL, "threshold_pct", tmp_path)

        assert field.default == ""

    @pytest.mark.parametrize(
        "typed,expected",
        [
            ("0.08", 0.0008),
            ("0.15", 0.0015),
            ("0.25%", 0.0025),
            (" 1 ", 0.01),
        ],
    )
    def test_percent_becomes_a_fraction(self, typed, expected):
        """The form speaks percent; the maths speaks fractions."""
        assert percent_to_fraction(typed, 0.0008) == pytest.approx(expected)

    @pytest.mark.parametrize("bad", ["", "abc", "-1", "0"])
    def test_nonsense_falls_back_instead_of_crashing(self, bad):
        """A typo in a form must not abort an otherwise valid run."""
        assert percent_to_fraction(bad, 0.0008) == 0.0008

    def test_the_chosen_threshold_reaches_the_script(self, tmp_path, monkeypatch):
        pytest.importorskip("tensorflow")
        from ShadBotTrader.presentation.commands.handlers import AccountCommandHandlers

        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path)
        handlers._run_log_dir = tmp_path / "run_logs"
        monkeypatch.setattr(handlers, "missing_timeframes", lambda symbol: [])
        monkeypatch.setattr(
            handlers,
            "_dataset_choices_for_test",
            lambda: ["5M"],
            raising=False,
        )
        captured: dict = {}

        def fake_run(command, arguments, message, started, timeout=900):
            from ShadBotTrader.presentation.commands.commands import CommandResult

            captured["arguments"] = list(arguments)
            return CommandResult.success(command.kind, message, [], 0.0)

        monkeypatch.setattr(handlers, "_run_script", fake_run)
        monkeypatch.setattr(
            "ShadBotTrader.presentation.commands.handlers.stored_dataset_choices",
            lambda root: ["5M", "1H", "1D"],
        )

        handlers.train_dual_models(
            Command(
                CommandKind.TRAIN_DUAL_MODELS,
                {"model": "signal", "dataset": "5M", "threshold_pct": "0.15"},
            )
        )

        arguments = captured["arguments"]
        assert arguments[arguments.index("--threshold") + 1] == "0.0015"


class TestBinaryLabelsUseTheFirstPassageThreshold:
    def build(self, threshold):
        import math
        from datetime import datetime, timedelta, timezone

        from ShadBotTrader.domain.market.candle import Candle
        from ShadBotTrader.domain.market.price import Price
        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.domain.market.timestamp import Timestamp
        from ShadBotTrader.infrastructure.ai.target_builder import build_signal_labels

        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        candles = []
        price = 2000.0
        for index in range(300):
            close = price * (1 + math.sin(index / 9.0) * 0.002)
            candles.append(
                Candle(
                    symbol=Symbol("TESTSYM"),
                    timeframe=Timeframe("5M"),
                    open_time=Timestamp(base + timedelta(minutes=5 * index)),
                    open_price=Price(f"{price:.2f}"),
                    high=Price(f"{max(price, close) + 1:.2f}"),
                    low=Price(f"{min(price, close) - 1:.2f}"),
                    close=Price(f"{close:.2f}"),
                    volume=10,
                )
            )
            price = close
        return build_signal_labels(candles, horizon=5, threshold=threshold)

    def test_a_wider_threshold_changes_first_passage_sample_counts(self):
        tight = self.build(0.0008).distribution()
        wide = self.build(0.0050).distribution()

        assert set(tight) == {"sell", "buy"}
        assert set(wide) == {"sell", "buy"}
        assert tight != wide

    def test_a_zero_threshold_is_refused(self):
        from ShadBotTrader.domain.common.errors import ValidationError

        with pytest.raises(ValidationError):
            self.build(0.0)


# ----------------------------------------------------------- the spread --
class TestTheSpreadComesFromTheBroker:
    def test_the_provider_exposes_a_live_quote(self):
        from ShadBotTrader.infrastructure.data.mt5_market_data_provider import (
            Mt5MarketDataProvider,
        )

        assert hasattr(Mt5MarketDataProvider, "live_quote")

    def test_the_spread_is_the_difference_between_bid_and_ask(self):
        """Not symbol_info.spread: that is an integer snapshot."""
        from ShadBotTrader.infrastructure.data.mt5_market_data_provider import (
            Mt5MarketDataProvider,
        )

        class Tick:
            bid, ask, time = 4376.12, 4376.47, 1700000000

        class Info:
            point, digits, spread = 0.01, 2, 35

        class FakeMt5:
            def symbol_info_tick(self, symbol):
                return Tick()

            def symbol_info(self, symbol):
                return Info()

        provider = Mt5MarketDataProvider(mt5_module=FakeMt5())
        provider._initialized = True

        quote = provider.live_quote("XAUUSD")

        assert quote["spread"] == pytest.approx(0.35, abs=1e-9)
        assert quote["spread_pct"] == pytest.approx(0.35 / 4376.295, rel=1e-6)
        assert quote["spread_points"] == 35

    def test_a_missing_tick_is_a_clear_error(self):
        from ShadBotTrader.infrastructure.data.mt5_market_data_provider import (
            Mt5MarketDataProvider,
        )

        class FakeMt5:
            def symbol_info_tick(self, symbol):
                return None

            def last_error(self):
                return (1, "no tick")

        provider = Mt5MarketDataProvider(mt5_module=FakeMt5())
        provider._initialized = True

        with pytest.raises(ConnectionError, match="Market Watch"):
            provider.live_quote("XAUUSD")

    def test_a_dead_quote_is_refused(self):
        """bid=0 during a closed market must not become a zero spread."""
        from ShadBotTrader.infrastructure.data.mt5_market_data_provider import (
            Mt5MarketDataProvider,
        )

        class Tick:
            bid, ask, time = 0.0, 0.0, 0

        class FakeMt5:
            def symbol_info_tick(self, symbol):
                return Tick()

            def symbol_info(self, symbol):
                return None

            def last_error(self):
                return (2, "market closed")

        provider = Mt5MarketDataProvider(mt5_module=FakeMt5())
        provider._initialized = True

        with pytest.raises(ConnectionError, match="unusable tick"):
            provider.live_quote("XAUUSD")


class TestTheLiveLoopUsesTheBrokerSpread:
    def service(self, quote_source):
        from ShadBotTrader.application.services.live_decision_service import (
            LiveDecisionService,
        )

        return LiveDecisionService(
            symbol="XAUUSD",
            market=None,
            matrix_builder=None,
            trading_service=None,
            quote_source=quote_source,
        )

    def test_the_broker_value_is_used_when_available(self):
        class Source:
            def live_quote(self, symbol):
                return {"spread": 0.35}

        service = self.service(Source())

        assert service._current_spread() == Decimal("0.35")
        assert service.last_spread_source == "broker"

    def test_a_failure_falls_back_without_aborting_the_tick(self):
        """A missing spread is a data problem, not a reason to stop."""

        class Broken:
            def live_quote(self, symbol):
                raise ConnectionError("terminal closed")

        service = self.service(Broken())

        assert service._current_spread() == Decimal("0.35")
        assert "ConnectionError" in service.last_spread_source

    def test_no_quote_source_is_reported_honestly(self):
        service = self.service(None)

        assert service._current_spread() == Decimal("0.35")
        assert "no quote source" in service.last_spread_source

    def test_a_nonpositive_broker_spread_is_rejected(self):
        class Zero:
            def live_quote(self, symbol):
                return {"spread": 0.0}

        service = self.service(Zero())

        assert service._current_spread() == Decimal("0.35")
        assert "<= 0" in service.last_spread_source

    def test_the_old_hardcoded_four_dollar_spread_is_gone(self):
        """On gold at 4,376 it made every 0.08% signal loss-making."""
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2]
            / "src/ShadBotTrader/application/services/live_decision_service.py"
        ).read_text(encoding="utf-8")

        assert 'spread=Decimal("4")' not in source
