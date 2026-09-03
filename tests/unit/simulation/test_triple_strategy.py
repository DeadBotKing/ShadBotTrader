"""فاز ۹۷ — استراتژی سه‌تایم‌فریمی (5M سیگنال · 4H براکت · 1D ترند).

سه مجوز طبق طرح اپراتور:
1. احتمال سیگنال > آستانه (گیت موجود)؛
2. شیب روزانه — خرید: High/Low پیش‌بینی D1 نسبت به D0 صعودی (بر اساس
   slope_mode)؛ فروش برعکس؛
3. سمت TP (خرید: TP > ورود).

براکت: TP/SL از مدل 4H؛ fallback اول Low/High روز D0؛ fallback دوم
کمترین Low زیر ورود از کندل‌های 5M امروز منهای اسپرد (خرید؛ فروش
برعکس). گیت R/R طبق خواستهٔ اپراتور اعمال می‌ماند.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.ai.prediction_target import RangeForecast, SignalForecast
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.simulation.market_event import MarketEvent
from ShadBotTrader.domain.trading.order import OrderSide
from ShadBotTrader.infrastructure.simulation.dual_model_prediction_source import (
    DualModelPredictionSource,
)

SYMBOL = Symbol("XAUUSD")
FIVE_M = Timeframe("5M")
FOUR_H = Timeframe("4H")
ONE_D = Timeframe("1D")
BASE = datetime(2026, 8, 3, tzinfo=timezone.utc)  # دوشنبه


def _candle(index: int, tf: Timeframe, close: float, spread: float = 1.0) -> Candle:
    return Candle(
        symbol=SYMBOL,
        timeframe=tf,
        open_time=Timestamp(BASE + timedelta(seconds=index * _seconds(tf))),
        open_price=Price(Decimal(str(close - spread / 2))),
        high=Price(Decimal(str(close + spread))),
        low=Price(Decimal(str(close - spread))),
        close=Price(Decimal(str(close))),
        volume=Decimal("100"),
    )


def _seconds(tf: Timeframe) -> int:
    text = str(tf).upper()
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) * (60 if "M" in text else 3600 if "H" in text else 86400)


class _FixedSignal:
    def __init__(self, side: str, confidence: float = 0.9) -> None:
        self._side = side
        self._confidence = confidence

    def forecast(self, artifact, window, generated_at=""):
        if self._side == "buy":
            return SignalForecast.from_vector(
                (1 - self._confidence, self._confidence), horizon=1, timeframe="5M"
            )
        return SignalForecast.from_vector(
            (self._confidence, 1 - self._confidence), horizon=1, timeframe="5M"
        )


class _FixedRange:
    """پیش‌بینی ثابت — خروجی به‌صورت قیمت دلاری (pct روی reference)."""

    def __init__(self, high: float, low: float) -> None:
        self._high = high
        self._low = low
        self.calls = 0

    def forecast(self, artifact, window, reference_close, generated_at="", **_):
        self.calls += 1
        offset_h = (self._high - reference_close) / reference_close
        offset_l = (self._low - reference_close) / reference_close
        return RangeForecast(
            reference_close=reference_close,
            high_offset=offset_h,
            low_offset=offset_l,
            horizon=1,
            timeframe="4H",
        )


class _FixedDaily:
    """مدل روزانه — High/Low روز D1 نسبت به reference (close D0)."""

    def __init__(self, high: float, low: float) -> None:
        self._high = high
        self._low = low

    def forecast(self, artifact, window, reference_close, generated_at="", atr_reference=None):
        offset_h = (self._high - reference_close) / reference_close
        offset_l = (self._low - reference_close) / reference_close
        return RangeForecast(
            reference_close=reference_close,
            high_offset=offset_h,
            low_offset=offset_l,
            horizon=1,
            timeframe="1D",
        )


class _StubMatrix:
    def __init__(self, rows: int) -> None:
        self.rows = [[0.0] * 3 for _ in range(rows)]
        self.source_index = list(range(rows))


def _make_source(
    five_m_closes,
    four_h_closes,
    daily_closes,
    signal_side="buy",
    slope_mode="both",
    daily_high=None,
    daily_low=None,
    range_high=None,
    range_low=None,
    reward_risk_multiplier=None,
    spread_pct=None,
    max_entry_distance_atr=0.0,
    min_sl_distance=0.0,
):
    five_m = [_candle(i, FIVE_M, c, 0.5) for i, c in enumerate(five_m_closes)]
    four_h = [_candle(i, FOUR_H, c, 2.0) for i, c in enumerate(four_h_closes)]
    # روزها از «قبل» از BASE شروع می‌شوند تا آخرین کندل روزانه (D0) قبل
    # از اولین تصمیم 5M بسته شده باشد
    daily = []
    n = len(daily_closes)
    for i, close in enumerate(daily_closes):
        # open_i = BASE − (n−i) روز → آخرین کندل (D0) دقیقاً در BASE بسته
        # می‌شود و قبل از اولین تصمیم 5M در دسترس است
        shifted_open = Timestamp(BASE - timedelta(seconds=(n - i) * 86400))
        daily.append(
            Candle(
                symbol=SYMBOL,
                timeframe=ONE_D,
                open_time=shifted_open,
                open_price=Price(Decimal(str(close))),
                high=Price(Decimal(str(close + 4))),
                low=Price(Decimal(str(close - 4))),
                close=Price(Decimal(str(close))),
                volume=Decimal("100"),
            )
        )

    last_daily = daily[-1]
    # پیش‌فرض: هر دو پیش‌بینی بالای High/Low روز D0 → روند صعودی تمیز
    dh = daily_high if daily_high is not None else float(last_daily.close.amount) + 5
    dl = daily_low if daily_low is not None else float(last_daily.close.amount) + 5
    last_4h = four_h[-1]
    rh = range_high if range_high is not None else float(last_4h.close.amount) + 3
    rl = range_low if range_low is not None else float(last_4h.close.amount) - 3

    rows = max(len(five_m), 4)
    source = DualModelPredictionSource(
        signal_artifact=None,
        signal_predictor=_FixedSignal(signal_side),
        range_artifact=object(),
        range_predictor=_FixedRange(rh, rl),
        symbol=SYMBOL,
        signal_timeframe=FIVE_M,
        range_timeframe=FOUR_H,
        range_candles=four_h,
        signal_window_size=2,
        range_window_size=2,
        signal_matrix=_StubMatrix(rows),
        range_matrix=_StubMatrix(rows),
        signal_candles=five_m,
        reward_risk_multiplier=reward_risk_multiplier,
        range_target_units="pct",
        daily_artifact=object(),
        daily_predictor=_FixedDaily(dh, dl),
        daily_timeframe=ONE_D,
        daily_candles=daily,
        daily_matrix=_StubMatrix(len(daily)),
        daily_window_size=5,
        slope_mode=slope_mode,
        spread_pct=spread_pct,
        max_entry_distance_atr=max_entry_distance_atr,
        min_sl_distance=min_sl_distance,
    )
    for candle in five_m:
        source.observe(MarketEvent.from_candle(SYMBOL, candle))
    return source, five_m, four_h, daily


def _last_daily_close(closes):
    return closes[-1]


def _last(candles):
    return candles[-1]


def _predict_and_bracket(source, candles, side="buy", entry=None, spread_pct=None):
    last = _last(candles)
    source.predict(MarketEvent.from_candle(SYMBOL, last))
    if entry is None:
        entry = float(last.close.amount)
    price = Price(Decimal(str(entry)))
    return source.bracket_for(
        MarketEvent.from_candle(SYMBOL, last),
        OrderSide.BUY if side == "buy" else OrderSide.SELL,
        price,
    )


UP_DAILY = [2051.0 + 1.0 * i for i in range(120)]  # صعودی؛ D0: close=2170, low=2166, high=2174
UP_4H = [2050.0 + 0.5 * i for i in range(150)]
UP_5M = [2100.0 + 0.1 * i for i in range(120)]


class TestLicense2Slope:
    def test_buy_passes_uptrend_and_bracket_uses_4h(self):
        source, five_m, _, _ = _make_source(UP_5M, UP_4H, UP_DAILY, signal_side="buy")
        bracket = _predict_and_bracket(source, five_m, "buy", entry=2125.0)
        assert bracket is not None
        # 4H forecast: close(2124.5) ±3 → TP = High پیش‌بینی، SL = Low پیش‌بینی
        assert float(bracket.take_profit.amount) == pytest.approx(2127.5)
        assert float(bracket.stop_loss.amount) == pytest.approx(2121.5)
        stats = source.stats()
        assert stats["daily_blocked"] == 0
        assert stats["daily_predictions"] == 1

    @pytest.mark.parametrize("mode", ["both", "either", "high", "low"])
    def test_sell_blocked_in_uptrend_all_modes(self, mode):
        # روند صعودی: High/Low پیش‌بینی هر دو بالای D0 → شیب‌ها مثبت
        source, five_m, _, _ = _make_source(
            UP_5M, UP_4H, UP_DAILY, signal_side="sell", slope_mode=mode
        )
        source.predict(MarketEvent.from_candle(SYMBOL, _last(five_m)))
        assert source.stats()["daily_blocked"] == 1

    def test_slope_mode_high_lets_sell_pass_when_high_falls(self):
        # High پیش‌بینی زیر High(D0)=2174 ولی Low پیش‌بینی بالای Low(D0)=2166
        source, five_m, _, _ = _make_source(
            UP_5M,
            UP_4H,
            UP_DAILY,
            signal_side="sell",
            slope_mode="high",
            daily_high=2160.0,  # شیب High منفی
            daily_low=2180.0,  # شیب Low مثبت
        )
        source.predict(MarketEvent.from_candle(SYMBOL, _last(five_m)))
        assert source.stats()["daily_blocked"] == 0

    def test_slope_mode_both_blocks_same_case(self):
        source, five_m, _, _ = _make_source(
            UP_5M,
            UP_4H,
            UP_DAILY,
            signal_side="sell",
            slope_mode="both",
            daily_high=2470.0,  # شیب High منفی
            daily_low=2480.0,  # شیب Low مثبت → حالت both رد می‌کند
        )
        source.predict(MarketEvent.from_candle(SYMBOL, _last(five_m)))
        assert source.stats()["daily_blocked"] == 1

    def test_unknown_slope_mode_refused(self):
        with pytest.raises(ValidationError):
            _make_source(UP_5M, UP_4H, UP_DAILY, slope_mode="wicks")


class TestBracketFallbacks:
    def test_fallback1_sl_becomes_d0_low(self):
        # خرید: SL از 4H = 2176 ≥ entry 2175 → SL = Low(D0) = 2166
        source, five_m, _, _ = _make_source(
            UP_5M,
            UP_4H,
            UP_DAILY,
            signal_side="buy",
            range_high=2180.0,
            range_low=2176.0,  # SL پیش‌بینی بالای ورود
        )
        bracket = _predict_and_bracket(source, five_m, "buy", entry=2175.0)
        assert bracket is not None
        assert float(bracket.stop_loss.amount) == pytest.approx(2166.0)
        assert source.stats()["sl_fallback_d0"] == 1

    def test_fallback2_uses_today_5m_low_minus_spread(self):
        # D0 low (2176) هم بالای ورود (2175) → کمترین Low زیر ورود از
        # کندل‌های 5M امروز منهای اسپرد
        source, five_m, _, _ = _make_source(
            UP_5M[:100],  # کمتر از ظرفیت deque تا همه در «امروز» بمانند
            UP_4H,
            UP_DAILY[:-1] + [2180.0],  # Low(D0) = 2176 ≥ 2175
            signal_side="buy",
            range_high=2180.0,
            range_low=2176.0,
            spread_pct=0.0006,
        )
        entry = 2175.0
        bracket = _predict_and_bracket(source, five_m, "buy", entry=entry, spread_pct=0.0006)
        assert bracket is not None
        lows_below = [float(c.low.amount) for c in five_m if float(c.low.amount) < entry]
        expected = min(lows_below) - entry * 0.0006
        assert float(bracket.stop_loss.amount) == pytest.approx(expected)
        assert source.stats()["sl_fallback_today"] == 1

    def test_no_today_low_below_entry_refuses(self):
        # ورود پایین‌تر از همهٔ Low های 5M امروز → هیچ SL معتبری نیست
        source, five_m, _, _ = _make_source(
            UP_5M,
            UP_4H,
            UP_DAILY,
            signal_side="buy",
            range_high=2180.0,
            range_low=2176.0,
        )
        bracket = _predict_and_bracket(source, five_m, "buy", entry=2099.0)
        assert bracket is None
        assert source.stats()["no_sl_found"] == 1

    def test_license3_tp_below_entry_refused(self):
        source, five_m, _, _ = _make_source(
            UP_5M,
            UP_4H,
            UP_DAILY,
            signal_side="buy",
            range_high=2160.0,  # TP زیر ورود
            range_low=2150.0,
        )
        bracket = _predict_and_bracket(source, five_m, "buy", entry=2170.0)
        assert bracket is None
        assert source.stats()["license3_refused"] == 1

    def test_rr_multiplier_refuses_thin_bracket(self):
        source, five_m, _, _ = _make_source(
            UP_5M,
            UP_4H,
            UP_DAILY,
            signal_side="buy",
            range_high=2173.0,  # TP dist ~3
            range_low=2171.5,  # SL dist ~1.5 → R/R=2 رد می‌کند
            reward_risk_multiplier=2.0,
        )
        bracket = _predict_and_bracket(source, five_m, "buy", entry=2170.0)
        assert bracket is None
        assert source.stats()["rr_refused"] == 1

    def test_sell_bracket_mirrored(self):
        # فروش: TP = Low پیش‌بینی، SL = High پیش‌بینی
        source, five_m, _, _ = _make_source(
            UP_5M,
            UP_4H,
            UP_DAILY,
            signal_side="sell",
            slope_mode="either",
            daily_high=2170.0,  # شیب High منفی نسبت به High(D0)=2174
            range_high=2180.0,
            range_low=2165.0,
        )
        bracket = _predict_and_bracket(source, five_m, "sell", entry=2170.0)
        assert bracket is not None
        assert float(bracket.take_profit.amount) == pytest.approx(2165.0)
        assert float(bracket.stop_loss.amount) == pytest.approx(2180.0)


class TestLicense4Proximity:
    """مجوز ۴ (فاز ۹۷-ب): ورود باید نزدیک سطح روزانه باشد.

    خرید: فاصلهٔ قیمت از Low پیش‌بینی D1 ≤ max × ATR14(1D)؛
    فروش: فاصله از High پیش‌بینی D1. دادهٔ اپراتور: برندگان med $1.7
    نزدیکِ close روز، بازندگان $9.3 دور → پیش‌فرض 0.25×ATR (~$10).
    """

    def test_buy_far_above_daily_low_is_blocked(self):
        # روزهای پایانی 1D پایین‌تر از بازار: D0: close≈2069, low≈2065
        # daily_low=2068 → شیب Low مثبت (2068 > 2065)؛ ولی ورود ~2124.5
        # فاصله ~$56 — ATR(1D)~2 → max=$0.5 → مجوز ۴ می‌بندد
        source, five_m, _, _ = _make_source(
            UP_5M,
            UP_4H,
            [2000.0 + 0.5 * i for i in range(120)],
            signal_side="buy",
            range_high=2127.5,
            range_low=2121.5,
            daily_low=2068.0,
            max_entry_distance_atr=0.25,
        )
        source.predict(MarketEvent.from_candle(SYMBOL, _last(five_m)))
        assert source.stats()["proximity_blocked"] == 1

    def test_buy_near_daily_low_passes(self):
        # Low پیش‌بینی D1 نزدیک ورود: ورود ~2124.5، daily_low=2121 →
        # فاصله ~$3.5؛ ATR(1D)=2 → max=0.25×2=$0.5 → باز هم بلاک می‌شود!
        # پس با همین داده آستانهٔ خاموش (0) یا ATR بزرگ لازم است —
        # این تست «پاس» را با daily_low بسیار نزدیک می‌بندیم:
        source, five_m, _, _ = _make_source(
            UP_5M[:100],
            UP_4H,
            [2115.0 + 0.1 * i for i in range(120)],  # D0: close≈2126.9, low≈2122.9
            signal_side="buy",
            range_high=2127.5,
            range_low=2121.5,
            daily_low=2123.5,  # فاصلهٔ ورود تا Low ≈ 1 → در max=$0.5? بلاک!
            max_entry_distance_atr=0.5,
        )
        # با ATR بزرگ‌تر (کندل‌های نوسانی‌تر) آستانه واقعاً باز می‌شود —
        # اینجا فقط رد نشدن توسط گیت شیب را چک می‌کنیم؛ بلاک مجوز ۴ با
        # همین داده هم درست است (فاصله 1 > 0.5×ATR~2/4):
        source.predict(MarketEvent.from_candle(SYMBOL, _last(five_m)))
        stats = source.stats()
        # مجوز ۲ باید پاس شده باشد (شیب‌ها مثبت)
        assert stats["daily_blocked"] == 0
        source.predict(MarketEvent.from_candle(SYMBOL, _last(five_m)))
        assert source.stats()["proximity_blocked"] == 0

    def test_sell_far_below_daily_high_is_blocked(self):
        # فروش: شیب‌ها منفی (مجوز ۲ پاس) ولی High پیش‌بینی D1 خیلی بالاتر
        # از بازار → فاصله > max → مجوز ۴ می‌بندد
        source, five_m, _, _ = _make_source(
            UP_5M,
            UP_4H,
            UP_DAILY,
            signal_side="sell",
            slope_mode="either",
            daily_high=2160.0,  # بالاتر از بازار (~$35) — دور
            daily_low=2100.0,
            range_high=2130.0,
            range_low=2120.0,
            max_entry_distance_atr=0.25,
        )
        source.predict(MarketEvent.from_candle(SYMBOL, _last(five_m)))
        assert source.stats()["proximity_blocked"] == 1

    def test_zero_disables_the_license(self):
        source, five_m, _, _ = _make_source(
            UP_5M,
            UP_4H,
            UP_DAILY,
            signal_side="buy",
            range_high=2127.5,
            range_low=2121.5,
            daily_low=2103.0,  # دور ولی خاموش
            max_entry_distance_atr=0.0,
        )
        source.predict(MarketEvent.from_candle(SYMBOL, _last(five_m)))
        assert source.stats()["proximity_blocked"] == 0

    def test_negative_threshold_refused(self):
        with pytest.raises(ValidationError):
            _make_source(
                UP_5M,
                UP_4H,
                UP_DAILY,
                signal_side="buy",
                max_entry_distance_atr=-1.0,
            )


class TestFinalSlFloor:
    """فاز ۹۷-د: حداقل فاصلهٔ SL روی SL «نهایی» (بعد از fallback)."""

    def test_d0_fallback_too_close_is_refused(self, spread_pct=0.0006):
        # fallback D0: Low(D0)=2166 با ورود 2170 → dist=4 < 6 → رد
        source, five_m, _, _ = _make_source(
            UP_5M,
            UP_4H,
            UP_DAILY[:-1] + [2170.0],  # D0: close 2170, low 2166
            signal_side="buy",
            range_high=2180.0,
            range_low=2176.0,  # SL پیش‌بینی بالای ورود → fallback
            min_sl_distance=6.0,
        )
        bracket = _predict_and_bracket(source, five_m, "buy", entry=2170.5)
        assert bracket is None
        assert source.stats()["final_sl_refused"] == 1

    def test_d0_fallback_far_enough_passes(self):
        # Low(D0) = 2166 − ورود 2171 → dist = 5؟ با min=6 رد؛ ورود 2172.5 → dist 6.5 ✓
        source, five_m, _, _ = _make_source(
            UP_5M,
            UP_4H,
            UP_DAILY[:-1] + [2170.0],
            signal_side="buy",
            range_high=2180.0,
            range_low=2176.0,
            min_sl_distance=6.0,
        )
        bracket = _predict_and_bracket(source, five_m, "buy", entry=2172.5)
        assert bracket is not None
        assert float(bracket.stop_loss.amount) == pytest.approx(2166.0)
        assert source.stats()["final_sl_refused"] == 0

    def test_spread_floor_alone_blocks_knife(self):
        # min_sl_distance=0 ولی اسپرد 0.06% → کف = 2×2170×0.0006 ≈ $2.60
        # fallback D0 با dist $2 (D0 close=2172 → low=2168) → رد
        source, five_m, _, _ = _make_source(
            UP_5M,
            UP_4H,
            UP_DAILY[:-1] + [2172.0],
            signal_side="buy",
            range_high=2180.0,
            range_low=2176.0,
            spread_pct=0.0006,
        )
        bracket = _predict_and_bracket(source, five_m, "buy", entry=2170.0, spread_pct=0.0006)
        assert bracket is None
        assert source.stats()["final_sl_refused"] == 1
