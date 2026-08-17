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
    CommandStatus,
)

Handler = Callable[[Command], CommandResult]

#: The two timeframes the platform trains on: 5M feeds the signal model,
#: 1H feeds the range model (Phase 29 §2). They are fetched together
#: because building the dataset with only one of them is not a smaller
#: dataset — it is a missing model.
TRAINING_TIMEFRAMES: tuple[str, ...] = ("5M", "1H")


def parse_timeframes(raw: str) -> List[str]:
    """Split a ``5M,1H`` field into an ordered, de-duplicated list."""
    seen: List[str] = []
    for token in (raw or "").replace(";", ",").replace(" ", ",").split(","):
        cleaned = token.strip().upper()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


# ---------------------------------------------------------------- registry --
def descriptors() -> List[CommandDescriptor]:
    """Every command the dashboard offers, with its form."""
    return [
        CommandDescriptor(
            kind=CommandKind.FETCH_MARKET_DATA,
            label="Fetch market data",
            description=(
                "Download real candles from MetaTrader 5 for EVERY listed "
                "timeframe and append them to the stored history. Requires "
                "Windows with the MT5 terminal running — generated sample "
                "data is never substituted for real prices."
            ),
            fields=[
                CommandField(
                    "symbol",
                    "Symbol",
                    "XAUUSD",
                    hint="platform name; the broker's alias is applied automatically",
                ),
                CommandField(
                    "timeframe",
                    "Timeframes",
                    "5M,1H",
                    hint="comma separated — 5M feeds the signal model, 1H the range model",
                ),
                CommandField("bars", "Bars", "5000", kind="number"),
                CommandField(
                    "max_candles",
                    "Keep at most",
                    "100000",
                    kind="number",
                    hint="rolling limit — oldest candles are dropped",
                ),
                CommandField(
                    "allow_gap",
                    "Allow gap",
                    "0",
                    hint="1 = accept a discontinuity the broker could not fill",
                ),
            ],
            slow=True,
            group="Data",
        ),
        CommandDescriptor(
            kind=CommandKind.COMPUTE_FEATURES,
            label="Update features",
            description=(
                "Recompute the standard feature set over the stored candles "
                "and register the definitions in the database."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField("timeframe", "Timeframe", "5M"),
            ],
            slow=True,
            group="Data",
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
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.RUN_BACKTEST,
            label="Run a backtest",
            description=(
                "Replay the stored candles through the production trading "
                "chain and record the result."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField("timeframe", "Timeframe", "5M"),
                CommandField("capital", "Capital", "100", kind="number"),
                CommandField("spread", "Spread", "4", kind="number"),
            ],
            group="Simulation",
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
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField("timeframe", "Timeframe", "5M"),
                CommandField("capital", "Capital", "100", kind="number"),
                CommandField("spread", "Spread", "4", kind="number"),
            ],
            group="Simulation",
        ),
        CommandDescriptor(
            kind=CommandKind.RUN_OPTIMISATION,
            label="Run optimisation",
            description=(
                "Search strategy parameters in-sample, validate the leaders "
                "on unseen folds, and remember the outcome."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField("timeframe", "Timeframe", "5M"),
                CommandField("folds", "Validation folds", "3", kind="number"),
            ],
            slow=True,
            group="Simulation",
        ),
        CommandDescriptor(
            kind=CommandKind.RUN_TRADING_CYCLE,
            label="Run a trading cycle",
            description=(
                "Evaluate the strategy once against the latest stored candle "
                "and persist the decision, execution and position."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField("timeframe", "Timeframe", "5M"),
                CommandField("session", "Session", "dashboard"),
            ],
            group="Trading",
        ),
        CommandDescriptor(
            kind=CommandKind.REFRESH_PROJECT_STATE,
            label="Refresh project state",
            description="Rescan the repository and regenerate the project snapshot.",
            group="Operations",
        ),
        # -- accounts (Phase 32) -----------------------------------------
        CommandDescriptor(
            kind=CommandKind.ADD_ACCOUNT,
            label="Add account",
            description=(
                "Register a MetaTrader 5 account. The password is NOT stored: "
                "set it in the environment variable shown after saving."
            ),
            fields=[
                CommandField("name", "Profile name", "alpari-demo"),
                CommandField("login", "Login", "", kind="number"),
                CommandField("server", "Server", "Alpari-MT5-Demo"),
                CommandField("terminal_path", "Terminal path", "", hint="optional"),
                CommandField("is_demo", "Demo account", "1", hint="1 = demo, 0 = live"),
            ],
            group="Accounts",
        ),
        CommandDescriptor(
            kind=CommandKind.ACTIVATE_ACCOUNT,
            label="Switch account",
            description="Make a profile the active one; every run then uses it.",
            fields=[CommandField("name", "Profile name", "")],
            group="Accounts",
        ),
        CommandDescriptor(
            kind=CommandKind.CHECK_ACCOUNT,
            label="Check account",
            description=(
                "Connect to the broker and confirm every mapped symbol exists. "
                "Leave the name empty to check the active profile."
            ),
            fields=[CommandField("name", "Profile name", "")],
            group="Accounts",
        ),
        CommandDescriptor(
            kind=CommandKind.MAP_SYMBOL,
            label="Map a symbol",
            description=(
                "Tell this profile what its broker calls an instrument, "
                "e.g. XAUUSD -> XAUUSD_i. Datasets keep the canonical name."
            ),
            fields=[
                CommandField("name", "Profile name", ""),
                CommandField("canonical", "Platform symbol", "XAUUSD"),
                CommandField("broker", "Broker symbol", "XAUUSD_i"),
            ],
            group="Accounts",
        ),
        CommandDescriptor(
            kind=CommandKind.AUTO_MAP_SYMBOLS,
            label="Detect symbol names",
            description=(
                "Ask the broker what it calls each instrument and suggest a "
                "mapping. Suggestions are applied only when you confirm."
            ),
            fields=[
                CommandField("name", "Profile name", ""),
                CommandField("symbols", "Symbols", "XAUUSD,EURUSD,GBPUSD"),
                CommandField("apply", "Apply suggestions", "0", hint="1 = save them"),
            ],
            slow=True,
            group="Accounts",
        ),
        CommandDescriptor(
            kind=CommandKind.REMOVE_ACCOUNT,
            label="Remove account",
            description="Delete a profile. The broker account itself is untouched.",
            fields=[CommandField("name", "Profile name", "")],
            danger=True,
            group="Accounts",
        ),
        # -- data ----------------------------------------------------------
        CommandDescriptor(
            kind=CommandKind.BUILD_DATASET,
            label="Build training dataset",
            description=(
                "Build TWO separate datasets from the stored real candles: "
                "5M for the signal model and 1H for the range model. Each "
                "gets its own matrix of 123 columns. Real data only — "
                "'Fetch market data' must have run for both timeframes."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField("candles", "Candles per timeframe", "100000", kind="number"),
            ],
            slow=True,
            group="Data",
        ),
        CommandDescriptor(
            kind=CommandKind.WEEKLY_UPDATE,
            label="Weekly update",
            description=(
                "Back up, refresh the dataset (full feature recompute) and "
                "prepare the models for continued training."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField("candles", "Candles", "100000", kind="number"),
                CommandField("force", "Ignore the 7-day gate", "0"),
            ],
            slow=True,
            group="Data",
        ),
        # -- AI --------------------------------------------------------------
        CommandDescriptor(
            kind=CommandKind.TRAIN_DUAL_MODELS,
            label="Train both models",
            description=(
                "Roll-forward training of the range model (1H high/low) and "
                "the signal model (5M buy/sell/hold)."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField("epochs", "Epochs", "1", kind="number"),
                CommandField("folds", "Folds", "2", kind="number"),
                CommandField("window", "Window rows", "500", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        # -- trading ---------------------------------------------------------
        CommandDescriptor(
            kind=CommandKind.RUN_EXECUTION_DEMO,
            label="Run execution demo",
            description="Drive one intent through resolver, venue and ledger.",
            fields=[CommandField("symbol", "Symbol", "XAUUSD")],
            group="Trading",
        ),
        CommandDescriptor(
            kind=CommandKind.RUN_LIVE_TICK,
            label="Run one live tick",
            description=(
                "One five-minute cycle: buffers, both models, strategy, risk " "gate and execution."
            ),
            fields=[CommandField("symbol", "Symbol", "XAUUSD")],
            slow=True,
            group="Trading",
        ),
        # -- operations --------------------------------------------------------
        CommandDescriptor(
            kind=CommandKind.BACKUP_DATABASE,
            label="Back up the database",
            description="Take a backup and verify it can be read back.",
            fields=[CommandField("note", "Note", "manual backup")],
            group="Operations",
        ),
        CommandDescriptor(
            kind=CommandKind.HEALTH_CHECK,
            label="Health check",
            description="Liveness, readiness and every dependency.",
            group="Operations",
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
        account_store: str | Path = "configs/accounts.json",
    ):
        self._database_path = Path(database_path)
        self._storage_root = Path(storage_root)
        self._account_store = Path(account_store)
        # Where "Record a replay" writes its player. The server serves this
        # file at /replay, so the two must agree on one location.
        self._replay_path = Path(replay_path)

    @property
    def replay_path(self) -> Path:
        return self._replay_path

    def registry(self) -> Dict[CommandKind, Handler]:
        registry: Dict[CommandKind, Handler] = {
            CommandKind.FETCH_MARKET_DATA: self.fetch_market_data,
            CommandKind.COMPUTE_FEATURES: self.compute_features,
            CommandKind.TRAIN_MODEL: self.train_model,
            CommandKind.RUN_BACKTEST: self.run_backtest,
            CommandKind.RECORD_REPLAY: self.record_replay,
            CommandKind.RUN_OPTIMISATION: self.run_optimisation,
            CommandKind.RUN_TRADING_CYCLE: self.run_trading_cycle,
            CommandKind.REFRESH_PROJECT_STATE: self.refresh_project_state,
        }
        # Phase 32 handlers live in their own class; merged here so the
        # bus still sees a single flat registry.
        accounts = AccountCommandHandlers(
            self._database_path, self._storage_root, self._account_store
        )
        registry.update(
            {
                CommandKind.ADD_ACCOUNT: accounts.add_account,
                CommandKind.ACTIVATE_ACCOUNT: accounts.activate_account,
                CommandKind.REMOVE_ACCOUNT: accounts.remove_account,
                CommandKind.CHECK_ACCOUNT: accounts.check_account,
                CommandKind.MAP_SYMBOL: accounts.map_symbol,
                CommandKind.AUTO_MAP_SYMBOLS: accounts.auto_map_symbols,
                CommandKind.BUILD_DATASET: accounts.build_dataset,
                CommandKind.WEEKLY_UPDATE: accounts.weekly_update,
                CommandKind.TRAIN_DUAL_MODELS: accounts.train_dual_models,
                CommandKind.RUN_EXECUTION_DEMO: accounts.run_execution_demo,
                CommandKind.RUN_LIVE_TICK: accounts.run_live_tick,
                CommandKind.BACKUP_DATABASE: accounts.backup_database,
                CommandKind.HEALTH_CHECK: accounts.health_check,
            }
        )
        return registry

    # -- data ---------------------------------------------------------------
    def active_profile(self):
        """The active broker profile, or None when none is configured.

        Returned rather than raised: every run must still work on sample
        data before a broker is set up.
        """
        from ShadBotTrader.infrastructure.account import AccountProfileStore

        try:
            return AccountProfileStore(self._account_store).active()
        except Exception:
            return None

    def broker_symbol(self, canonical: str) -> tuple[str, str]:
        """Translate a platform symbol for the active broker.

        Returns ``(broker_symbol, note)``. The dataset keeps the canonical
        name so that switching brokers does not fragment history into
        XAUUSD / XAUUSD_i / GOLD copies of the same instrument.
        """
        profile = self.active_profile()
        if profile is None:
            return canonical, ""
        translated = profile.broker_symbol(canonical)
        if translated == canonical:
            return translated, f"account: {profile.name}"
        return translated, f"account: {profile.name} ({canonical} -> {translated})"

    def fetch_market_data(self, command: Command) -> CommandResult:
        """Download real candles for every requested timeframe.

        Phase 35 changed two things the operator kept tripping over:

        * ``timeframe`` accepts a list (``5M,1H``) and each one is
          fetched in the same run, because the training dataset needs
          both and fetching one silently left the other empty.
        * candles are stored under the **canonical** symbol even though
          they are fetched under the broker's spelling, so ``XAUUSD`` and
          ``XAUUSD_i`` stop being two disconnected datasets.
        """
        from ShadBotTrader.application.services.dataset_update_service import (
            DatasetUpdateService,
        )
        from ShadBotTrader.data_cli import build_service
        from ShadBotTrader.infrastructure.data import mt5_market_data_provider as mt5mod

        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        timeframes = parse_timeframes(command.text("timeframe", "5M,1H"))
        bars = max(command.integer("bars", 5000), 1)
        allow_gap = command.text("allow_gap", "0").strip() == "1"
        max_candles = max(command.integer("max_candles", 100_000), 1000)

        if not timeframes:
            return CommandResult.rejected(
                command.kind, "No timeframe given. Use for example: 5M,1H"
            )

        if not mt5mod.is_available():
            # Phase 35: no synthetic fallback. Silently ingesting a sine
            # wave under a real symbol is how a model ends up trained on
            # fiction that nobody can tell apart from market data.
            return CommandResult.rejected(
                command.kind,
                "MetaTrader 5 is not available, and this platform no longer "
                "substitutes generated candles for real ones. Run the "
                "dashboard on Windows with the MT5 terminal open and an "
                "account configured under 'Accounts'.",
            )

        broker_symbol, account_note = self.broker_symbol(symbol)
        profile = self.active_profile()
        if profile is not None:
            provider = mt5mod.Mt5MarketDataProvider(
                login=profile.login,
                password=profile.resolve_password(),
                server=profile.server,
                terminal_path=profile.terminal_path or None,
            )
        else:
            provider = mt5mod.Mt5MarketDataProvider()

        lines: List[str] = [
            "source: MetaTrader 5 (real broker data)",
            account_note or "account: terminal session",
            f"fetched as    : {broker_symbol}",
            f"stored as     : {symbol} (canonical)",
        ]
        headline: List[str] = []
        refused: List[str] = []

        try:
            _, store, _ = build_service(self._storage_root, provider=provider)
            updater = DatasetUpdateService(store, provider=provider, max_candles=max_candles)
            for timeframe in timeframes:
                lines.append("")
                lines.append(f"--- {timeframe} ---")
                try:
                    update = updater.fetch_and_update(
                        broker_symbol,
                        timeframe,
                        bars=bars,
                        allow_gap=allow_gap,
                        store_as=symbol,
                    )
                except Exception as error:
                    refused.append(timeframe)
                    lines.append(f"FAILED: {type(error).__name__}: {error}")
                    continue

                lines.extend(update.summary_lines())
                if update.refused:
                    refused.append(timeframe)
                else:
                    headline.append(
                        f"{timeframe} +{update.added_count:,} " f"({update.final_count:,} stored)"
                    )
        finally:
            provider.shutdown()

        lines.append("")
        lines.append("See the candles: open /data")

        if refused:
            lines.append("")
            lines.append(
                "A refused timeframe left its stored dataset untouched. "
                "Re-run when the broker can supply the missing range, or "
                "tick 'Allow gap' to accept the discontinuity deliberately."
            )
            return CommandResult.failure(
                command.kind,
                f"{symbol}: {len(refused)} of {len(timeframes)} timeframe(s) "
                f"refused ({', '.join(refused)})",
                "\n".join(lines),
                time.monotonic() - started,
            )

        return CommandResult.success(
            command.kind,
            f"{symbol}: " + " | ".join(headline),
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
        symbol = command.text("symbol", "XAUUSD")
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
                "",
                "Inspect them: open /data",
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
        symbol = command.text("symbol", "XAUUSD")
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
        symbol = command.text("symbol", "XAUUSD")
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
        symbol = command.text("symbol", "XAUUSD")
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
        symbol_text = command.text("symbol", "XAUUSD")
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


class AccountCommandHandlers:
    """Handlers for the Phase 32 account and operations commands.

    Separated from :class:`CommandHandlers` so the original class stays
    focused; both are merged into one registry by
    :meth:`CommandHandlers.registry`.
    """

    def __init__(
        self,
        database_path: "str | Path",
        storage_root: "str | Path" = "datasets",
        account_store: "str | Path" = "configs/accounts.json",
    ) -> None:
        self._database_path = Path(database_path)
        self._storage_root = Path(storage_root)
        self._account_store = Path(account_store)

    # -- helpers ------------------------------------------------------------
    def _store(self):
        from ShadBotTrader.infrastructure.account import AccountProfileStore

        return AccountProfileStore(self._account_store)

    def active_profile(self):
        """The active broker profile, or None when none is configured.

        Used to translate symbols; a missing profile is not an error
        because the canonical name is the default anyway.
        """
        try:
            return self._store().active()
        except Exception:
            return None

    def _profile(self, command: Command):
        """The named profile, or the active one when no name is given."""
        store = self._store()
        name = command.text("name", "").strip()
        book = store.load()
        if name:
            return store, book.get(name)
        active = book.active_profile
        if active is None:
            raise LookupError("No account profile exists yet. Use 'Add account' first.")
        return store, active

    # -- accounts -----------------------------------------------------------
    def add_account(self, command: Command) -> CommandResult:
        started = time.monotonic()
        name = command.text("name", "").strip()
        login = command.integer("login", 0)
        server = command.text("server", "").strip()

        if not name or login <= 0 or not server:
            return CommandResult.rejected(command.kind, "name, login and server are all required")

        try:
            profile = self._store().add(
                name=name,
                login=login,
                server=server,
                terminal_path=command.text("terminal_path", "").strip(),
                is_demo=command.text("is_demo", "1").strip() != "0",
                make_active=True,
            )
        except Exception as error:
            return CommandResult.failure(
                command.kind,
                "Could not add the account",
                str(error),
                time.monotonic() - started,
            )

        lines = [
            f"login    : {profile.login} @ {profile.server}",
            f"type     : {'demo' if profile.is_demo else 'LIVE'}",
            "",
            "The password is NOT stored. Set it in your shell:",
            f"    $env:{profile.password_variable} = 'your-password'",
            "",
            "Or leave it unset to use the terminal's existing session.",
        ]
        return CommandResult.success(
            command.kind,
            f"Added '{name}' and made it active",
            lines,
            time.monotonic() - started,
        )

    def activate_account(self, command: Command) -> CommandResult:
        started = time.monotonic()
        name = command.text("name", "").strip()
        if not name:
            return CommandResult.rejected(command.kind, "a profile name is required")
        try:
            profile = self._store().activate(name)
        except Exception as error:
            return CommandResult.failure(
                command.kind,
                "Could not switch account",
                str(error),
                time.monotonic() - started,
            )
        return CommandResult.success(
            command.kind,
            f"'{name}' is now the active account",
            [
                f"login  : {profile.login} @ {profile.server}",
                f"type   : {'demo' if profile.is_demo else 'LIVE'}",
                f"symbols: {profile.symbol_map.to_dict() or 'no aliases'}",
            ],
            time.monotonic() - started,
        )

    def remove_account(self, command: Command) -> CommandResult:
        started = time.monotonic()
        name = command.text("name", "").strip()
        if not name:
            return CommandResult.rejected(command.kind, "a profile name is required")
        try:
            self._store().remove(name)
        except Exception as error:
            return CommandResult.failure(
                command.kind,
                "Could not remove the account",
                str(error),
                time.monotonic() - started,
            )
        remaining = self._store().load()
        return CommandResult.success(
            command.kind,
            f"Removed '{name}'",
            [
                f"remaining: {', '.join(remaining.names) or 'none'}",
                f"active   : {remaining.active or 'none'}",
            ],
            time.monotonic() - started,
        )

    def check_account(self, command: Command) -> CommandResult:
        from ShadBotTrader.infrastructure.account import AccountConnector

        started = time.monotonic()
        try:
            store, profile = self._profile(command)
        except Exception as error:
            return CommandResult.rejected(command.kind, str(error))

        report = AccountConnector(store).check(profile)
        if not report.connected:
            return CommandResult.failure(
                command.kind,
                f"Cannot reach the broker for '{profile.name}'",
                report.error + "\n\nIs MetaTrader 5 running and logged in?",
                time.monotonic() - started,
            )

        return CommandResult.success(
            command.kind,
            f"'{profile.name}' is reachable"
            + ("" if report.is_usable else " — but some symbols are missing"),
            report.summary_lines(),
            time.monotonic() - started,
        )

    def map_symbol(self, command: Command) -> CommandResult:
        started = time.monotonic()
        canonical = command.text("canonical", "").strip()
        broker = command.text("broker", "").strip()
        if not canonical or not broker:
            return CommandResult.rejected(
                command.kind, "both the platform and broker symbol are required"
            )
        try:
            store, profile = self._profile(command)
            updated = store.set_symbol(profile.name, canonical, broker)
        except Exception as error:
            return CommandResult.failure(
                command.kind,
                "Could not map the symbol",
                str(error),
                time.monotonic() - started,
            )
        return CommandResult.success(
            command.kind,
            f"{canonical} -> {broker} on '{updated.name}'",
            [f"{key} -> {value}" for key, value in sorted(updated.symbol_map.aliases.items())],
            time.monotonic() - started,
        )

    def auto_map_symbols(self, command: Command) -> CommandResult:
        from ShadBotTrader.infrastructure.account import AccountConnector

        started = time.monotonic()
        try:
            store, profile = self._profile(command)
        except Exception as error:
            return CommandResult.rejected(command.kind, str(error))

        wanted = [
            item.strip() for item in command.text("symbols", "XAUUSD").split(",") if item.strip()
        ]
        try:
            found = AccountConnector(store).auto_map(profile, wanted)
        except Exception as error:
            return CommandResult.failure(
                command.kind,
                "Could not read the broker's symbol list",
                str(error),
                time.monotonic() - started,
            )

        apply = command.text("apply", "0").strip() == "1"
        lines: List[str] = []
        for canonical in wanted:
            suggestion = found.get(canonical.strip().upper())
            if suggestion is None:
                lines.append(f"{canonical:<10} -> NOT FOUND at this broker")
                continue
            lines.append(f"{canonical:<10} -> {suggestion}")
            if apply:
                store.set_symbol(profile.name, canonical, suggestion)

        lines.append("")
        lines.append(
            "Applied and saved."
            if apply
            else "Suggestions only — re-run with 'Apply suggestions' = 1 to save."
        )
        return CommandResult.success(
            command.kind,
            f"Matched {len(found)} of {len(wanted)} symbol(s)",
            lines,
            time.monotonic() - started,
        )

    # -- data ---------------------------------------------------------------
    def missing_timeframes(self, symbol: str) -> List[str]:
        """Training timeframes that have no stored candles yet.

        Checked before the build rather than during it, so the operator
        is told which button to press instead of reading a stack trace
        three minutes into a feature computation.
        """
        from ShadBotTrader.data_cli import build_service
        from ShadBotTrader.infrastructure.data.symbol_scope import (
            resolve_stored_symbol,
        )

        try:
            _, store, _ = build_service(self._storage_root)
        except Exception:
            return []

        profile = self.active_profile()
        missing: List[str] = []
        for timeframe in TRAINING_TIMEFRAMES:
            try:
                found = resolve_stored_symbol(store, symbol, timeframe, profile).found
            except Exception:
                found = False
            if not found:
                missing.append(timeframe)
        return missing

    def build_dataset(self, command: Command) -> CommandResult:
        """Build the 5M and the 1H dataset — two matrices, one run."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        candles = max(command.integer("candles", 100_000), 1000)

        missing = self.missing_timeframes(symbol)
        if missing:
            return CommandResult.rejected(
                command.kind,
                f"No stored candles for {symbol} {', '.join(missing)}. "
                f"The platform builds one dataset per timeframe — 5M for the "
                f"signal model and 1H for the range model — and it will not "
                f"substitute generated data for either. Run 'Fetch market "
                f"data' with Timeframes = 5M,1H first.",
            )

        return self._run_script(
            command,
            [
                "scripts/run_training_dataset.py",
                "--build",
                "--symbol",
                symbol,
                "--candles",
                str(candles),
            ],
            f"Built the 5M and 1H datasets for {symbol}",
            started,
            timeout=3600,
        )

    def weekly_update(self, command: Command) -> CommandResult:
        started = time.monotonic()
        arguments = [
            "scripts/run_weekly_update.py",
            "--symbol",
            command.text("symbol", "XAUUSD"),
            "--candles",
            str(max(command.integer("candles", 100_000), 1000)),
            "--db",
            str(self._database_path),
        ]
        if command.text("force", "0").strip() == "1":
            arguments.append("--force")
        return self._run_script(command, arguments, "Weekly update finished", started, timeout=7200)

    # -- AI -------------------------------------------------------------------
    def train_dual_models(self, command: Command) -> CommandResult:
        started = time.monotonic()
        try:
            import tensorflow  # noqa: F401
        except ImportError:
            return CommandResult.rejected(
                command.kind,
                "TensorFlow is not installed — run: pip install -r requirements-ai.txt",
            )
        return self._run_script(
            command,
            [
                "scripts/run_dual_models.py",
                "--with-features",
                "--symbol",
                command.text("symbol", "XAUUSD"),
                "--epochs",
                str(max(command.integer("epochs", 1), 1)),
                "--folds",
                str(max(command.integer("folds", 2), 1)),
                "--window",
                str(max(command.integer("window", 500), 2)),
            ],
            "Both models trained",
            started,
            timeout=7200,
        )

    # -- trading ---------------------------------------------------------------
    def run_execution_demo(self, command: Command) -> CommandResult:
        started = time.monotonic()
        return self._run_script(
            command, ["scripts/run_execution.py"], "Execution demo finished", started
        )

    def run_live_tick(self, command: Command) -> CommandResult:
        started = time.monotonic()
        return self._run_script(
            command,
            [
                "scripts/run_live_loop.py",
                "--demo",
                "--ticks",
                "1",
                "--symbol",
                command.text("symbol", "XAUUSD"),
            ],
            "Live tick complete",
            started,
            timeout=1800,
        )

    # -- operations --------------------------------------------------------------
    def backup_database(self, command: Command) -> CommandResult:
        from ShadBotTrader.infrastructure.deployment.backup import BackupService

        started = time.monotonic()
        if not self._database_path.exists():
            return CommandResult.rejected(
                command.kind, f"No database at {self._database_path} to back up."
            )
        try:
            record = BackupService(self._database_path).create(
                note=command.text("note", "manual backup")
            )
        except Exception as error:
            return CommandResult.failure(
                command.kind, "Backup failed", str(error), time.monotonic() - started
            )
        return CommandResult.success(
            command.kind,
            f"Backed up {record.total_rows:,} rows",
            [
                f"file    : {Path(record.path).name}",
                f"size    : {record.size_kb:.1f} KB",
                f"schema  : v{record.schema_version}",
                f"verified: {record.verified}",
            ],
            time.monotonic() - started,
        )

    def health_check(self, command: Command) -> CommandResult:
        from ShadBotTrader import __version__
        from ShadBotTrader.infrastructure.deployment.health_checks import default_monitor

        started = time.monotonic()
        report = default_monitor(
            version=__version__,
            environment="development",
            database_path=(str(self._database_path) if self._database_path.exists() else None),
            storage_root=str(self._storage_root),
        ).run()

        message = f"{report.status.value} — ready={report.is_ready}"
        if report.is_ready:
            return CommandResult.success(
                command.kind, message, report.summary_lines(), time.monotonic() - started
            )
        # An unhealthy result must still show WHICH check failed. Putting
        # the detail only in `detail` left the GUI showing an empty box —
        # exactly when the operator most needs to see something.
        return CommandResult(
            kind=command.kind,
            status=CommandStatus.FAILED,
            message=message,
            detail="Fix the failing critical dependency before running anything.",
            lines=report.summary_lines(),
            duration_seconds=time.monotonic() - started,
        )

    # -- shared ------------------------------------------------------------------
    def _run_script(
        self,
        command: Command,
        arguments: List[str],
        success_message: str,
        started: float,
        timeout: int = 900,
    ) -> CommandResult:
        """Run a project script and turn its output into a result.

        Scripts run in a subprocess so a crash inside one cannot take the
        dashboard down with it, and so a long run can be time-limited.
        """
        import subprocess
        import sys

        try:
            completed = subprocess.run(
                [sys.executable, *arguments],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path.cwd()),
            )
        except subprocess.TimeoutExpired:
            return CommandResult.failure(
                command.kind,
                f"Timed out after {timeout // 60} minutes",
                "Reduce the size of the run, or start it from a terminal.",
                time.monotonic() - started,
            )
        except Exception as error:
            return CommandResult.failure(
                command.kind,
                "Could not start the script",
                str(error),
                time.monotonic() - started,
            )

        output = completed.stdout.strip().splitlines()
        if completed.returncode != 0:
            return CommandResult.failure(
                command.kind,
                "The script reported a failure",
                (completed.stderr or "\n".join(output[-25:]))[-1500:],
                time.monotonic() - started,
            )

        interesting = [line for line in output if line.strip() and not line.startswith("=")]
        return CommandResult.success(
            command.kind, success_message, interesting[-20:], time.monotonic() - started
        )
