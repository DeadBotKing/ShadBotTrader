"""Data inspection: chart, candle facts and column listing (Phase 34).

The operator's question after each of Fetch / Update features / Build
dataset is the same: *what is actually stored now?* These tests pin down
that the answer is read from storage and reported honestly — including
when nothing is stored at all.
"""

import json
import threading
import urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.data.parquet_candle_store import ParquetCandleStore
from ShadBotTrader.infrastructure.persistence import Database
from ShadBotTrader.presentation.gateway.data_inspector import DataInspector
from ShadBotTrader.presentation.web.data_renderer import render_data_page
from ShadBotTrader.presentation.web.server import create_server

SYMBOL = "XAUUSD"
FIVE_MIN = "5M"


def candles(count: int, start: datetime | None = None):
    moment = start or datetime(2024, 5, 1, 8, 0, tzinfo=timezone.utc)
    out = []
    price = 2000.0
    for index in range(count):
        move = 2.0 if index % 2 else -1.5
        open_, close = price, price + move
        out.append(
            Candle(
                symbol=Symbol(SYMBOL),
                timeframe=Timeframe(FIVE_MIN),
                open_time=Timestamp(moment + timedelta(minutes=5 * index)),
                open_price=Price(Decimal(str(round(open_, 2)))),
                high=Price(Decimal(str(round(max(open_, close) + 1, 2)))),
                low=Price(Decimal(str(round(min(open_, close) - 1, 2)))),
                close=Price(Decimal(str(round(close, 2)))),
                volume=Decimal(str(100 + index)),
            )
        )
        price = close
    return out


def store_candles(root, items):
    from ShadBotTrader.domain.dataset.data_layer import DataLayer
    from ShadBotTrader.domain.dataset.dataset_identity import DataKind, DatasetId

    store = ParquetCandleStore(root)
    dataset_id = DatasetId(
        provider="csv",
        kind=DataKind.MARKET_CANDLE,
        symbol=SYMBOL,
        timeframe=FIVE_MIN,
        layer=DataLayer.NORMALIZED.value,
    )
    store.save_normalized(dataset_id, 1, items)
    return store


@pytest.fixture
def populated(tmp_path):
    store_candles(tmp_path, candles(500))
    return tmp_path


# ---------------------------------------------------------------- candles ---
class TestCandleInspection:
    def test_the_stored_count_is_reported(self, populated):
        info = DataInspector(populated).candles(SYMBOL, FIVE_MIN)

        assert info.exists
        assert info.count == 500

    def test_the_chart_carries_ohlcv_for_each_point(self, populated):
        info = DataInspector(populated).candles(SYMBOL, FIVE_MIN)

        assert info.chart
        first = info.chart[0]
        assert set(first) == {"t", "o", "h", "l", "c", "v"}

    def test_the_chart_is_limited_but_the_count_is_not(self, populated):
        """A 100k dataset must not become a 100k-point web page."""
        info = DataInspector(populated, chart_candles=100).candles(SYMBOL, FIVE_MIN)

        assert len(info.chart) == 100
        assert info.count == 500

    def test_the_chart_shows_the_newest_candles(self, populated):
        info = DataInspector(populated, chart_candles=50).candles(SYMBOL, FIVE_MIN)

        assert info.chart[-1]["t"] == info.last_time.isoformat()

    def test_the_price_range_matches_the_charted_window(self, populated):
        info = DataInspector(populated).candles(SYMBOL, FIVE_MIN)

        lows = [point["l"] for point in info.chart]
        highs = [point["h"] for point in info.chart]
        assert info.price_low == pytest.approx(min(lows))
        assert info.price_high == pytest.approx(max(highs))

    def test_continuity_is_reported_alongside(self, populated):
        info = DataInspector(populated).candles(SYMBOL, FIVE_MIN)

        assert info.continuity is not None
        assert info.continuity["continuous"] is True

    def test_a_gap_shows_up_in_the_report(self, tmp_path):
        series = candles(200)
        store_candles(tmp_path, series[:80] + series[120:])

        info = DataInspector(tmp_path).candles(SYMBOL, FIVE_MIN)

        assert info.continuity["continuous"] is False
        assert info.continuity["missing_candles"] == 40

    def test_an_unknown_series_reports_absence_not_an_error(self, tmp_path):
        info = DataInspector(tmp_path).candles("NOTHING", "1H")

        assert not info.exists
        assert info.count == 0
        assert info.chart == []

    def test_stored_series_are_discoverable(self, populated):
        found = DataInspector(populated).available_series()

        assert {"symbol": SYMBOL, "timeframe": FIVE_MIN} in found


# ----------------------------------------------------------------- matrix ---
class TestMatrixInspection:
    @pytest.fixture
    def with_matrix(self, tmp_path):
        from ShadBotTrader.application.services.training_data_service import (
            TrainingDataService,
        )
        from ShadBotTrader.domain.dataset.training_dataset import DatasetSpec

        series = candles(1200)
        store_candles(tmp_path, series)
        service = TrainingDataService(tmp_path)  # OHLCV only: fast
        service.build(
            DatasetSpec(
                symbol=SYMBOL,
                timeframes=(FIVE_MIN,),
                target_candles=1200,
                window_rows=500,
            ),
            {FIVE_MIN: series},
        )
        return tmp_path

    def test_rows_and_columns_are_reported(self, with_matrix):
        info = DataInspector(with_matrix).training_matrix(SYMBOL, FIVE_MIN)

        assert info.exists
        assert info.rows > 0
        assert info.column_count == 14  # OHLCV-only build

    def test_every_column_is_described(self, with_matrix):
        info = DataInspector(with_matrix).training_matrix(SYMBOL, FIVE_MIN)

        for column in info.columns:
            assert column.name
            assert column.kind in {"raw price", "candle shape", "feature", "target"}
            assert column.total > 0

    def test_columns_are_grouped_by_kind(self, with_matrix):
        info = DataInspector(with_matrix).training_matrix(SYMBOL, FIVE_MIN)

        kinds = {column.kind for column in info.columns}
        assert "raw price" in kinds
        assert "candle shape" in kinds

    def test_a_constant_column_is_flagged(self, with_matrix):
        """close_rel is zero by construction — say so rather than hide it."""
        info = DataInspector(with_matrix).training_matrix(SYMBOL, FIVE_MIN)

        assert "close_rel" in [column.name for column in info.constant_columns]

    def test_the_digest_and_revision_come_from_the_manifest(self, with_matrix):
        info = DataInspector(with_matrix).training_matrix(SYMBOL, FIVE_MIN)

        assert info.digest
        assert info.revision == 1

    def test_an_absent_matrix_reports_absence(self, tmp_path):
        info = DataInspector(tmp_path).training_matrix(SYMBOL, FIVE_MIN)

        assert not info.exists
        assert info.column_count == 0


# --------------------------------------------------------------- features ---
class TestFeatureInspection:
    def test_nothing_computed_reports_nothing(self, tmp_path):
        result = DataInspector(tmp_path).features()

        assert not result["exists"]
        assert result["count"] == 0

    def test_stored_features_are_listed(self, tmp_path):
        from ShadBotTrader.domain.feature.feature_result import (
            FeaturePoint,
            FeatureResult,
        )
        from ShadBotTrader.infrastructure.feature.parquet_feature_store import (
            ParquetFeatureStore,
        )

        store = ParquetFeatureStore(tmp_path)
        moment = datetime(2024, 5, 1, tzinfo=timezone.utc)
        store.save(
            "rsi_14",
            1,
            FeatureResult(
                feature_id="rsi_14",
                points=[
                    FeaturePoint(
                        timestamp=Timestamp(moment + timedelta(minutes=5 * i)),
                        value=float(50 + i),
                    )
                    for i in range(20)
                ],
            ),
        )

        result = DataInspector(tmp_path).features()

        assert result["exists"]
        assert result["count"] == 1
        assert result["features"][0]["feature_id"] == "rsi_14"

    def test_one_feature_series_can_be_read(self, tmp_path):
        from ShadBotTrader.domain.feature.feature_result import (
            FeaturePoint,
            FeatureResult,
        )
        from ShadBotTrader.infrastructure.feature.parquet_feature_store import (
            ParquetFeatureStore,
        )

        moment = datetime(2024, 5, 1, tzinfo=timezone.utc)
        ParquetFeatureStore(tmp_path).save(
            "sma_20",
            1,
            FeatureResult(
                feature_id="sma_20",
                points=[
                    FeaturePoint(timestamp=Timestamp(moment), value=None),
                    FeaturePoint(timestamp=Timestamp(moment + timedelta(minutes=5)), value=2000.0),
                ],
            ),
        )

        result = DataInspector(tmp_path).feature_values("sma_20")

        assert result["exists"]
        assert result["total_points"] == 2
        assert result["missing"] == 1  # the warm-up point is honest, not zero

    def test_an_unknown_feature_reports_absence(self, tmp_path):
        assert not DataInspector(tmp_path).feature_values("nope")["exists"]


# ------------------------------------------------------------------ page ---
class TestDataPage:
    def test_the_page_renders_with_data(self, populated):
        inspector = DataInspector(populated)

        page = render_data_page(
            candles=inspector.candles(SYMBOL, FIVE_MIN).to_dict(),
            matrix=inspector.training_matrix(SYMBOL, FIVE_MIN).to_dict(),
            features=inspector.features(),
            series=inspector.available_series(),
            selected={"symbol": SYMBOL, "timeframe": FIVE_MIN},
        )

        assert page.startswith("<!DOCTYPE html>")
        assert 'id="chart"' in page
        assert "500" in page

    def test_the_page_is_self_contained(self, populated):
        inspector = DataInspector(populated)

        page = render_data_page(
            candles=inspector.candles(SYMBOL, FIVE_MIN).to_dict(),
            matrix=inspector.training_matrix(SYMBOL, FIVE_MIN).to_dict(),
            features=inspector.features(),
        )

        assert "http://" not in page and "https://" not in page
        assert "<script src=" not in page

    def test_the_candles_are_embedded_as_data(self, populated):
        inspector = DataInspector(populated)

        page = render_data_page(
            candles=inspector.candles(populated and SYMBOL, FIVE_MIN).to_dict(),
            matrix={},
            features={},
        )
        payload = page.split("const CANDLES = ", 1)[1].split(";\n", 1)[0]

        assert len(json.loads(payload)) > 0

    def test_an_empty_installation_explains_what_to_press(self, tmp_path):
        inspector = DataInspector(tmp_path)

        page = render_data_page(
            candles=inspector.candles(SYMBOL, FIVE_MIN).to_dict(),
            matrix=inspector.training_matrix(SYMBOL, FIVE_MIN).to_dict(),
            features=inspector.features(),
        )

        assert "Fetch market data" in page
        assert "Build training dataset" in page
        assert "Update features" in page


class TestDataRoute:
    @pytest.fixture
    def server(self, tmp_path):
        database = tmp_path / "d.db"
        Database(database).close()
        store_candles(tmp_path / "datasets", candles(300))

        httpd = create_server(
            database,
            host="127.0.0.1",
            port=0,
            storage_root=tmp_path / "datasets",
            account_store=tmp_path / "accounts.json",
        )
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        yield f"http://127.0.0.1:{port}"
        httpd.shutdown()
        httpd.server_close()

    def get(self, url):
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.read().decode("utf-8")

    def test_the_data_page_is_served(self, server):
        page = self.get(f"{server}/data")

        assert 'id="chart"' in page
        assert "300" in page

    def test_the_dashboard_links_to_it(self, server):
        assert 'href="/data"' in self.get(f"{server}/")

    def test_the_json_api_mirrors_the_page(self, server):
        payload = json.loads(self.get(f"{server}/api/data"))

        assert payload["candles"]["count"] == 300
        assert payload["symbol"] == SYMBOL

    def test_a_series_can_be_selected(self, server):
        page = self.get(f"{server}/data?series={SYMBOL}|{FIVE_MIN}")

        assert f"{SYMBOL} {FIVE_MIN}" in page
