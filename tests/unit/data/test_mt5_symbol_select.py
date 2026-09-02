"""فاز ۹۶-د — انتخاب نمونه در Market Watch قبل از هر فراخوانی داده.

MT5 اسم‌ها را case-sensitive می‌شناسد (آلپاری: ``XAUUSD_i`` با i کوچک)
و ``copy_rates`` برای نمونهٔ غایب/غلط فقط ``(-1, 'Terminal: Call
failed')`` می‌دهد. پراوایدر حالا قبل از هر fetch نمونه را انتخاب می‌کند
و در صورت نبود، خطای واضح با نزدیک‌ترین اسم‌های واقعی می‌دهد.
"""

from types import SimpleNamespace

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.infrastructure.data.mt5_market_data_provider import (
    Mt5MarketDataProvider,
)


def _fake_mt5(existing=("XAUUSD_i", "XAUUSD", "EURUSD_i")):
    """ماکولای minimal با symbol_info/symbol_select/symbols_get."""

    class _Fake:
        def __init__(self) -> None:
            self.selected: list[str] = []

        def symbol_info(self, symbol: str):
            if symbol in existing:
                return SimpleNamespace(name=symbol)
            return None

        def symbol_select(self, symbol: str, visible: bool) -> bool:
            self.selected.append(symbol)
            return True

        def symbols_get(self, pattern: str = ""):
            hits = [s for s in existing if s.replace("_", "") in pattern.replace("*", "")]
            return [SimpleNamespace(name=s) for s in hits]

        def copy_rates_range(self, symbol, timeframe, start, end):
            if symbol not in self.selected:
                raise RuntimeError("(-1, 'Terminal: Call failed')")
            return None

        def copy_rates_from_pos(self, symbol, timeframe, start, count):
            # اگر نمونه select نشده باشد — همان -1 واقعی
            if symbol not in self.selected:
                raise RuntimeError("(-1, 'Terminal: Call failed')")
            return None

        # ثابت‌هایی که _resolve_timeframe با getattr می‌خواند
        TIMEFRAME_M1 = 1
        TIMEFRAME_M5 = 5
        TIMEFRAME_M15 = 15
        TIMEFRAME_M30 = 30
        TIMEFRAME_H1 = 16385
        TIMEFRAME_H4 = 16388
        TIMEFRAME_D1 = 16408
        TIMEFRAME_W1 = 32769
        TIMEFRAME_MN1 = 49153

    return _Fake()


def _provider() -> Mt5MarketDataProvider:
    provider = Mt5MarketDataProvider(mt5_module=_fake_mt5())
    provider._initialized = True
    provider._mt5 = provider._mt5  # noqa: PLW0127 — خوانا برای تست
    return provider


class TestSelectSymbol:
    def test_valid_symbol_gets_selected_before_fetch(self):
        fake = _fake_mt5()
        provider = Mt5MarketDataProvider(mt5_module=fake)
        provider._initialized = True
        # rates=None → بعد از select، «no data» می‌آید (فیک دادهٔ واقعی
        # ندارد)؛ مهم این است که select **قبل از** copy_rates اجرا شده
        # و خطای -1 نداده است
        with pytest.raises(ConnectionError):
            provider.fetch_candles("XAUUSD_i", "4H", "100")
        assert fake.selected == ["XAUUSD_i"]

    def test_wrong_case_raises_actionable_error(self):
        fake = _fake_mt5()
        provider = Mt5MarketDataProvider(mt5_module=fake)
        provider._initialized = True
        with pytest.raises(ValidationError) as excinfo:
            provider.fetch_candles("XAUUSD_I", "4H", "100")  # i بزرگ — همان ران اپراتور
        message = str(excinfo.value)
        assert "XAUUSD_i" in message  # اسم درست پیشنهاد می‌شود
        assert "check case" in message

    def test_fetch_range_also_selects(self):
        from datetime import datetime, timezone

        fake = _fake_mt5()
        provider = Mt5MarketDataProvider(mt5_module=fake)
        provider._initialized = True
        # rates=None → بعد از select شدن ConnectionError «no data» می‌آید که
        # در این تست اهمیتی ندارد؛ فقط ترتیبِ select-before-fetch مهم است
        with pytest.raises(ConnectionError):
            provider.fetch_range(
                "XAUUSD_i",
                "4H",
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        assert fake.selected == ["XAUUSD_i"]
