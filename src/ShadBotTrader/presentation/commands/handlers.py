"""Command handlers (Phase 19, section 13).

    Controller -> Command Bus -> Command Handler -> Application Service

Each handler is thin on purpose: it validates input, calls an existing
application service, and turns the outcome into a ``CommandResult``.
None of them contains trading, AI, risk or persistence logic — that all
lives where it already lived. If a handler ever starts calculating
something, it has crossed the line §4 draws.
"""

from __future__ import annotations

import time
from decimal import Decimal
from pathlib import Path
from typing import Callable, Dict, List

from ShadBotTrader.presentation.commands.commands import (
    Command,
    CommandDescriptor,
    CommandField,
    CommandKind,
    CommandResult,
)

Handler = Callable[[Command], CommandResult]


# ---------------------------------------------------------------- registry --
def descriptors() -> List[CommandDescriptor]:
    """Every command the dashboard offers, with its form."""
    return [
        CommandDescriptor(
            kind=CommandKind.FETCH_MARKET_DATA,
            label="Fetch market data",
            description=(
                "Download real candles from MetaTrader 5 and ingest them "
                "through the Data Platform. Requires Windows with the MT5 "
                "terminal running; falls back to the sample CSV otherwise."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD", hint="broker symbol"),
                CommandField("timeframe", "Timeframe", "5M"),
                CommandField("bars", "Bars", "5000", kind="number"),
            ],
            slow=True,
        ),
        CommandDescriptor(
            kind=CommandKind.COMPUTE_FEATURES,
            label="Update features",
            description=(
                "Recompute the standard feature set over the stored candles "
                "and register the definitions in the database."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD_i"),
                CommandField("timeframe", "Timeframe", "5M"),
            ],
            slow=True,
        ),
        CommandDescriptor(
            kind=CommandKind.TRAIN_MODEL,
            label="Retrain the model",
            description=(
                "Roll-forward training of the WaveNet direction classifier. "
                "Needs TensorFlow; each fold trains a fresh model, so keep "
                "the fold count small."
            ),
            fields=[
                CommandField("folds", "Folds", "3", kind="number"),
                CommandField("epochs", "Epochs per fold", "2", kind="number"),
                CommandField("window", "Window size", "8", kind="number"),
            ],
            slow=True,
        ),
        CommandDescriptor(
            kind=CommandKind.RUN_BACKTEST,
            label="Run a backtest",
            description=(
                "Replay the stored candles through the production trading "
                "chain and record the result."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD_i"),
                CommandField("timeframe", "Timeframe", "5M"),
                CommandField("capital", "Capital", "100", kind="number"),
                CommandField("spread", "Spread", "4", kind="number"),
            ],
        ),
        CommandDescriptor(
            kind=CommandKind.RECORD_REPLAY,
            label="Record a replay",
            description=(
                "Run the same backtest with recording on, then write a "
                "player you can watch bar by bar: where it entered, where "
                "it exited and what each trade produced. Opens at /replay."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD_i"),
                CommandField("timeframe", "Timeframe", "5M"),
                CommandField("capital", "Capital", "100", kind="number"),
                CommandField("spread", "Spread", "4", kind="number"),
            ],
        ),
        CommandDescriptor(
            kind=CommandKind.RUN_OPTIMISATION,
            label="Run optimisation",
            description=(
                "Search strategy parameters in-sample, validate the leaders "
                "on unseen folds, and remember the outcome."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD_i"),
                CommandField("timeframe", "Timeframe", "5M"),
                CommandField("folds", "Validation folds", "3", kind="number"),
            ],
            slow=True,
        ),
        CommandDescriptor(
            kind=CommandKind.RUN_TRADING_CYCLE,
            label="Run a trading cycle",
            description=(
                "Evaluate the strategy once against the latest stored candle "
                "and persist the decision, execution and position."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD_i"),
                CommandField("timeframe", "Timeframe", "5M"),
                CommandField("session", "Session", "dashboard"),
            ],
        ),
        CommandDescriptor(
            kind=CommandKind.REFRESH_PROJECT_STATE,
            label="Refresh project state",
            description="Rescan the repository and regenerate the project snapshot.",
        ),
    ]


def descriptor_for(kind: CommandKind) -> CommandDescriptor:
    for descriptor in descriptors():
        if descriptor.kind is kind:
            return descriptor
    raise KeyError(kind)


# ---------------------------------------------------------------- handlers --
class CommandHandlers:
    """Binds commands to the application services that do the work."""

    def __init__(
        self,
        database_path: str | Path,
        storage_root: str | Path = "datasets",
        replay_path: str | Path = "replay.html",
    ):
        self._database_path = Path(database_path)
        self._storage_root = Path(storage_root)
        # Where "Record a replay" writes its player. The server serves this
        # file at /replay, so the two must agree on one location.
        self._replay_path = Path(replay_path)

    @property
    def replay_path(self) -> Path:
        return self._replay_path

    def registry(self) -> Dict[CommandKind, Handler]:
        return {
            CommandKind.FETCH_MARKET_DATA: self.fetch_market_data,
            CommandKind.COMPUTE_FEATURES: self.compute_features,
            CommandKind.TRAIN_MODEL: self.train_model,
            CommandKind.RUN_BACKTEST: self.run_backtest,
            CommandKind.RECORD_REPLAY: self.record_replay,
            CommandKind.RUN_OPTIMISATION: self.run_optimisation,
            CommandKind.RUN_TRADING_CYCLE: self.run_trading_cycle,
            CommandKind.REFRESH_PROJECT_STATE: self.refresh_project_state,
        }

    # -- data ---------------------------------------------------------------
    def fetch_market_data(self, command: Command) -> CommandResult:
        from ShadBotTrader.data_cli import build_service, generate_sample
        from ShadBotTrader.infrastructure.data import mt5_market_data_provider as mt5mod

        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD")
        timeframe = command.text("timeframe", "5M")
        bars = max(command.integer("bars", 5000), 1)
        lines: List[str] = []

        if mt5mod.is_available():
            provider = mt5mod.Mt5MarketDataProvider()
            try:
                service, _, _ = build_service(self._storage_root, provider=provider)
                result = service.ingest(symbol, timeframe, str(bars))
                lines = [
                    "source: MetaTrader 5 (real broker data)",
                    f"raw rows      : {result.raw_row_count}",
                    f"valid candles : {result.candle_count}",
                    f"quality score : {result.quality_report.score.overall}",
                    f"quarantined   : {result.quarantined}",
                ]
            except Exception as error:
                return CommandResult.failure(
                    command.kind,
                    "MetaTrader 5 ingestion failed",
                    str(error),
                    time.monotonic() - started,
                )
            finally:
                provider.shutdown()
        else:
            # Be explicit rather than silently producing synthetic data.
            sample = self._storage_root / "samples" / f"{symbol}_{timeframe}.csv"
            if not sample.exists():
                generate_sample(symbol, timeframe, min(bars, 400), sample)
            service, _, _ = build_service(self._storage_root)
            result = service.ingest(symbol, timeframe, str(sample))
            lines = [
                "MetaTrader5 is not installed (Windows only).",
                "source: generated sample CSV, NOT real market data",
                f"valid candles : {result.candle_count}",
                f"quality score : {result.quality_report.score.overall}",
            ]

        return CommandResult.success(
            command.kind,
            f"Ingested {symbol} {timeframe} (v{result.version})",
            lines,
            time.monotonic() - started,
        )

    # -- features ------------------------------------------------------------
    def compute_features(self, command: Command) -> CommandResult:
        from ShadBotTrader.data_cli import build_service
        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.feature_cli import _build_service as build_feature_service
        from ShadBotTrader.infrastructure.feature.standard_catalog import (
            standard_feature_set_v1,
        )
        from ShadBotTrader.infrastructure.persistence import (
            Database,
            SqliteFeatureRegistry,
        )

        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD_i")
        timeframe = command.text("timeframe", "5M")

        _, store, _ = build_service(self._storage_root)
        candles = store.query(Symbol(symbol), Timeframe(timeframe))
        if not candles:
            return CommandResult.rejected(
                command.kind,
                f"No stored candles for {symbol} {timeframe}. Fetch data first.",
            )

        feature_set = standard_feature_set_v1()
        try:
            service, _, _ = build_feature_service(self._storage_root)
            outcome = service.compute_set(
                feature_set=feature_set,
                symbol=Symbol(symbol),
                timeframe=Timeframe(timeframe),
                candles=candles,
                source_dataset_id=(f"csv.market_candle.{symbol}.{timeframe}.L3_normalized"),
                dataset_version=1,
            )
        except Exception as error:
            return CommandResult.failure(
                command.kind,
                "Feature computation failed",
                str(error),
                time.monotonic() - started,
            )

        # record the catalogue in the database so the dashboard can show it
        database = Database(self._database_path)
        registry = SqliteFeatureRegistry(database)
        for definition in feature_set.definitions:
            registry.register(definition)
        database.close()

        quarantined = sum(1 for item in outcome.outcomes if item.quarantined)
        research_only = sum(1 for item in outcome.outcomes if not item.live_compatible)
        return CommandResult.success(
            command.kind,
            f"Computed {len(outcome.outcomes)} features over {len(candles)} candles",
            [
                f"feature set : {outcome.set_name}",
                f"computed    : {len(outcome.outcomes) - quarantined}",
                f"quarantined : {quarantined}",
                f"research    : {research_only} (not live-compatible)",
                f"{len(feature_set.definitions)} definitions registered in the database",
            ],
            time.monotonic() - started,
        )

    # -- AI --------------------------------------------------------------------
    def train_model(self, command: Command) -> CommandResult:
        started = time.monotonic()
        try:
            import tensorflow  # noqa: F401
        except ImportError:
            return CommandResult.rejected(
                command.kind,
                "TensorFlow is not installed — run: pip install -r requirements-ai.txt",
            )

        import subprocess

        folds = max(command.integer("folds", 3), 1)
        epochs = max(command.integer("epochs", 2), 1)
        window = max(command.integer("window", 8), 2)

        try:
            completed = subprocess.run(
                [
                    "python",
                    "scripts/run_ai.py",
                    "--quick",
                    "--folds",
                    str(folds),
                    "--epochs",
                    str(epochs),
                    "--window-size",
                    str(window),
                ],
                capture_output=True,
                text=True,
                timeout=1800,
                cwd=str(Path.cwd()),
            )
        except subprocess.TimeoutExpired:
            return CommandResult.failure(
                command.kind,
                "Training timed out after 30 minutes",
                "Reduce the fold count or epochs.",
                time.monotonic() - started,
            )

        if completed.returncode != 0:
            return CommandResult.failure(
                command.kind,
                "Training failed",
                completed.stderr[-1500:] or completed.stdout[-1500:],
                time.monotonic() - started,
            )

        interesting = [
            line
            for line in completed.stdout.splitlines()
            if any(word in line for word in ("fold", "val_loss", "accuracy", "run_id"))
        ]
        return CommandResult.success(
            command.kind,
            f"Retrained over {folds} fold(s)",
            interesting[-14:],
            time.monotonic() - started,
        )

    # -- simulation --------------------------------------------------------------
    def run_backtest(self, command: Command) -> CommandResult:
        from ShadBotTrader.application.services.backtest_service import BacktestService
        from ShadBotTrader.data_cli import build_service
        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.domain.simulation.session import SimulationConfiguration
        from ShadBotTrader.infrastructure.simulation import MomentumPredictionSource

        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD_i")
        timeframe = command.text("timeframe", "5M")

        _, store, _ = build_service(self._storage_root)
        candles = store.query(Symbol(symbol), Timeframe(timeframe))
        if not candles:
            return CommandResult.rejected(
                command.kind,
                f"No stored candles for {symbol} {timeframe}. Fetch data first.",
            )

        try:
            service = BacktestService(
                configuration=SimulationConfiguration(
                    initial_capital=Decimal(str(command.number("capital", 100.0))),
                    spread=Decimal(str(command.number("spread", 4.0))),
                    commission_rate=Decimal("0.0001"),
                    warmup_bars=20,
                ),
                base_quantity=Decimal("0.01"),
            )
            result = service.run(
                f"dashboard-{symbol}",
                Symbol(symbol),
                Timeframe(timeframe),
                candles,
                prediction_source=MomentumPredictionSource(lookback=6),
            )
        except Exception as error:
            return CommandResult.failure(
                command.kind, "Backtest failed", str(error), time.monotonic() - started
            )

        metrics = result.metrics
        hit = metrics.hit_rate
        return CommandResult.success(
            command.kind,
            f"Backtested {result.bars_processed} bars",
            [
                f"trades      : {metrics.trade_count}",
                f"return      : {metrics.total_return:.4f} "
                f"({metrics.total_return_percent:.2f}%)",
                f"max drawdown: {metrics.max_drawdown_percent:.2f}%",
                f"hit rate    : {f'{hit:.3f}' if hit is not None else 'n/a'}",
                f"fees        : {metrics.total_fees:.4f}",
            ],
            time.monotonic() - started,
        )

    def record_replay(self, command: Command) -> CommandResult:
        """Run a recorded backtest and write the player to disk."""
        from ShadBotTrader.application.services.backtest_service import BacktestService
        from ShadBotTrader.data_cli import build_service
        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.domain.simulation.session import SimulationConfiguration
        from ShadBotTrader.infrastructure.simulation import MomentumPredictionSource
        from ShadBotTrader.presentation.web.replay_renderer import render_replay

        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD_i")
        timeframe = command.text("timeframe", "5M")

        _, store, _ = build_service(self._storage_root)
        candles = store.query(Symbol(symbol), Timeframe(timeframe))
        if not candles:
            return CommandResult.rejected(
                command.kind,
                f"No stored candles for {symbol} {timeframe}. Fetch data first.",
            )

        try:
            service = BacktestService(
                configuration=SimulationConfiguration(
                    initial_capital=Decimal(str(command.number("capital", 100.0))),
                    spread=Decimal(str(command.number("spread", 4.0))),
                    commission_rate=Decimal("0.0001"),
                    warmup_bars=20,
                ),
                base_quantity=Decimal("0.01"),
            )
            result = service.run(
                f"replay-{symbol}",
                Symbol(symbol),
                Timeframe(timeframe),
                candles,
                prediction_source=MomentumPredictionSource(lookback=6),
                record_replay=True,
            )
        except Exception as error:
            return CommandResult.failure(
                command.kind, "Replay run failed", str(error), time.monotonic() - started
            )

        tape = result.tape
        if tape is None:  # pragma: no cover - recording was requested
            return CommandResult.failure(
                command.kind, "The run produced no replay", "", time.monotonic() - started
            )

        markup = render_replay(tape, result.metrics)
        self._replay_path.parent.mkdir(parents=True, exist_ok=True)
        self._replay_path.write_text(markup, encoding="utf-8")

        trips = tape.round_trips()
        wins = sum(1 for trip in trips if trip["result"] == "win")
        return CommandResult.success(
            command.kind,
            f"Recorded {len(tape.bars)} bars — open /replay to watch it",
            [
                f"fills         : {len(tape.markers)}",
                f"closed trades : {len(trips)} ({wins} win / {len(trips) - wins} loss)",
                f"return        : {result.metrics.total_return:.4f} "
                f"({result.metrics.total_return_percent:.2f}%)",
                f"written to    : {self._replay_path}",
            ],
            time.monotonic() - started,
        )

    def run_optimisation(self, command: Command) -> CommandResult:
        from ShadBotTrader.application.services.optimisation_service import (
            OptimisationService,
            default_baseline,
        )
        from ShadBotTrader.data_cli import build_service
        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.domain.simulation.session import SimulationConfiguration
        from ShadBotTrader.infrastructure.persistence import (
            Database,
            SqliteLearningMemory,
        )

        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD_i")
        timeframe = command.text("timeframe", "5M")
        folds = max(command.integer("folds", 3), 2)

        _, store, _ = build_service(self._storage_root)
        candles = store.query(Symbol(symbol), Timeframe(timeframe))
        if not candles:
            return CommandResult.rejected(
                command.kind,
                f"No stored candles for {symbol} {timeframe}. Fetch data first.",
            )

        database = Database(self._database_path)
        try:
            service = OptimisationService(
                symbol=Symbol(symbol),
                timeframe=Timeframe(timeframe),
                simulation_config=SimulationConfiguration(
                    initial_capital=Decimal("100"),
                    spread=Decimal("4"),
                    commission_rate=Decimal("0.0001"),
                    warmup_bars=10,
                ),
            )
            # results land in the database so the dashboard shows them
            service.memory = SqliteLearningMemory(database)
            result = service.run(
                f"dashboard-{symbol}",
                {"lookback": [3, 6, 12], "strategy_min_confidence": [0.55, 0.65]},
                candles,
                baseline=default_baseline(),
                fold_count=folds,
            )
        except Exception as error:
            database.close()
            return CommandResult.failure(
                command.kind,
                "Optimisation failed",
                str(error),
                time.monotonic() - started,
            )
        database.close()

        verdict = result.verdict
        if verdict is None:
            outcome = "no candidate reached the gate"
        elif verdict.approved:
            outcome = f"APPROVED — {verdict.reason}"
        else:
            reason = verdict.rejection_reason
            outcome = f"REJECTED ({reason.value if reason else 'unknown'})"

        return CommandResult.success(
            command.kind,
            f"Evaluated {len(result.evaluated)} candidate(s)",
            [
                f"validated : {len(result.validated)}",
                f"promoted  : {result.promoted}",
                f"gate      : {outcome}",
                "A rejection is a valid outcome: the gate refuses anything",
                "that cannot prove itself out of sample.",
            ],
            time.monotonic() - started,
        )

    # -- trading -------------------------------------------------------------
    def run_trading_cycle(self, command: Command) -> CommandResult:
        from ShadBotTrader.application.services.execution_service import ExecutionService
        from ShadBotTrader.application.services.trading_decision_service import (
            TradingDecisionService,
        )
        from ShadBotTrader.data_cli import build_service
        from ShadBotTrader.domain.execution.market_view import (
            ExecutionContext,
        )
        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy
        from ShadBotTrader.domain.strategy.strategy_context import (
            PortfolioView,
            PredictionView,
            StrategyContext,
        )
        from ShadBotTrader.infrastructure.execution import (
            DefaultIntentResolver,
            SimulatedExecutionVenue,
        )
        from ShadBotTrader.infrastructure.persistence import (
            Database,
            SqliteDecisionJournal,
            SqliteExecutionJournal,
            SqlitePortfolioLedger,
        )
        from ShadBotTrader.infrastructure.simulation import MomentumPredictionSource
        from ShadBotTrader.infrastructure.simulation.candle_data_provider import (
            CandleMarketDataProvider,
        )
        from ShadBotTrader.infrastructure.trading import (
            AiDirectionalStrategy,
            DefaultIntentFactory,
            DefaultSignalValidator,
            PolicyRiskGate,
            PositionAwareDecisionEngine,
        )

        started = time.monotonic()
        symbol_text = command.text("symbol", "XAUUSD_i")
        timeframe_text = command.text("timeframe", "5M")
        session = command.text("session", "dashboard")
        symbol = Symbol(symbol_text)
        timeframe = Timeframe(timeframe_text)

        _, store, _ = build_service(self._storage_root)
        candles = store.query(symbol, timeframe)
        if len(candles) < 20:
            return CommandResult.rejected(
                command.kind,
                f"Need at least 20 candles for {symbol_text}; found {len(candles)}.",
            )

        # A prediction for the latest bar, produced by the same source the
        # backtester uses — the GUI does not compute anything itself.
        provider = CandleMarketDataProvider(symbol, candles, spread=Decimal("4"))
        source = MomentumPredictionSource(lookback=6)
        events = provider.events()
        for event in events:
            source.observe(event)
        latest = events[-1]
        value = source.predict(latest)
        if value is None:
            return CommandResult.rejected(command.kind, "Not enough history for a prediction.")

        database = Database(self._database_path)
        ledger = SqlitePortfolioLedger(database, session_id=session, starting_cash=Decimal("100"))
        trading = TradingDecisionService(
            strategies=[AiDirectionalStrategy(min_confidence=0.55)],
            decision_engine=PositionAwareDecisionEngine(),
            risk_gate=PolicyRiskGate(RiskPolicy(max_open_positions=2)),
            intent_factory=DefaultIntentFactory(base_quantity=Decimal("0.01")),
            validator=DefaultSignalValidator(max_signal_age_seconds=10**9),
            journal=SqliteDecisionJournal(database, session_id=session),
        )
        execution = ExecutionService(
            resolver=DefaultIntentResolver(),
            venue=SimulatedExecutionVenue(commission_rate=Decimal("0.0001")),
            ledger=ledger,
            journal=SqliteExecutionJournal(database, session_id=session),
        )

        position = ledger.position(symbol)
        context = StrategyContext(
            timestamp=latest.event_time,
            symbol=symbol,
            timeframe=timeframe,
            predictions=[
                PredictionView(
                    model_id="gold_direction",
                    model_version=1,
                    value=value,
                    confidence=source.confidence(latest),
                    generated_at=latest.event_time,
                )
            ],
            portfolio=PortfolioView(
                equity=ledger.cash.amount,
                open_position_quantity=position.signed_quantity,
                open_position_count=0 if position.is_flat else 1,
            ),
        )

        outcome = trading.evaluate(context)
        lines = [
            f"prediction : {value:.4f}",
            f"signal     : {outcome.signal.signal_type.value if outcome.signal else '-'}",
            f"decision   : " f"{outcome.decision.decision_type.value if outcome.decision else '-'}",
        ]

        if outcome.intent is None:
            lines.append(f"no intent  : {outcome.rejected_reason or 'nothing to do'}")
            database.close()
            return CommandResult.success(
                command.kind,
                "Cycle complete — no trade",
                lines,
                time.monotonic() - started,
            )

        quote = provider.quote_for(latest.candle) if latest.candle else None
        if quote is None:
            database.close()
            return CommandResult.failure(command.kind, "No quote for the latest bar")

        executed = execution.execute(
            outcome.intent,
            ExecutionContext(
                timestamp=latest.event_time,
                quote=quote,
                position=position,
                equity=ledger.cash.amount,
            ),
        )
        if executed.executed and executed.result is not None:
            lines.append(
                f"filled     : {executed.result.filled_quantity} @ "
                f"{executed.result.average_fill_price}"
            )
        else:
            lines.append(f"not filled : {executed.rejected_reason}")
        lines.append(f"position   : {ledger.position(symbol)}")
        database.close()

        return CommandResult.success(
            command.kind,
            f"Cycle complete for session '{session}'",
            lines,
            time.monotonic() - started,
        )

    # -- project ----------------------------------------------------------------
    def refresh_project_state(self, command: Command) -> CommandResult:
        from ShadBotTrader.intelligence import main as intelligence_main

        started = time.monotonic()
        try:
            code = intelligence_main(["--project-root", str(Path.cwd())])
        except Exception as error:
            return CommandResult.failure(
                command.kind,
                "Project scan failed",
                str(error),
                time.monotonic() - started,
            )
        if code != 0:
            return CommandResult.failure(command.kind, f"Scanner exited with {code}")
        return CommandResult.success(
            command.kind,
            "Project state regenerated",
            ["written to project_state/generated/"],
            time.monotonic() - started,
        )
