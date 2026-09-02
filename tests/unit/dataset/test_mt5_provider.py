"""Tests for the MetaTrader 5 provider.

The real ``MetaTrader5`` package is Windows-only and needs a running
terminal, so these tests drive the adapter through a fake module that
mimics the parts of the API it uses. That is enough to verify the
mapping, the error handling and the port compliance — which is where
the bugs would actually be.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.dataset.ports import MarketDataProvider
from ShadBotTrader.infrastructure.data.mt5_market_data_provider import (
    Mt5MarketDataProvider,
    supported_timeframes,
)


class FakeRate(dict):
    """One MT5 rate row (the real API yields a numpy structured row)."""


def make_rate(
    time: int = 1_700_000_000,
    open_: float = 2000.0,
    high: float = 2005.0,
    low: float = 1995.0,
    close: float = 2002.0,
    tick_volume: int = 150,
    spread: int = 12,
    real_volume: int = 0,
) -> FakeRate:
    return FakeRate(
        time=time,
        open=open_,
        high=high,
        low=low,
        close=close,
        tick_volume=tick_volume,
        spread=spread,
        real_volume=real_volume,
    )


class FakeSymbol:
    def __init__(self, name: str) -> None:
        self.name = name


class FakeAccount:
    login = 12345
    server = "Broker-Demo"
    currency = "USD"
    balance = 10000.0
    equity = 10250.0
    leverage = 100
    trade_mode = 0


class FakeMt5:
    """A stand-in for the MetaTrader5 module."""

    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_H1 = 16385
    TIMEFRAME_D1 = 16408

    def __init__(self, rates=None, symbols=None, initialize_ok=True, logged_in=True):
        self._rates = rates if rates is not None else [make_rate()]
        self._symbols = (
            symbols
            if symbols is not None
            else [
                FakeSymbol("XAUUSD"),
                FakeSymbol("EURUSD"),
            ]
        )
        self._initialize_ok = initialize_ok
        self._logged_in = logged_in
        self.initialize_calls = []
        self.shutdown_calls = 0
        self.last_request = None

    # -- API surface the adapter uses ------------------------------------
    def initialize(self, **kwargs):
        self.initialize_calls.append(kwargs)
        return self._initialize_ok

    def shutdown(self):
        self.shutdown_calls += 1

    def last_error(self):
        return (-1, "fake error")

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        self.last_request = ("from_pos", symbol, timeframe, start, count)
        return self._rates

    def copy_rates_range(self, symbol, timeframe, start, end):
        self.last_request = ("range", symbol, timeframe, start, end)
        return self._rates

    def symbols_get(self, pattern=None):
        self.last_request = ("symbols", pattern)
        return self._symbols

    def symbol_info(self, symbol):
        # فاز ۹۶-د: این فیک برای تستِ mapping نرخ‌هاست، پس هر اسمی را
        # «شناخته‌شده» فرض می‌کند؛ رفتار نمونهٔ ناشناخته در
        # tests/unit/data/test_mt5_symbol_select.py پوشش داده شده است.
        for item in self._symbols:
            if item.name == symbol:
                return item
        return type("Info", (), {"name": symbol})()

    def symbol_select(self, symbol, visible=True):
        self.last_request = ("select", symbol, visible)
        return True

    def account_info(self):
        # فاز ۹۶-ه: None یعنی ترمینال لاگین نیست (نشست زنده نیست)
        return FakeAccount() if self._logged_in else None

    def terminal_info(self):
        return SimpleNamespace(name="MetaTrader 5", data_path="C:/MT5")


def provider(mt5=None, **kwargs) -> Mt5MarketDataProvider:
    return Mt5MarketDataProvider(mt5_module=mt5 or FakeMt5(), **kwargs)


# ------------------------------------------------------------- contract ---
class TestPortCompliance:
    def test_implements_the_market_data_provider_port(self):
        """The whole point: the platform sees a MarketDataProvider."""
        assert isinstance(provider(), MarketDataProvider)

    def test_provider_name_is_stable(self):
        assert provider().provider_name == "mt5"

    def test_returns_raw_records_without_transforming(self):
        """Per the port contract, a provider must not validate or convert."""
        records = provider().fetch_candles("XAUUSD", "5M", "10")
        record = records[0]
        # every core field is a string: raw means raw
        assert isinstance(record.open, str)
        assert isinstance(record.volume, str)


# -------------------------------------------------------------- mapping ---
class TestRateMapping:
    def test_maps_every_candle_field(self):
        rate = make_rate(open_=1.5, high=2.5, low=0.5, close=2.0, tick_volume=42)
        records = provider(FakeMt5(rates=[rate])).fetch_candles("EURUSD", "5M", "1")

        assert len(records) == 1
        record = records[0]
        assert record.symbol == "EURUSD"
        assert record.timeframe == "5M"
        assert record.open == "1.5"
        assert record.high == "2.5"
        assert record.low == "0.5"
        assert record.close == "2.0"

    def test_uses_tick_volume_as_the_volume(self):
        """Retail FX reports tick volume; real_volume is usually zero."""
        rate = make_rate(tick_volume=987, real_volume=0)
        record = provider(FakeMt5(rates=[rate])).fetch_candles("X", "5M", "1")[0]
        assert record.volume == "987"

    def test_timestamp_is_utc_iso(self):
        rate = make_rate(time=1_700_000_000)
        record = provider(FakeMt5(rates=[rate])).fetch_candles("X", "5M", "1")[0]
        parsed = datetime.fromisoformat(record.timestamp)
        assert parsed.tzinfo is not None
        assert parsed == datetime.fromtimestamp(1_700_000_000, tz=timezone.utc)

    def test_broker_extras_are_preserved(self):
        """Nothing the broker sent may be silently dropped."""
        rate = make_rate(spread=27, real_volume=1234)
        record = provider(FakeMt5(rates=[rate])).fetch_candles("X", "5M", "1")[0]
        assert record.extra["spread"] == 27
        assert record.extra["real_volume"] == 1234
        assert record.extra["provider"] == "mt5"

    def test_timeframe_is_normalised_to_upper_case(self):
        record = provider().fetch_candles("X", "5m", "1")[0]
        assert record.timeframe == "5M"


# ------------------------------------------------------------ timeframes ---
class TestTimeframeTranslation:
    def test_known_timeframes_translate(self):
        mt5 = FakeMt5()
        provider(mt5).fetch_candles("X", "5M", "10")
        assert mt5.last_request[2] == FakeMt5.TIMEFRAME_M5

        provider(mt5).fetch_candles("X", "1H", "10")
        assert mt5.last_request[2] == FakeMt5.TIMEFRAME_H1

    def test_aliases_are_accepted(self):
        mt5 = FakeMt5()
        provider(mt5).fetch_candles("X", "D1", "10")
        assert mt5.last_request[2] == FakeMt5.TIMEFRAME_D1

    def test_unknown_timeframe_is_rejected_with_guidance(self):
        with pytest.raises(ValidationError, match="Unsupported timeframe"):
            provider().fetch_candles("X", "7M", "10")

    def test_supported_timeframes_are_listed(self):
        names = supported_timeframes()
        assert "5M" in names and "1H" in names and "1D" in names


# ------------------------------------------------------------- requests ---
class TestRequests:
    def test_bar_count_comes_from_source(self):
        mt5 = FakeMt5()
        provider(mt5).fetch_candles("XAUUSD", "5M", "2500")
        assert mt5.last_request[0] == "from_pos"
        assert mt5.last_request[4] == 2500

    def test_non_numeric_bar_count_is_rejected(self):
        with pytest.raises(ValidationError, match="bar count"):
            provider().fetch_candles("X", "5M", "many")

    def test_zero_bars_is_rejected(self):
        with pytest.raises(ValidationError, match="Bar count"):
            provider().fetch_candles("X", "5M", "0")

    def test_fetch_range_converts_to_naive_utc(self):
        """MT5 expects naive datetimes; a tz-aware one would shift the window."""
        mt5 = FakeMt5()
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 2, 1, tzinfo=timezone.utc)
        provider(mt5).fetch_range("XAUUSD", "5M", start, end)

        _, _, _, sent_start, sent_end = mt5.last_request
        assert sent_start.tzinfo is None
        assert sent_end.tzinfo is None
        assert sent_start == datetime(2026, 1, 1)

    def test_inverted_range_is_rejected(self):
        start = datetime(2026, 2, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValidationError, match="end must be after start"):
            provider().fetch_range("X", "5M", start, end)


# --------------------------------------------------------- failure modes ---
class TestFailureHandling:
    def test_failed_initialisation_raises_a_clear_error(self):
        broken = FakeMt5(initialize_ok=False)
        with pytest.raises(ConnectionError, match="Could not connect"):
            provider(broken).fetch_candles("X", "5M", "10")

    def test_none_result_is_a_connection_error(self):
        """MT5 returns None on failure — that is not an empty dataset."""
        mt5 = FakeMt5(rates=None)
        mt5._rates = None
        with pytest.raises(ConnectionError, match="returned no data"):
            provider(mt5).fetch_candles("X", "5M", "10")

    def test_empty_result_is_an_error_not_a_silent_success(self):
        """Ingesting zero bars would look like a successful run."""
        with pytest.raises(ValidationError, match="zero bars"):
            provider(FakeMt5(rates=[])).fetch_candles("MISSING", "5M", "10")

    def test_error_message_mentions_market_watch(self):
        """The usual cause is a symbol hidden in Market Watch."""
        with pytest.raises(ValidationError, match="Market Watch"):
            provider(FakeMt5(rates=[])).fetch_candles("X", "5M", "10")


# ------------------------------------------------------------- lifecycle ---
class TestLifecycle:
    def test_initialises_once_and_reuses_the_session(self):
        mt5 = FakeMt5()
        instance = provider(mt5)
        instance.fetch_candles("X", "5M", "10")
        instance.fetch_candles("X", "5M", "10")
        assert len(mt5.initialize_calls) == 1

    def test_credentials_are_forwarded_when_no_session(self):
        """فاز ۹۶-ه: نشست زنده نیست → لاگین برنامه‌ای با credential."""
        mt5 = FakeMt5(logged_in=False)
        instance = Mt5MarketDataProvider(
            login=999, password="secret", server="Broker-X", mt5_module=mt5
        )
        instance.fetch_candles("X", "5M", "10")
        assert mt5.initialize_calls[0] == {}  # اول تلاش برای نشست
        sent = mt5.initialize_calls[1]
        assert sent["login"] == 999
        assert sent["server"] == "Broker-X"

    def test_live_session_beats_saved_credentials(self):
        """ترمینال لاگین است → credential اصلاً فرستاده نمی‌شود (اکانت OTP)."""
        mt5 = FakeMt5(logged_in=True)
        instance = Mt5MarketDataProvider(
            login=999, password="secret", server="Broker-X", mt5_module=mt5
        )
        instance.fetch_candles("X", "5M", "10")
        assert len(mt5.initialize_calls) == 1
        assert mt5.initialize_calls[0] == {}

    def test_no_credentials_uses_the_existing_session(self):
        """Avoids putting a password anywhere near the codebase."""
        mt5 = FakeMt5()
        provider(mt5).fetch_candles("X", "5M", "10")
        assert mt5.initialize_calls[0] == {}

    def test_context_manager_shuts_down(self):
        mt5 = FakeMt5()
        with Mt5MarketDataProvider(mt5_module=mt5) as instance:
            instance.fetch_candles("X", "5M", "10")
        assert mt5.shutdown_calls == 1

    def test_shutdown_is_safe_before_connecting(self):
        Mt5MarketDataProvider(mt5_module=FakeMt5()).shutdown()


# ---------------------------------------------------------------- extras ---
def test_available_symbols_are_sorted():
    mt5 = FakeMt5(symbols=[FakeSymbol("EURUSD"), FakeSymbol("AUDUSD")])
    assert provider(mt5).available_symbols() == ["AUDUSD", "EURUSD"]


def test_account_summary_exposes_the_essentials():
    summary = provider().account_summary()
    assert summary["login"] == 12345
    assert summary["currency"] == "USD"
    assert summary["balance"] == 10000.0


def test_multiple_rates_preserve_their_order():
    rates = [make_rate(time=1_700_000_000 + index * 300) for index in range(5)]
    records = provider(FakeMt5(rates=rates)).fetch_candles("X", "5M", "5")
    stamps = [record.timestamp for record in records]
    assert stamps == sorted(stamps)
    assert len(records) == 5
