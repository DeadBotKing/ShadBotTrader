"""Application service for the signal-first, TP/SL model backtest.

This is the composition root for the requested workflow:

    5M window -> signal probabilities -> confidence gate
              -> 1H window -> predicted high/low -> fixed bracket
              -> candle-by-candle TP/SL exit -> PnL

The service keeps model loading and model metadata out of the simulation
engine.  A caller may either provide already-loaded artifacts/predictors
(which is convenient for tests and experiments) or use ``from_storage``
to load the saved models and their training records from ``datasets``.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, List, Optional, Sequence

from ShadBotTrader.application.persistence_context import PersistenceContext
from ShadBotTrader.application.services.backtest_service import BacktestService
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.simulation.session import SimulationConfiguration
from ShadBotTrader.domain.simulation.simulation_types import EntryTiming, SameBarPolicy
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy
from ShadBotTrader.infrastructure.ai.dual_predictor import RangePredictor, SignalPredictor
from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import FilesystemArtifactStore
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue, ModelRecord
from ShadBotTrader.infrastructure.simulation.dual_model_prediction_source import (
    DualModelPredictionSource,
)
from ShadBotTrader.infrastructure.trading.dual_model_strategy import DualModelStrategy


def _pad_or_trim_matrix(matrix: Any, expected: int) -> Any:
    """تعداد feature ستون‌ها رو با expected تطبیق بده.

    اگه matrix.width < expected: ستون‌های صفر اضافه می‌کنیم (padding)
    اگه matrix.width > expected: ستون‌های اضافه رو قطع می‌کنیم (trim)
    اگه برابر: همون رو برمیگردونیم

    این برای جلوگیری از feature mismatch بین training و backtest لازمه.
    برخی calculators در backtest context resolve نمیشن و باعث کمبود
    feature میشن. padding با صفر مشکل shape mismatch رو حل می‌کنه.
    """
    from ShadBotTrader.infrastructure.ai.feature_matrix import FeatureMatrix

    actual = matrix.width
    if actual == expected:
        return matrix

    rows = matrix.rows
    if not rows:
        return matrix

    if actual < expected:
        # padding: ستون‌های صفر به آخر اضافه کن
        pad = expected - actual
        new_rows = [list(row) + [0.0] * pad for row in rows]
        # column_names هم pad کن
        pad_names = [f"_pad_{i}" for i in range(pad)]
        new_col_names = list(matrix.column_names) + pad_names
    else:
        # trim: ستون‌های اضافه رو قطع کن
        new_rows = [list(row)[:expected] for row in rows]
        new_col_names = list(matrix.column_names)[:expected]

    return FeatureMatrix(
        rows=new_rows,
        column_names=new_col_names,
        source_index=list(matrix.source_index),
        dropped_warmup=matrix.dropped_warmup,
        skipped_features=list(matrix.skipped_features),
    )


class DualModelBacktestService:
    """Run the two-model strategy over 5M and 1H candle series."""

    def __init__(
        self,
        symbol: Symbol,
        signal_artifact: Any,
        signal_predictor: Any,
        range_artifact: Any,
        range_predictor: Any,
        signal_window_size: int = 100,
        range_window_size: int = 500,
        min_signal_confidence: float = 0.60,
        feature_set: Any = None,
        resolver: Any = None,
        signal_feature_source: Any = None,
        range_feature_source: Any = None,
        configuration: Optional[SimulationConfiguration] = None,
        risk_policy: Optional[RiskPolicy] = None,
        base_quantity: Decimal = Decimal("0.01"),
        persistence: Optional[PersistenceContext] = None,
        min_reward_risk: Optional[float] = None,
        min_move_fraction: float = 0.0,
        expected_signal_features: Optional[int] = None,
        expected_range_features: Optional[int] = None,
        reward_risk_multiplier: Optional[float] = None,
        filter_zero_bar: bool = False,
        allowed_hours_utc: Optional[Sequence[int]] = None,
        min_sl_distance: float = 0.0,
        range_target_units: str = "pct",
        trend_filter: str = "none",
        strategy: str = "classic",
        slope_mode: str = "both",
        daily_artifact: Any = None,
        daily_predictor: Any = None,
        daily_window_size: int = 150,
        expected_daily_features: Optional[int] = None,
        max_entry_distance_atr: float = 0.0,
    ) -> None:
        if signal_window_size < 2 or range_window_size < 2:
            raise ValidationError("Both model windows must be >= 2")
        if range_target_units not in ("pct", "atr"):
            raise ValidationError(
                f"Unknown range target units: {range_target_units!r} (use 'pct' or 'atr')"
            )
        if trend_filter not in ("none", "ema50"):
            raise ValidationError(f"Unknown trend filter: {trend_filter!r} (use 'none' or 'ema50')")
        if strategy not in ("classic", "triple"):
            raise ValidationError(f"Unknown strategy: {strategy!r} (use 'classic' or 'triple')")
        if slope_mode not in ("both", "either", "high", "low"):
            raise ValidationError(
                f"Unknown slope mode: {slope_mode!r} (use 'both', 'either', 'high' or 'low')"
            )
        if strategy == "triple" and daily_predictor is None:
            raise ValidationError("Triple strategy needs the daily (1D) range model")
        if max_entry_distance_atr < 0:
            raise ValidationError("max_entry_distance_atr must not be negative")
        if not 0.0 <= min_signal_confidence <= 1.0:
            raise ValidationError("min_signal_confidence must be in [0, 1]")
        if reward_risk_multiplier is not None and reward_risk_multiplier <= 0:
            raise ValidationError("reward_risk_multiplier must be positive")
        if min_sl_distance < 0:
            raise ValidationError("min_sl_distance must not be negative")

        self._symbol = symbol
        self._signal_artifact = signal_artifact
        self._signal_predictor = signal_predictor
        self._range_artifact = range_artifact
        self._range_predictor = range_predictor
        self._signal_window_size = signal_window_size
        self._range_window_size = range_window_size
        self._min_signal_confidence = min_signal_confidence
        self._feature_set = feature_set
        self._resolver = resolver
        self._signal_feature_source = signal_feature_source
        self._range_feature_source = range_feature_source
        self._risk_policy = risk_policy
        self._base_quantity = base_quantity
        self._persistence = persistence
        self._min_reward_risk = min_reward_risk
        self._min_move_fraction = min_move_fraction
        self._expected_signal_features = expected_signal_features
        self._expected_range_features = expected_range_features
        self._configuration = configuration or SimulationConfiguration(
            entry_timing=EntryTiming.NEXT_OPEN,
            same_bar_policy=SameBarPolicy.STOP_FIRST,
        )
        self._reward_risk_multiplier = reward_risk_multiplier
        self._filter_zero_bar = filter_zero_bar
        # فاز ۵۲: فیلترهای session و SL
        self._allowed_hours_utc = allowed_hours_utc
        self._min_sl_distance = float(min_sl_distance)
        # فاز ۹۵: واحد تارگت مدل رنج ("atr" = ضرایب ATR)
        self._range_target_units = range_target_units
        # فاز ۹۶-ب: فیلتر ترند روزانه ("ema50" یا "none")
        self._trend_filter = trend_filter
        # فاز ۹۷: استراتژی سه‌تایم‌فریمی
        self._strategy = strategy
        self._slope_mode = slope_mode
        self._daily_artifact = daily_artifact
        self._daily_predictor = daily_predictor
        self._daily_window_size = daily_window_size
        self._expected_daily_features = expected_daily_features
        self._max_entry_distance_atr = float(max_entry_distance_atr)

    @classmethod
    def from_storage(
        cls,
        storage_root: str | Path,
        symbol: str = "XAUUSD",
        signal_model_id: str = "gold_signal_5m",
        range_model_id: str = "gold_range_1h",
        signal_version: Optional[int] = None,
        range_version: Optional[int] = None,
        min_signal_confidence: float = 0.60,
        signal_window_size: Optional[int] = None,
        range_window_size: Optional[int] = None,
        configuration: Optional[SimulationConfiguration] = None,
        risk_policy: Optional[RiskPolicy] = None,
        base_quantity: Decimal = Decimal("0.01"),
        persistence: Optional[PersistenceContext] = None,
        feature_set: Any = None,
        resolver: Any = None,
        reward_risk_multiplier: Optional[float] = None,
        filter_zero_bar: bool = False,
        allowed_hours_utc: Optional[Sequence[int]] = None,
        min_sl_distance: float = 0.0,
        trend_filter: str = "none",
        strategy: str = "classic",
        slope_mode: str = "both",
        daily_model_id: str = "gold_range_1d",
        daily_version: Optional[int] = None,
        max_entry_distance_atr: float = 0.0,
    ) -> "DualModelBacktestService":
        """Load both artifacts and their ``training.json`` metadata.

        Window sizes and horizons come from the model records, not from a
        hard-coded guess.  This matters in the checked-in project: the
        signal model was trained on 100 rows while the range model was
        trained on 500 rows.

        فاز ۹۷: ``strategy="triple"`` — مدل رنج 1D (``daily_model_id``)
        برای ترند روز (مجوز ۲) و براکت TP/SL از مدل رنج اصلی (4H) با
        fallback های D0/5M ساخته می‌شود.
        """
        if strategy not in ("classic", "triple"):
            raise ValidationError(f"Unknown strategy: {strategy!r} (use 'classic' or 'triple')")
        root = Path(storage_root)
        catalogue = ModelCatalogue(root)
        signal_record = _require_record(catalogue, signal_model_id, signal_version)
        range_record = _require_record(catalogue, range_model_id, range_version)

        if signal_record.role != "signal":
            raise ValidationError(
                f"{signal_model_id} is recorded as {signal_record.role}, not signal"
            )
        if range_record.role != "range":
            raise ValidationError(f"{range_model_id} is recorded as {range_record.role}, not range")
        if signal_record.symbol and signal_record.symbol != symbol:
            raise ValidationError(
                f"Signal model belongs to {signal_record.symbol}, not requested symbol {symbol}"
            )
        if range_record.symbol and range_record.symbol != symbol:
            raise ValidationError(
                f"Range model belongs to {range_record.symbol}, not requested symbol {symbol}"
            )

        artifact_store = FilesystemArtifactStore(root)
        signal_artifact = artifact_store.load(
            ModelId(signal_model_id), ModelVersion(signal_record.version)
        )
        range_artifact = artifact_store.load(
            ModelId(range_model_id), ModelVersion(range_record.version)
        )
        if signal_artifact is None:
            raise ValidationError(
                f"Missing artifact for {signal_model_id} v{signal_record.version}"
            )
        if range_artifact is None:
            raise ValidationError(f"Missing artifact for {range_model_id} v{range_record.version}")

        signal_timeframe = signal_record.timeframe or "5M"
        range_timeframe = range_record.timeframe or "1H"
        signal_horizon = signal_record.horizon or 5
        range_horizon = range_record.horizon or 5

        # A model trained with the full 123-column matrix must receive the
        # same catalogue at inference.  Callers can inject another source
        # explicitly; the lazy imports keep the core test path TensorFlow/
        # PyWavelets-free.
        if (
            feature_set is None
            and max(signal_record.feature_columns, range_record.feature_columns) > 14
        ):
            from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
            from ShadBotTrader.infrastructure.feature.standard_catalog import (
                standard_feature_set_v1,
            )

            feature_set = standard_feature_set_v1()
            resolver = resolver or CalculatorRegistry()

        daily_artifact = None
        daily_predictor = None
        daily_window_size = 150
        expected_daily_features = None
        if strategy == "triple":
            daily_catalogue_version = daily_version or catalogue.latest_version(daily_model_id)
            daily_record = (
                catalogue.read(daily_model_id, daily_catalogue_version)
                if daily_catalogue_version
                else None
            )
            if daily_record is None:
                raise ValidationError(
                    f"Triple strategy needs a saved {daily_model_id!r} model "
                    "(the 1D range model for the daily trend license)"
                )
            if daily_record.role != "range":
                raise ValidationError(f"{daily_model_id} is recorded as {daily_record.role}")
            daily_artifact = artifact_store.load(
                ModelId(daily_model_id), ModelVersion(daily_catalogue_version)
            )
            if daily_artifact is None:
                raise ValidationError(
                    f"Missing artifact for {daily_model_id} v{daily_catalogue_version}"
                )
            daily_predictor = RangePredictor(
                horizon=daily_record.horizon or 1,
                timeframe=daily_record.timeframe or "1D",
                target_units=getattr(daily_record, "target_units", "pct") or "pct",
            )
            daily_window_size = daily_record.window_size or 150
            expected_daily_features = daily_record.feature_columns or None

        return cls(
            symbol=Symbol(symbol),
            signal_artifact=signal_artifact,
            signal_predictor=SignalPredictor(
                horizon=signal_horizon,
                timeframe=signal_timeframe,
            ),
            range_artifact=range_artifact,
            range_predictor=RangePredictor(
                horizon=range_horizon,
                timeframe=range_timeframe,
                target_units=getattr(range_record, "target_units", "pct") or "pct",
            ),
            signal_window_size=signal_window_size or signal_record.window_size or 100,
            range_window_size=range_window_size or range_record.window_size or 500,
            min_signal_confidence=min_signal_confidence,
            feature_set=feature_set,
            resolver=resolver,
            configuration=configuration,
            risk_policy=risk_policy,
            base_quantity=base_quantity,
            persistence=persistence,
            expected_signal_features=signal_record.feature_columns or None,
            expected_range_features=range_record.feature_columns or None,
            reward_risk_multiplier=reward_risk_multiplier,
            filter_zero_bar=filter_zero_bar,
            allowed_hours_utc=allowed_hours_utc,
            min_sl_distance=min_sl_distance,
            range_target_units=getattr(range_record, "target_units", "pct") or "pct",
            trend_filter=trend_filter,
            strategy=strategy,
            slope_mode=slope_mode,
            daily_artifact=daily_artifact,
            daily_predictor=daily_predictor,
            daily_window_size=daily_window_size,
            expected_daily_features=expected_daily_features,
            max_entry_distance_atr=max_entry_distance_atr,
        )

    @property
    def signal_window_size(self) -> int:
        return self._signal_window_size

    @property
    def range_window_size(self) -> int:
        return self._range_window_size

    @property
    def min_signal_confidence(self) -> float:
        return self._min_signal_confidence

    def run(
        self,
        session_id: str,
        signal_candles: Sequence[Candle],
        range_candles: Sequence[Candle],
        reporter: Any = None,
        record_replay: bool = False,
        test_ratio: float = 0.0,
        daily_candles: Sequence[Candle] = (),
    ) -> Any:
        """Execute the signal-first, fixed-bracket backtest.

        فاز ۹۷: ``daily_candles`` (1D) در حالت triple الزامی است.
        """
        if not signal_candles:
            raise ValueError("A dual-model backtest needs signal candles")
        if not range_candles:
            raise ValueError("A dual-model backtest needs range candles")
        if self._strategy == "triple" and not daily_candles:
            raise ValueError(
                "Triple strategy needs stored 1D candles (daily trend license) — "
                "fetch XAUUSD 1D first"
            )
        if not 0.0 <= test_ratio < 1.0:
            raise ValidationError("test_ratio must be in [0, 1)")

        from ShadBotTrader.infrastructure.ai.feature_matrix import build_feature_matrix

        ordered_signal = sorted(signal_candles, key=lambda candle: candle.open_time.value)
        ordered_range = sorted(range_candles, key=lambda candle: candle.open_time.value)
        include_features = self._feature_set is not None and self._resolver is not None
        signal_matrix = build_feature_matrix(
            candles=ordered_signal,
            symbol=self._symbol,
            timeframe=Timeframe(str(ordered_signal[0].timeframe)),
            feature_set=self._feature_set,
            resolver=self._resolver,
            include_features=include_features,
            source=self._signal_feature_source,
            causal_only=True,
            model_role="signal",
        )
        range_matrix = build_feature_matrix(
            candles=ordered_range,
            symbol=self._symbol,
            timeframe=Timeframe(str(ordered_range[0].timeframe)),
            feature_set=self._feature_set,
            resolver=self._resolver,
            include_features=include_features,
            source=self._range_feature_source,
            causal_only=True,
            model_role="range",
        )
        # فاز ۹۷: ماتریس روزانه برای مجوز ترند
        daily_matrix = None
        ordered_daily: List[Candle] = []
        if self._strategy == "triple":
            ordered_daily = sorted(daily_candles, key=lambda candle: candle.open_time.value)
            daily_matrix = build_feature_matrix(
                candles=ordered_daily,
                symbol=self._symbol,
                timeframe=Timeframe(str(ordered_daily[0].timeframe)),
                feature_set=self._feature_set,
                resolver=self._resolver,
                include_features=include_features,
                source=self._range_feature_source,
                causal_only=True,
                model_role="range",
            )
            if self._expected_daily_features is not None:
                daily_matrix = _pad_or_trim_matrix(daily_matrix, self._expected_daily_features)
        # Feature count validation + zero-padding
        # Training و backtest ممکنه تعداد feature کمی متفاوت داشته باشن
        # (برخی calculators در backtest context resolve نمیشن)
        # راه‌حل: اگه backtest کمتر feature داره → با صفر pad کن
        # اگه بیشتر داره → فقط expected تاش برش میدیم
        if self._expected_signal_features is not None:
            signal_matrix = _pad_or_trim_matrix(signal_matrix, self._expected_signal_features)
        if self._expected_range_features is not None:
            range_matrix = _pad_or_trim_matrix(range_matrix, self._expected_range_features)

        source = DualModelPredictionSource(
            signal_artifact=self._signal_artifact,
            signal_predictor=self._signal_predictor,
            range_artifact=self._range_artifact,
            range_predictor=self._range_predictor,
            symbol=self._symbol,
            signal_timeframe=Timeframe(str(signal_candles[0].timeframe)),
            range_timeframe=Timeframe(str(range_candles[0].timeframe)),
            range_candles=ordered_range,
            signal_window_size=self._signal_window_size,
            range_window_size=self._range_window_size,
            min_signal_confidence=self._min_signal_confidence,
            feature_set=self._feature_set,
            resolver=self._resolver,
            signal_feature_source=self._signal_feature_source,
            range_feature_source=self._range_feature_source,
            signal_matrix=signal_matrix,
            range_matrix=range_matrix,
            signal_candles=ordered_signal,
            reward_risk_multiplier=self._reward_risk_multiplier,
            # فاز ۵۷: spread برای گسترش SL
            spread=self._configuration.spread if self._configuration.spread > 0 else None,
            spread_pct=getattr(self._configuration, "spread_pct", None),
            # فاز ۹۵: واحد تارگت مدل رنج — مدل ATR به ATR مرجع نیاز داره
            range_target_units=self._range_target_units,
            # فاز ۹۶-ب: فیلتر ترند روزانه
            trend_filter=self._trend_filter,
            # فاز ۹۷: استراتژی سه‌تایم‌فریمی
            daily_artifact=self._daily_artifact,
            daily_predictor=self._daily_predictor,
            daily_timeframe=Timeframe("1D"),
            daily_candles=ordered_daily,
            daily_matrix=daily_matrix,
            daily_window_size=self._daily_window_size,
            slope_mode=self._slope_mode,
            max_entry_distance_atr=self._max_entry_distance_atr,
        )

        _active_config = self._configuration
        if test_ratio > 0:
            test_start = int(len(ordered_signal) * (1.0 - test_ratio))
            _active_config = SimulationConfiguration(
                initial_capital=self._configuration.initial_capital,
                base_currency=self._configuration.base_currency,
                spread=self._configuration.spread,
                slippage_rate=self._configuration.slippage_rate,
                commission_rate=self._configuration.commission_rate,
                seed=self._configuration.seed,
                mode=self._configuration.mode,
                warmup_bars=max(self._configuration.warmup_bars, test_start),
                entry_timing=self._configuration.entry_timing,
                same_bar_policy=self._configuration.same_bar_policy,
                metadata={
                    **self._configuration.metadata,
                    "test_ratio": test_ratio,
                    "test_start_index": test_start,
                },
            )

        strategy = DualModelStrategy(
            min_confidence=self._min_signal_confidence,
            min_reward_risk=self._min_reward_risk,
            min_move_fraction=self._min_move_fraction,
            require_range_model=True,
            allowed_hours_utc=self._allowed_hours_utc,
            min_sl_distance=self._min_sl_distance,
        )
        service = BacktestService(
            configuration=_active_config,
            risk_policy=self._risk_policy,
            base_quantity=self._base_quantity,
            allow_reversal=False,
            persistence=self._persistence,
            strategy=strategy,
            bracket_provider=source,
            model_id="dual_model",
            filter_zero_bar=self._filter_zero_bar,
        )
        return service.run(
            session_id=session_id,
            symbol=self._symbol,
            timeframe=Timeframe(str(signal_candles[0].timeframe)),
            candles=ordered_signal,
            prediction_source=source,
            reporter=reporter,
            record_replay=record_replay,
        )


def _require_record(
    catalogue: ModelCatalogue,
    model_id: str,
    version: Optional[int],
) -> ModelRecord:
    selected = version or catalogue.latest_version(model_id)
    if selected < 1:
        raise ValidationError(f"No training record found for {model_id}")
    record = catalogue.read(model_id, selected)
    if record is None:
        raise ValidationError(f"Training record for {model_id} v{selected} is unreadable")
    return record
