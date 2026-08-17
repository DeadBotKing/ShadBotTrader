"""Tests for candle continuity and the learned market calendar (Phase 33).

The user's requirement, in their words: when the dataset is updated a
month later, the last stored candle must join the first new one with no
hole in between — *allowing for days the market is closed*.

That distinction is the whole difficulty, so most of these tests are
about telling a weekend apart from missing data.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.dataset.continuity import (
    MarketCalendar,
    analyse_continuity,
    check_join,
    merge_candles,
    timeframe_delta,
)
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp

SYMBOL = Symbol("XAUUSD")
DAILY = Timeframe("1D")
FIVE_MIN = Timeframe("5M")


def candle_at(moment: datetime, timeframe: Timeframe = DAILY, price: float = 2000.0):
    return Candle(
        symbol=SYMBOL,
        timeframe=timeframe,
        open_time=Timestamp(moment),
        open_price=Price(Decimal(str(price))),
        high=Price(Decimal(str(price + 5))),
        low=Price(Decimal(str(price - 5))),
        close=Price(Decimal(str(price + 1))),
        volume=Decimal("100"),
    )


def weekdays(start: datetime, count: int):
    """``count`` daily candles, skipping Saturday and Sunday."""
    out = []
    cursor = start
    price = 2000.0
    while len(out) < count:
        if cursor.weekday() < 5:
            out.append(candle_at(cursor, DAILY, price))
            price += 1
        cursor += timedelta(days=1)
    return out


def every_day(start: datetime, count: int):
    return [candle_at(start + timedelta(days=i), DAILY, 2000 + i) for i in range(count)]


# ------------------------------------------------------------- calendar ---
class TestMarketCalendar:
    def test_it_learns_that_weekends_are_closed(self):
        """Nobody configures this — it is read off the data."""
        calendar = MarketCalendar.learn(weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 40))

        assert calendar.closed_weekdays == {5, 6}  # Saturday, Sunday
        assert "Sat" in calendar.describe()

    def test_a_market_that_never_closes_has_no_closed_days(self):
        """Crypto trades every day; the same code must handle it."""
        calendar = MarketCalendar.learn(every_day(datetime(2024, 5, 1, tzinfo=timezone.utc), 40))

        assert calendar.closed_weekdays == set()
        assert "every day" in calendar.describe()

    def test_it_stays_silent_without_enough_evidence(self):
        calendar = MarketCalendar.learn(weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 3))

        assert not calendar.is_confident

    def test_an_empty_history_yields_an_empty_calendar(self):
        calendar = MarketCalendar.learn([])

        assert calendar.closed_weekdays == set()
        assert calendar.observed_days == 0

    def test_the_evidence_is_inspectable(self):
        """A claim about the market must be checkable against the data."""
        calendar = MarketCalendar.learn(weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 40))

        traded, total = calendar.evidence[5]  # Saturday
        assert traded == 0 and total > 0

    def test_a_weekend_costs_no_expected_slots(self):
        calendar = MarketCalendar.learn(weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 40))
        friday = datetime(2024, 7, 5, tzinfo=timezone.utc)
        monday = datetime(2024, 7, 8, tzinfo=timezone.utc)

        assert calendar.expected_slots(friday, monday, DAILY) == 0

    def test_a_missing_trading_day_does_cost_a_slot(self):
        calendar = MarketCalendar.learn(weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 40))
        monday = datetime(2024, 7, 8, tzinfo=timezone.utc)
        wednesday = datetime(2024, 7, 10, tzinfo=timezone.utc)

        assert calendar.expected_slots(monday, wednesday, DAILY) == 1  # Tuesday


class TestTimeframeDelta:
    @pytest.mark.parametrize(
        "label,expected",
        [
            ("5M", timedelta(minutes=5)),
            ("15M", timedelta(minutes=15)),
            ("1H", timedelta(hours=1)),
            ("4H", timedelta(hours=4)),
            ("1D", timedelta(days=1)),
        ],
    )
    def test_the_step_matches_the_timeframe(self, label, expected):
        assert timeframe_delta(Timeframe(label)) == expected


# ---------------------------------------------------------------- joins ---
class TestCheckJoin:
    def setup_method(self):
        self.history = weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 40)
        self.calendar = MarketCalendar.learn(self.history)
        self.last = self.history[-1].open_time.value

    def next_trading_day(self, moment: datetime) -> datetime:
        cursor = moment + timedelta(days=1)
        while cursor.weekday() >= 5:
            cursor += timedelta(days=1)
        return cursor

    def test_the_next_trading_day_joins_cleanly(self):
        """The exact case the user described: Monday 10th -> Tuesday 11th."""
        following = weekdays(self.next_trading_day(self.last), 5)

        assert check_join(self.history, following, DAILY, self.calendar) is None

    def test_a_weekend_between_them_is_not_a_gap(self):
        friday = datetime(2024, 7, 5, tzinfo=timezone.utc)
        history = weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 1) + [candle_at(friday)]
        monday = [candle_at(datetime(2024, 7, 8, tzinfo=timezone.utc))]

        assert check_join(history, monday, DAILY, self.calendar) is None

    def test_a_single_missing_trading_day_is_reported(self):
        skipped = self.next_trading_day(self.next_trading_day(self.last))
        following = weekdays(skipped, 5)

        gap = check_join(self.history, following, DAILY, self.calendar)

        assert gap is not None
        assert gap.missing == 1

    def test_a_month_long_hole_counts_only_trading_days(self):
        """Thirty calendar days, but only ~21 trading days are missing."""
        following = weekdays(self.last + timedelta(days=30), 5)

        gap = check_join(self.history, following, DAILY, self.calendar)

        assert gap is not None
        assert 18 <= gap.missing <= 23
        assert "missing" in gap.describe()

    def test_overlapping_data_is_not_a_gap(self):
        overlap = self.history[-5:]

        assert check_join(self.history, overlap, DAILY, self.calendar) is None

    def test_a_tolerance_absorbs_a_single_dropped_bar(self):
        skipped = self.next_trading_day(self.next_trading_day(self.last))
        following = weekdays(skipped, 5)

        assert check_join(self.history, following, DAILY, self.calendar, tolerance=2) is None

    def test_nothing_to_join_returns_nothing(self):
        assert check_join([], weekdays(self.last, 3), DAILY) is None
        assert check_join(self.history, [], DAILY) is None


# ----------------------------------------------------------- continuity ---
class TestAnalyseContinuity:
    def test_an_unbroken_series_is_continuous(self):
        report = analyse_continuity(weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 40), DAILY)

        assert report.is_continuous
        assert report.missing_candles == 0

    def test_a_hole_in_the_middle_is_found(self):
        candles = weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 40)
        broken = candles[:20] + candles[25:]

        report = analyse_continuity(broken, DAILY)

        assert not report.is_continuous
        assert report.gaps
        assert report.missing_candles == 5

    def test_duplicates_are_counted(self):
        candles = weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 10)
        report = analyse_continuity([*candles, candles[3]], DAILY)

        assert report.duplicates == 1
        assert not report.is_continuous

    def test_out_of_order_input_is_detected(self):
        candles = weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 10)
        shuffled = [candles[5], *candles[:5], *candles[6:]]

        report = analyse_continuity(shuffled, DAILY)

        assert report.out_of_order > 0

    def test_five_minute_series_work_too(self):
        start = datetime(2024, 5, 1, 8, 0, tzinfo=timezone.utc)
        candles = [candle_at(start + timedelta(minutes=5 * i), FIVE_MIN) for i in range(50)]

        assert analyse_continuity(candles, FIVE_MIN).is_continuous

    def test_the_largest_gap_is_reported(self):
        candles = weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 60)
        broken = candles[:10] + candles[13:40] + candles[50:]

        report = analyse_continuity(broken, DAILY)

        assert report.largest_gap is not None
        assert report.largest_gap.missing == 10

    def test_the_summary_reads_clearly(self):
        report = analyse_continuity(weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 20), DAILY)

        text = " ".join(report.summary_lines())
        assert "continuity" in text
        assert "OK" in text

    def test_an_empty_series_is_trivially_continuous(self):
        report = analyse_continuity([], DAILY)

        assert report.is_continuous
        assert report.candle_count == 0


# --------------------------------------------------------------- merging ---
class TestMergeCandles:
    def test_new_candles_extend_the_history(self):
        first = weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 10)
        second = weekdays(first[-1].open_time.value + timedelta(days=3), 5)

        merged = merge_candles(first, second)

        assert len(merged) == 15

    def test_the_result_is_ordered(self):
        first = weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 10)
        second = weekdays(first[-1].open_time.value + timedelta(days=3), 5)

        merged = merge_candles(second, first)  # deliberately backwards

        stamps = [candle.open_time.value for candle in merged]
        assert stamps == sorted(stamps)

    def test_a_repeated_timestamp_is_not_duplicated(self):
        candles = weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 10)

        merged = merge_candles(candles, candles)

        assert len(merged) == 10

    def test_the_incoming_candle_wins_a_collision(self):
        """A re-fetched bar is a correction of a still-forming one."""
        moment = datetime(2024, 5, 1, tzinfo=timezone.utc)
        old = [candle_at(moment, DAILY, 2000.0)]
        new = [candle_at(moment, DAILY, 2500.0)]

        merged = merge_candles(old, new)

        assert len(merged) == 1
        assert float(merged[0].open.amount) == 2500.0

    def test_the_rolling_limit_keeps_the_newest(self):
        candles = weekdays(datetime(2024, 5, 1, tzinfo=timezone.utc), 100)

        merged = merge_candles(candles, [], max_candles=60)

        assert len(merged) == 60
        assert merged[-1].open_time.value == candles[-1].open_time.value

    def test_a_zero_limit_is_refused(self):
        from ShadBotTrader.domain.common.errors import ValidationError

        with pytest.raises(ValidationError):
            merge_candles([], [], max_candles=0)
