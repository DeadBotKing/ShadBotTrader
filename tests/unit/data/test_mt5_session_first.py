"""فاز ۹۶-ه — session-first برای MT5.

اکانت‌های OTP/گواهی‌دار (آلپاری جدید) لاگینِ برنامه‌ای پسوردی را با
(-7) رد می‌کنند حتی وقتی ترمینال لاگین است. پراوایدر باید اول نشستِ
ترمینال را ترجیح دهد و فقط بدون نشست به credential برگردد؛ پیام خطای
نهایی هم راهنمای OTP داشته باشد.
"""

from types import SimpleNamespace

import pytest

from ShadBotTrader.infrastructure.data.mt5_market_data_provider import (
    Mt5MarketDataProvider,
)

TIMEFRAMES = {
    "TIMEFRAME_M1": 1,
    "TIMEFRAME_M5": 5,
    "TIMEFRAME_M15": 15,
    "TIMEFRAME_M30": 30,
    "TIMEFRAME_H1": 16385,
    "TIMEFRAME_H4": 16388,
    "TIMEFRAME_D1": 16408,
    "TIMEFRAME_W1": 32769,
    "TIMEFRAME_MN1": 49153,
}


class _SessionFake:
    """ماکولای MT5 با کنترل نشست و نتیجهٔ لاگین برنامه‌ای."""

    def __init__(self, logged_in: bool = True, login_ok: bool = True) -> None:
        self._logged_in = logged_in
        self._login_ok = login_ok
        self.initialize_calls: list[dict] = []
        self.shutdown_calls = 0
        self.__dict__.update(TIMEFRAMES)

    def initialize(self, **kwargs) -> bool:
        self.initialize_calls.append(kwargs)
        return True  # اتصال به ترمینال همیشه ممکن است

    def shutdown(self) -> None:
        self.shutdown_calls += 1

    def terminal_info(self):
        return SimpleNamespace(name="MetaTrader 5")

    def account_info(self):
        return SimpleNamespace(login=123) if self._logged_in else None

    def last_error(self):
        return (-7, "Unsupported authorization mode, OTP or certificate password needed")

    def symbol_info(self, symbol):
        return SimpleNamespace(name=symbol)

    def symbol_select(self, symbol, visible=True):
        return True

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        return None  # «no data» بعد از اتصال — برای این تست بی‌اهمیت


def _provider(fake, **creds):
    provider = Mt5MarketDataProvider(mt5_module=fake, **creds)
    provider._initialized = False
    return provider


class TestSessionFirst:
    def test_logged_in_terminal_never_sends_credentials(self):
        fake = _SessionFake(logged_in=True)
        with pytest.raises(ConnectionError, match="no data"):
            _provider(fake, login=999, password="secret", server="Alpari-Demo").fetch_candles(
                "XAUUSD_i", "4H", "10"
            )
        assert len(fake.initialize_calls) == 1
        assert fake.initialize_calls[0] == {}  # نشست — بدون پسورد
        assert fake.shutdown_calls == 0

    def test_no_session_falls_back_to_credentials(self):
        fake = _SessionFake(logged_in=False)
        # بعد از لاگین موفق، rates=None → ConnectionError «no data» طبیعی است
        with pytest.raises(ConnectionError, match="no data"):
            _provider(fake, login=999, password="secret", server="Alpari-Demo").fetch_candles(
                "XAUUSD_i", "4H", "10"
            )
        assert fake.initialize_calls[0] == {}
        assert fake.initialize_calls[1]["login"] == 999
        assert fake.shutdown_calls == 1  # ریست بین دو تلاش

    def test_rejected_credential_login_mentions_otp(self):
        fake = _SessionFake(logged_in=False, login_ok=False)

        class _Rejecting(_SessionFake):
            def initialize(self, **kwargs):
                self.initialize_calls.append(kwargs)
                return len(self.initialize_calls) == 1  # نشست اوکی، لاگین رد

        fake = _Rejecting(logged_in=False, login_ok=False)
        with pytest.raises(ConnectionError) as excinfo:
            _provider(fake, login=999, password="secret", server="Alpari-Demo").fetch_candles(
                "XAUUSD_i", "4H", "10"
            )
        assert "OTP" in str(excinfo.value)
        assert "log the terminal in manually" in str(excinfo.value)

    def test_no_credentials_keeps_legacy_behavior(self):
        fake = _SessionFake(logged_in=False)
        with pytest.raises(ConnectionError, match="no data"):
            _provider(fake).fetch_candles("XAUUSD_i", "4H", "10")
        assert len(fake.initialize_calls) == 1  # فقط نشست — بدون fallback
