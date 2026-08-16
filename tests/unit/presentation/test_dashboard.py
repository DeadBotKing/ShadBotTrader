"""Tests for the presentation layer (Phase 19).

Two things matter here:

* the GUI shows what is actually stored — no invented numbers
* the GUI *cannot* act: no method or endpoint mutates anything
"""

from decimal import Decimal

import pytest

from ShadBotTrader.domain.execution.execution_types import ExecutionStatus
from ShadBotTrader.domain.execution.fill import ExecutionResult, Fill
from ShadBotTrader.domain.execution.money import Money
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.risk_policy import RiskVerdict
from ShadBotTrader.domain.strategy.strategy_types import RejectionReason, SignalType
from ShadBotTrader.domain.trading.order import OrderSide
from ShadBotTrader.infrastructure.persistence import (
    Database,
    SqliteDecisionJournal,
    SqliteLearningMemory,
    SqlitePortfolioLedger,
)
from ShadBotTrader.infrastructure.trading import PositionAwareDecisionEngine
from ShadBotTrader.presentation.gateway.dashboard_gateway import DashboardGateway
from ShadBotTrader.presentation.viewmodels.models import (
    money,
    percent,
    ratio,
    signed,
    tone,
)
from ShadBotTrader.presentation.web.renderer import render_dashboard
from tests.learning_fixtures import make_candidate, winning_fold
from tests.unit.strategy.conftest import BASE_TIME, flat_portfolio, make_context, make_signal

XAU = Symbol("XAUUSD_i")
TF = Timeframe("5M")
SESSION = "test-session"


def d(value: str) -> Decimal:
    return Decimal(value)


@pytest.fixture
def database(tmp_path) -> Database:
    return Database(tmp_path / "dash.db")


@pytest.fixture
def populated(database) -> Database:
    """A database with a position, decisions and a learning candidate."""
    ledger = SqlitePortfolioLedger(database, session_id=SESSION, starting_cash=d("100"))
    ledger.apply(
        ExecutionResult(
            intent_id="i1",
            order_id="o1",
            status=ExecutionStatus.FILLED,
            requested_quantity=d("2"),
            fills=[
                Fill(
                    fill_id="f1",
                    order_id="o1",
                    symbol=XAU,
                    side=OrderSide.BUY,
                    quantity=d("2"),
                    price=Price(d("2000")),
                    executed_at=Timestamp(BASE_TIME),
                    fee=Money(d("0.4"), "USD"),
                )
            ],
        )
    )

    journal = SqliteDecisionJournal(database, session_id=SESSION)
    decision = PositionAwareDecisionEngine().decide(
        make_signal(XAU, TF, SignalType.BUY),
        make_context(XAU, TF, portfolio=flat_portfolio()),
    )
    journal.record(decision, RiskVerdict.approve(), None)
    journal.record(decision, RiskVerdict.reject(RejectionReason.RISK_EXPOSURE))

    memory = SqliteLearningMemory(database)
    memory.remember(make_candidate("c1", in_sample="5", folds=[winning_fold("2")]))
    return database


# ---------------------------------------------------------- formatting -----
class TestFormatters:
    def test_money_and_signed(self):
        assert money(d("1234.5")) == "1,234.50"
        assert signed(d("12.5")) == "+12.50"
        assert signed(d("-12.5")) == "-12.50"

    def test_none_is_shown_honestly(self):
        """Missing data must look missing, not like zero."""
        assert money(None) == "—"
        assert signed(None) == "—"
        assert percent(None) == "—"
        assert ratio(None) == "n/a"

    def test_tone_reflects_sign(self):
        assert tone(d("1")) == "positive"
        assert tone(d("-1")) == "negative"
        assert tone(d("0")) == "neutral"
        assert tone(None) == "neutral"


# ------------------------------------------------------------- gateway -----
class TestDashboardGateway:
    def test_system_reports_the_schema(self, database):
        system = DashboardGateway(database).system()
        assert system.schema_version == 1
        assert system.environment == "local"
        assert "trading_decision" in system.table_counts

    def test_empty_database_yields_an_empty_dashboard(self, database):
        view = DashboardGateway(database).dashboard()
        assert view.is_empty
        assert view.portfolio is None
        assert view.decisions == []

    def test_portfolio_reflects_stored_position(self, populated):
        view = DashboardGateway(populated).portfolio(SESSION)
        assert view.open_positions == 1
        position = view.positions[0]
        assert position.symbol == "XAUUSD_i"
        assert position.side == "long"
        assert position.average_price == "2,000.00000"

    def test_decisions_show_the_risk_verdict(self, populated):
        decisions = DashboardGateway(populated).decisions(SESSION)
        assert len(decisions) == 2
        verdicts = {item.risk_verdict for item in decisions}
        assert verdicts == {"pass", "blocked"}

    def test_rejection_counts_are_aggregated(self, populated):
        counts = DashboardGateway(populated).rejection_counts(SESSION)
        assert counts["risk_exposure"] == 1

    def test_candidates_are_listed(self, populated):
        candidates = DashboardGateway(populated).candidates()
        assert len(candidates) == 1
        assert candidates[0].in_sample == "5.0000"

    def test_default_session_is_the_most_recent(self, populated):
        assert DashboardGateway(populated).default_session() == SESSION

    def test_equity_points_come_from_transactions(self, populated):
        points = DashboardGateway(populated).equity_points(SESSION)
        # one fee transaction was recorded
        assert len(points) >= 1
        assert points[0].value < 0  # a fee reduces cash

    def test_dashboard_assembles_every_panel(self, populated):
        view = DashboardGateway(populated).dashboard()
        assert not view.is_empty
        assert view.portfolio is not None
        assert view.decisions
        assert view.candidates
        assert view.sessions

    def test_to_dict_is_json_serialisable(self, populated):
        import json

        payload = DashboardGateway(populated).dashboard().to_dict()
        assert json.dumps(payload, default=str)
        assert payload["system"]["schema_version"] == 1


# -------------------------------------------------------------- renderer ---
class TestRenderer:
    def test_renders_a_complete_page(self, populated):
        gateway = DashboardGateway(populated)
        markup = render_dashboard(gateway.dashboard())
        assert markup.startswith("<!DOCTYPE html>")
        assert "</html>" in markup
        assert "ShadBotTrader" in markup

    def test_shows_the_stored_numbers(self, populated):
        gateway = DashboardGateway(populated)
        markup = render_dashboard(gateway.dashboard())
        assert "XAUUSD_i" in markup
        assert "2,000.00000" in markup
        assert "risk_exposure" in markup

    def test_empty_database_gets_guidance_not_a_broken_page(self, database):
        markup = render_dashboard(DashboardGateway(database).dashboard())
        assert "Nothing recorded yet" in markup
        assert "run_persistence" in markup

    def test_everything_is_inlined(self, populated):
        """The preview sandbox has no network: no external assets allowed."""
        markup = render_dashboard(DashboardGateway(populated).dashboard())
        assert "<style>" in markup
        assert "http://" not in markup.replace('lang="en"', "")
        assert "cdn" not in markup.lower()
        assert "<script" not in markup.lower()

    def test_html_is_escaped(self, database):
        """A crafted symbol must not become markup."""
        ledger = SqlitePortfolioLedger(database, session_id="x")
        ledger.apply(
            ExecutionResult(
                intent_id="i",
                order_id="o",
                status=ExecutionStatus.FILLED,
                requested_quantity=d("1"),
                fills=[
                    Fill(
                        fill_id="f",
                        order_id="o",
                        symbol=Symbol("<script>alert(1)</script>"),
                        side=OrderSide.BUY,
                        quantity=d("1"),
                        price=Price(d("100")),
                        executed_at=Timestamp(BASE_TIME),
                    )
                ],
            )
        )
        markup = render_dashboard(DashboardGateway(database).dashboard("x"))
        assert "<script>alert" not in markup
        assert "&lt;script&gt;" in markup

    def test_chart_needs_two_points(self, populated):
        """A single dot is not a curve; say so instead of drawing one."""
        markup = render_dashboard(DashboardGateway(populated).dashboard(), [])
        assert "Not enough recorded transactions" in markup

    def test_chart_is_drawn_with_enough_points(self, populated):
        from ShadBotTrader.presentation.viewmodels.models import CashPoint

        points = [
            CashPoint("2026-01-01T00:00", 100.0),
            CashPoint("2026-01-02T00:00", 120.0),
            CashPoint("2026-01-03T00:00", 110.0),
        ]
        markup = render_dashboard(DashboardGateway(populated).dashboard(), points)
        assert "<svg" in markup
        assert "polyline" in markup


# ------------------------------------------- the architectural boundary ----
class TestReadOnlyBoundary:
    def test_gateway_exposes_no_mutating_method(self):
        """Phase 19 §4: the GUI may not execute, train or modify."""
        forbidden = (
            "execute",
            "submit",
            "train",
            "save",
            "delete",
            "insert",
            "update",
            "apply",
            "record",
            "promote",
            "ingest",
        )
        public = [name for name in dir(DashboardGateway) if not name.startswith("_")]
        for name in public:
            assert not any(
                word in name.lower() for word in forbidden
            ), f"DashboardGateway.{name} looks like it mutates state"

    def test_viewmodels_are_frozen(self):
        """A ViewModel is a value: the view cannot alter it."""
        from dataclasses import FrozenInstanceError

        from ShadBotTrader.presentation.viewmodels.models import PositionView

        position = PositionView(
            symbol="X",
            side="long",
            quantity="1",
            average_price="1",
            realized_pnl="0",
            realized_tone="neutral",
            fees="0",
            currency="USD",
            is_flat=False,
        )
        with pytest.raises(FrozenInstanceError):
            position.symbol = "Y"  # type: ignore[misc]

    def test_presentation_never_imports_domain_infrastructure_directly(self):
        """§10: a ViewModel must not reach a repository or database."""
        import ast
        from pathlib import Path

        root = Path(__file__).resolve().parents[3] / "src" / "ShadBotTrader"
        viewmodels = root / "presentation" / "viewmodels"

        for path in viewmodels.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                module = ""
                if isinstance(node, ast.ImportFrom) and node.module:
                    module = node.module
                elif isinstance(node, ast.Import):
                    module = node.names[0].name
                assert (
                    "infrastructure" not in module
                ), f"{path.name} imports infrastructure: {module}"
                assert "domain" not in module, f"{path.name} imports domain: {module}"


class TestEmptinessDetection:
    """Regression guards for what counts as an 'empty' dashboard.

    ``is_empty`` originally checked only sessions and candidates, so a
    database holding real positions rendered the "nothing recorded yet"
    placeholder and the stored state was invisible.
    """

    def test_a_stored_position_is_not_empty(self, database):
        ledger = SqlitePortfolioLedger(database, session_id="only-ledger")
        ledger.apply(
            ExecutionResult(
                intent_id="i",
                order_id="o",
                status=ExecutionStatus.FILLED,
                requested_quantity=d("1"),
                fills=[
                    Fill(
                        fill_id="f",
                        order_id="o",
                        symbol=XAU,
                        side=OrderSide.BUY,
                        quantity=d("1"),
                        price=Price(d("2000")),
                        executed_at=Timestamp(BASE_TIME),
                    )
                ],
            )
        )
        view = DashboardGateway(database).dashboard("only-ledger")
        assert not view.is_empty
        markup = render_dashboard(view)
        assert "Nothing recorded yet" not in markup
        assert "XAUUSD_i" in markup

    def test_a_truly_empty_database_is_empty(self, database):
        assert DashboardGateway(database).dashboard().is_empty

    def test_candidates_alone_are_not_empty(self, database):
        SqliteLearningMemory(database).remember(make_candidate("c1", folds=[winning_fold()]))
        assert not DashboardGateway(database).dashboard().is_empty


class TestSentinelDisplay:
    """A penalty marker must not be shown to a user as a number.

    ``RiskAdjustedObjective`` returns -1,000,000 for a run with too few
    trades to judge. Rendering that literally implies a catastrophic
    result rather than an absent one.
    """

    def test_penalty_scores_are_labelled_not_printed(self, database):
        from ShadBotTrader.domain.learning.candidate import Candidate, EvaluationRecord
        from ShadBotTrader.domain.learning.parameter_space import CandidateConfiguration
        from tests.learning_fixtures import make_metrics

        candidate = Candidate("thin", CandidateConfiguration({"lookback": 3}))
        candidate.record_in_sample(
            EvaluationRecord("in_sample", d("-1000000"), make_metrics(trade_count=1))
        )
        SqliteLearningMemory(database).remember(candidate)

        view = DashboardGateway(database).candidates()[0]
        assert view.in_sample == "insufficient"
        assert "-1000000" not in view.in_sample

    def test_real_scores_are_still_shown(self, database):
        SqliteLearningMemory(database).remember(
            make_candidate("real", in_sample="2.5", folds=[winning_fold("1.5")])
        )
        view = DashboardGateway(database).candidates()[0]
        assert view.in_sample == "2.5000"
        assert view.out_of_sample == "1.5000"
