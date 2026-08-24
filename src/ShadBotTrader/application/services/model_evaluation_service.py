"""Score a saved model against a stored dataset (Phase 48).

Training reports how a model did on the data it was fitted to. That is
not the same question as "how does this model do on THIS dataset", and
the operator asked for the second one: pick a saved model, pick a
dataset, run it, and keep the numbers.

Two properties make the answer trustworthy rather than merely printed:

**The evaluation never trains.** Weights are loaded and frozen. A score
produced by a model that quietly kept learning on the test data is not
an evaluation, it is a second training run wearing a disguise.

**The matrix is rebuilt exactly as training built it.** Same feature set,
same model_role filter, same window size, same column order. The matrix
is built from candles live — not from a cached .npz — so it always
matches the model's expected feature count regardless of when the .npz
was last updated.

Results are appended to ``run_logs/evaluations.jsonl`` — one line per
run, never overwritten — so two models on the same dataset, or one model
across three datasets, can be compared afterwards.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

#: Default first-passage price move for signal labels when an old record
#: has no recorded threshold.
DEFAULT_THRESHOLD = 0.0008

#: The platform default label horizon, used under the same condition.
DEFAULT_HORIZON = 5

#: One line per evaluation, appended forever. A comparison is worthless
#: if yesterday's number was overwritten by today's.
EVALUATION_LOG = "evaluations.jsonl"


@dataclass
class EvaluationResult:
    """What one model scored on one dataset."""

    model_id: str
    role: str
    symbol: str
    timeframe: str
    version: int = 1
    rows: int = 0
    windows: int = 0
    window_size: int = 0
    feature_columns: int = 0
    metrics: Dict[str, float] = field(default_factory=dict)
    baseline: Optional[float] = None
    threshold: float = 0.0
    horizon: int = 0
    threshold_assumed: bool = False
    trained_on: str = ""
    evaluated_at: str = ""
    note: str = ""
    failed: bool = False
    reason: str = ""

    @property
    def headline(self) -> str:
        """The single number that matters for this kind of model."""
        if self.role == "signal":
            accuracy = self.metrics.get("accuracy")
            if accuracy is None:
                return "n/a"
            text = f"accuracy {accuracy:.2%}"
            if self.baseline is not None:
                verdict = "BETTER" if accuracy > self.baseline else "NO BETTER"
                text += f" vs baseline {self.baseline:.2%} — {verdict}"
            return text
        mae = self.metrics.get("mae")
        return "n/a" if mae is None else f"mae {mae:.6f}"

    @property
    def is_same_dataset_it_trained_on(self) -> bool:
        return bool(self.trained_on) and self.trained_on == self.timeframe

    def summary_lines(self) -> List[str]:
        if self.failed:
            return [f"FAILED: {self.reason}"]

        lines = [
            f"model    : {self.model_id} v{self.version} ({self.role})",
            f"dataset  : {self.symbol} {self.timeframe}",
            f"rows     : {self.rows:,}",
            f"windows  : {self.windows:,} of {self.window_size} x {self.feature_columns}",
            *(
                [
                    f"labels   : binary SELL/BUY, first-passage threshold "
                    f"{self.threshold:.4%}, horizon unbounded"
                ]
                if self.role == "signal"
                else []
            ),
            "",
            f"result   : {self.headline}",
        ]
        for name in sorted(self.metrics):
            lines.append(f"    {name:<12}: {self.metrics[name]:.6f}")

        if self.threshold_assumed:
            lines += [
                "",
                f"NOTE: threshold was not recorded — assumed {DEFAULT_THRESHOLD:.4%}.",
            ]

        if self.is_same_dataset_it_trained_on:
            lines += [
                "",
                "NOTE: this model was TRAINED on this timeframe. The score "
                "flatters it — a model always does better on data it has "
                "already seen. Evaluate on a different dataset for a real test.",
            ]
        return lines

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "role": self.role,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "version": self.version,
            "rows": self.rows,
            "windows": self.windows,
            "window_size": self.window_size,
            "feature_columns": self.feature_columns,
            "metrics": dict(self.metrics),
            "baseline": self.baseline,
            "threshold": self.threshold,
            "horizon": self.horizon,
            "threshold_assumed": self.threshold_assumed,
            "trained_on": self.trained_on,
            "evaluated_at": self.evaluated_at,
            "note": self.note,
            "failed": self.failed,
            "reason": self.reason,
        }


class ModelEvaluationService:
    """Loads a saved model and scores it on a stored dataset."""

    def __init__(self, storage_root: str | Path, log_dir: str | Path = "run_logs") -> None:
        self._root = Path(storage_root)
        self._log_dir = Path(log_dir)

    @property
    def log_path(self) -> Path:
        return self._log_dir / EVALUATION_LOG

    # ------------------------------------------------------------ run --
    def evaluate(
        self,
        model_id: str,
        symbol: str,
        timeframe: str,
        window_size: int = 0,
        max_windows: int = 5000,
    ) -> EvaluationResult:
        """Score ``model_id`` on the stored ``symbol``/``timeframe`` candles.

        The feature matrix is built live from candles — identical to how
        training built it — so the feature count always matches the model,
        even when the catalogue .npz is stale or was never built.
        """
        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        catalogue = ModelCatalogue(self._root)
        version = catalogue.latest_version(model_id)
        record = catalogue.read(model_id, version) if version else None

        result = EvaluationResult(
            model_id=model_id,
            role=(record.role if record else ""),
            symbol=symbol,
            timeframe=timeframe,
            version=version or 0,
            trained_on=(record.timeframe if record else ""),
            evaluated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

        if record is None:
            result.failed = True
            result.reason = (
                f"No saved model called {model_id!r}. Train one first, or pick "
                f"a different model."
            )
            return result

        # window_size: prefer the recorded value — that's what the weights expect
        window_size = window_size or record.window_size or 288
        result.window_size = window_size

        # ── role: از record بخون، اگه نبود از model_id استنتاج کن ────────
        role = record.role or ""
        if not role:
            # model_id pattern: gold_signal_5m / gold_range_1h / gold_range_1d
            mid_lower = model_id.lower()
            if "signal" in mid_lower:
                role = "signal"
            elif "range" in mid_lower:
                role = "range"
            else:
                role = "signal"   # safe default
        result.role = role

        # ── load candles ──────────────────────────────────────────────────
        try:
            candles = self._load_candles(symbol, timeframe)
        except Exception as error:
            result.failed = True
            result.reason = f"Could not load candles: {type(error).__name__}: {error}"
            return result

        if not candles:
            result.failed = True
            result.reason = (
                f"No candles stored for {symbol} {timeframe}. "
                f"Run 'Fetch market data' for that timeframe first."
            )
            return result

        # ── build feature matrix — identical to training ───────────────────
        try:
            matrix = self._build_matrix(candles, symbol, timeframe, result.role)
        except Exception as error:
            result.failed = True
            result.reason = f"Feature matrix failed: {type(error).__name__}: {error}"
            return result

        result.rows = len(matrix.rows)
        result.feature_columns = matrix.width

        # ── score frozen model ────────────────────────────────────────────
        try:
            self._score(result, matrix, candles, record, max_windows)
        except Exception as error:
            result.failed = True
            result.reason = f"{type(error).__name__}: {error}"

        return result

    # -------------------------------------------------------- internals --
    def _load_candles(self, symbol: str, timeframe: str) -> list:
        """Load candles from the Parquet store."""
        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.infrastructure.data.parquet_candle_store import ParquetCandleStore

        store = ParquetCandleStore(self._root)
        candles = store.query(Symbol(symbol), Timeframe(timeframe))
        return list(candles) if candles else []

    def _build_matrix(self, candles: list, symbol: str, timeframe: str, role: str) -> Any:
        """Build the feature matrix exactly as training does.

        Uses the same standard catalogue, the same causal-only filter,
        and the same model_role scope filter so the column count is
        identical to what the model was trained on.
        """
        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.infrastructure.ai.feature_matrix import build_feature_matrix
        from ShadBotTrader.infrastructure.feature.calculators.adaptive_filters import AdaptiveFiltersCalculator
        from ShadBotTrader.infrastructure.feature.calculators.atr import AtrCalculator
        from ShadBotTrader.infrastructure.feature.calculators.balance import BalanceCalculator
        from ShadBotTrader.infrastructure.feature.calculators.bollinger import BollingerCalculator
        from ShadBotTrader.infrastructure.feature.calculators.bollinger_bands import BollingerBandsCalculator
        from ShadBotTrader.infrastructure.feature.calculators.candle_pattern import CandlePatternCalculator
        from ShadBotTrader.infrastructure.feature.calculators.ehlers_advanced import EhlersAdvancedCalculator
        from ShadBotTrader.infrastructure.feature.calculators.ehlers_cycle import EhlersCycleCalculator
        from ShadBotTrader.infrastructure.feature.calculators.ema import EmaCalculator
        from ShadBotTrader.infrastructure.feature.calculators.fractal_stats import FractalStatsCalculator
        from ShadBotTrader.infrastructure.feature.calculators.ichimoku import IchimokuCalculator
        from ShadBotTrader.infrastructure.feature.calculators.macd import MacdCalculator
        from ShadBotTrader.infrastructure.feature.calculators.market_regime import MarketRegimeCalculator
        from ShadBotTrader.infrastructure.feature.calculators.mean_reversion import MeanReversionCalculator
        from ShadBotTrader.infrastructure.feature.calculators.momentum_advanced import MomentumAdvancedCalculator
        from ShadBotTrader.infrastructure.feature.calculators.prado_features import PradoFeaturesCalculator
        from ShadBotTrader.infrastructure.feature.calculators.price_filter import PriceFilterCalculator
        from ShadBotTrader.infrastructure.feature.calculators.returns import ReturnsCalculator
        from ShadBotTrader.infrastructure.feature.calculators.rsi import RsiCalculator
        from ShadBotTrader.infrastructure.feature.calculators.session_time import SessionTimeCalculator
        from ShadBotTrader.infrastructure.feature.calculators.sma import SmaCalculator
        from ShadBotTrader.infrastructure.feature.calculators.stochastic import StochasticCalculator
        from ShadBotTrader.infrastructure.feature.calculators.structure_features import StructureFeaturesCalculator
        from ShadBotTrader.infrastructure.feature.calculators.target import TargetCalculator
        from ShadBotTrader.infrastructure.feature.calculators.trend_strength import TrendStrengthCalculator
        from ShadBotTrader.infrastructure.feature.calculators.volatility_breakout import VolatilityBreakoutCalculator
        from ShadBotTrader.infrastructure.feature.calculators.volume_analysis import VolumeAnalysisCalculator
        from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set_v1

        # registry بدون pywt (noise_filter که non-causal هست)
        class _SafeRegistry:
            def __init__(self):
                self._m = {
                    "adaptive_filters": AdaptiveFiltersCalculator(),
                    "atr": AtrCalculator(), "balance": BalanceCalculator(),
                    "bollinger": BollingerCalculator(), "bband": BollingerBandsCalculator(),
                    "candle_pattern": CandlePatternCalculator(),
                    "ehlers_advanced": EhlersAdvancedCalculator(),
                    "ehlers_cycle": EhlersCycleCalculator(),
                    "ema": EmaCalculator(), "fractal_stats": FractalStatsCalculator(),
                    "ichimoku": IchimokuCalculator(), "macd": MacdCalculator(),
                    "market_regime": MarketRegimeCalculator(),
                    "mean_reversion": MeanReversionCalculator(),
                    "momentum_advanced": MomentumAdvancedCalculator(),
                    "prado_features": PradoFeaturesCalculator(),
                    "price_filter": PriceFilterCalculator(),
                    "returns": ReturnsCalculator(), "rsi": RsiCalculator(),
                    "session_time": SessionTimeCalculator(), "sma": SmaCalculator(),
                    "stochastic": StochasticCalculator(),
                    "structure_features": StructureFeaturesCalculator(),
                    "target": TargetCalculator(),
                    "trend_strength": TrendStrengthCalculator(),
                    "volatility_breakout": VolatilityBreakoutCalculator(),
                    "volume_analysis": VolumeAnalysisCalculator(),
                }
            def resolve(self, f):
                return self._m.get(f)

        # اول سعی کن از CalculatorRegistry کامل استفاده کن
        try:
            from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
            resolver = CalculatorRegistry()
        except ImportError:
            resolver = _SafeRegistry()

        feature_set = standard_feature_set_v1()
        return build_feature_matrix(
            candles=candles,
            symbol=Symbol(symbol),
            timeframe=Timeframe(timeframe),
            feature_set=feature_set,
            resolver=resolver,
            include_features=True,
            causal_only=True,
            model_role=role,   # ← فیلتر model_scope مثل training
        )

    def _score(
        self,
        result: EvaluationResult,
        matrix: Any,
        candles: list,
        record: Any,
        max_windows: int,
    ) -> None:
        """Run the frozen model over the dataset and collect metrics."""
        import numpy as np

        from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
        from ShadBotTrader.infrastructure.ai.data_windowing import minmax_scale_window
        from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import FilesystemArtifactStore
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import _deserialize_model

        artifact = FilesystemArtifactStore(self._root).load(
            ModelId(result.model_id), ModelVersion(result.version)
        )
        if artifact is None:
            raise FileNotFoundError(
                f"{result.model_id} v{result.version} is listed but its weights "
                f"are missing from datasets/models/"
            )

        model = _deserialize_model(artifact.payload)

        # ── بررسی تطابق feature count ────────────────────────────────────
        expected_shape = getattr(model, "input_shape", None)
        if expected_shape is not None and len(expected_shape) == 3:
            exp_features = expected_shape[2]
            if exp_features is not None and matrix.width != exp_features:
                raise ValueError(
                    f"Feature mismatch: matrix has {matrix.width} columns "
                    f"but model expects {exp_features}.\n"
                    f"  model role detected: {result.role!r}\n"
                    f"  record.feature_columns: {getattr(record, 'feature_columns', '?')}\n"
                    f"  matrix.width: {matrix.width}\n"
                    f"  This means the model was trained with a different feature set "
                    f"or model_role filter than what evaluate produced. "
                    f"Re-train the model with the current code to fix this."
                )

        # ── threshold از record ───────────────────────────────────────────
        recorded_threshold = float(getattr(record, "threshold", 0.0) or 0.0)
        threshold = recorded_threshold if recorded_threshold > 0 else DEFAULT_THRESHOLD
        recorded_horizon = int(getattr(record, "horizon", 0) or 0)
        result.threshold_assumed = result.role == "signal" and recorded_threshold <= 0
        result.threshold = threshold

        # ── بازه زمانی eval ───────────────────────────────────────────────
        rows = matrix.rows
        horizon = recorded_horizon if recorded_horizon > 0 else (0 if result.role == "signal" else DEFAULT_HORIZON)
        result.horizon = horizon

        usable = len(rows) - result.window_size - max(horizon, 1) + 1
        if usable < 1:
            raise ValueError(
                f"{len(rows):,} rows — not enough for a single {result.window_size}-row "
                f"window with horizon {horizon}. Load more candles."
            )

        step = max(1, usable // max_windows) if max_windows else 1
        starts = list(range(0, usable, step))[:max_windows] if max_windows else list(range(usable))
        result.windows = len(starts)
        if step > 1:
            result.note = f"sampled every {step} windows of {usable:,}"

        # ── inference ─────────────────────────────────────────────────────
        windows = np.array(
            [minmax_scale_window(rows[s: s + result.window_size]) for s in starts],
            dtype=np.float32,
        )
        predictions = model.predict(windows, verbose=0)

        if result.role == "signal":
            self._score_signal(result, predictions, starts, matrix, candles, threshold)
        else:
            self._score_range(result, predictions, starts, matrix, horizon)

    def _score_signal(
        self,
        result: EvaluationResult,
        predictions: Any,
        starts: Any,
        matrix: Any,
        candles: list,
        threshold: float,
    ) -> None:
        """Accuracy: prediction == first-passage label از OHLC واقعی.

        دقیقاً مثل training:
          - از candle های OHLC واقعی label میسازه (نه فقط close)
          - اگه high کندل به +threshold رسید قبل از low → BUY
          - اگه low کندل به -threshold رسید قبل از high → SELL
          - window آخرین کندل matrix → با source_index به candle اصلی map میشه
        """
        import numpy as np

        from ShadBotTrader.infrastructure.ai.target_builder import (
            build_signal_labels_from_candles,
        )

        # ── label از OHLC candle های واقعی ─────────────────────────────
        # source_index: هر ردیف matrix به کدام candle اصل بازمیگرده
        source_index = matrix.source_index   # list[int]

        # label را روی کل سری candle بساز (همانطور که training میساخت)
        labels_obj = build_signal_labels_from_candles(candles, threshold=threshold)
        # دیکشنری: candle_index → label (0=sell, 1=buy)
        label_by_candle = dict(
            zip(labels_obj.source_index, labels_obj.labels, strict=True)
        )

        # ── مقایسه prediction با label ──────────────────────────────────
        predicted_all = np.argmax(np.asarray(predictions), axis=1).tolist()
        truth: List[int] = []
        predicted: List[int] = []

        for start, pred_val in zip(starts, predicted_all, strict=False):
            # آخرین ردیف این window در matrix
            matrix_row = start + result.window_size - 1
            if matrix_row >= len(source_index):
                continue
            # کندل اصلی متناظر
            candle_idx = source_index[matrix_row]
            if candle_idx not in label_by_candle:
                continue   # این کندل label ندارد (threshold نرسیده)
            truth.append(label_by_candle[candle_idx])
            predicted.append(int(pred_val))

        if not truth:
            raise ValueError(
                f"No signal windows have a first-passage label at threshold "
                f"{threshold:.4%}. The model may need more data or a smaller threshold."
            )

        result.windows = len(truth)
        correct = sum(1 for a, p in zip(truth, predicted, strict=True) if a == p)
        total = len(truth)
        result.metrics["accuracy"] = correct / total
        counts = {label: truth.count(label) for label in (0, 1)}
        result.baseline = max(counts.values()) / total
        result.metrics["sell_share"] = counts[0] / total
        result.metrics["buy_share"]  = counts[1] / total

    def _score_range(
        self,
        result: EvaluationResult,
        predictions: Any,
        starts: Any,
        matrix: Any,
        horizon: int,
    ) -> None:
        """Score high/low offsets against the real future price path."""
        import numpy as np

        columns = matrix.column_names
        needed = ("return_1", "high_rel", "low_rel")
        if not all(name in columns for name in needed):
            raise ValueError(
                "the matrix has no return_1/high_rel/low_rel columns to score against. "
                "Make sure the range model dataset includes these candle columns."
            )

        return_index = columns.index("return_1")
        high_index = columns.index("high_rel")
        low_index = columns.index("low_rel")

        closes = [1.0]
        for row in matrix.rows[1:]:
            closes.append(closes[-1] * (1.0 + float(row[return_index])))

        truth = []
        for start in starts:
            here = start + result.window_size - 1
            if here >= len(closes):
                truth.append([0.0, 0.0])
                continue
            reference = closes[here]
            if reference <= 0:
                truth.append([0.0, 0.0])
                continue
            future_idx = range(here + 1, min(here + 1 + horizon, len(matrix.rows)))
            future_highs = [
                closes[i] * (1.0 + float(matrix.rows[i][high_index])) for i in future_idx
            ]
            future_lows = [
                closes[i] * (1.0 + float(matrix.rows[i][low_index])) for i in future_idx
            ]
            truth.append([
                max(future_highs) / reference - 1.0 if future_highs else 0.0,
                min(future_lows) / reference - 1.0 if future_lows else 0.0,
            ])

        expected = np.asarray(truth, dtype=np.float64)
        actual = np.asarray(predictions, dtype=np.float64)[:, : expected.shape[1]]
        count = min(len(actual), len(expected))
        if count < 1:
            raise ValueError("No complete range targets were available for the test")
        actual = actual[:count]
        expected = expected[:count]
        error = actual - expected

        result.metrics["mae"] = float(np.mean(np.abs(error)))
        result.metrics["mse"] = float(np.mean(error**2))
        result.metrics["rmse"] = float(np.sqrt(np.mean(error**2)))
        result.metrics["high_mae"] = float(np.mean(np.abs(error[:, 0])))
        result.metrics["low_mae"] = float(np.mean(np.abs(error[:, 1])))
        result.metrics["high_rmse"] = float(np.sqrt(np.mean(error[:, 0] ** 2)))
        result.metrics["low_rmse"] = float(np.sqrt(np.mean(error[:, 1] ** 2)))
        result.metrics["high_bias"] = float(np.mean(error[:, 0]))
        result.metrics["low_bias"] = float(np.mean(error[:, 1]))

    # ------------------------------------------------------------- log --
    def append_to_log(self, result: EvaluationResult) -> Path:
        """Append one evaluation, keeping every earlier one."""
        path = self.log_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
        return path

    def history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Past evaluations, newest last."""
        path = self.log_path
        if not path.exists():
            return []
        entries: List[Dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries[-limit:]
