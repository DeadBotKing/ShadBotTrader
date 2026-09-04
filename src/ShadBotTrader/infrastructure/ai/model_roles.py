"""The two model roles of Phase 29, with their defaults.

A role binds together everything that makes one of the two models what
it is: the question it answers, the timeframe it reads, how far ahead it
looks, and the shape of its output head. Keeping that in one object
prevents the combination drifting apart across the trainer, the CLI and
the dashboard.

Defaults follow the user requirement: **1H for the range model, 5M for
the signal model**. Hourly bars carry enough structure for a multi-bar
range to mean something, while 5-minute extremes are mostly
microstructure noise; the signal model in turn needs the resolution to
act.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ShadBotTrader.domain.ai.prediction_target import PredictionTarget, TargetKind
from ShadBotTrader.domain.common.errors import ValidationError

#: Loss + activation per task. Regression must NOT use a bounded
#: activation: a sigmoid output can never express a -3% low offset.
#:
#: Range model uses Huber loss (فاز ۵۳):
#:   loss = Huber(delta=0.005)
#:
#:   target magnitude : ±0.002 (±0.2% offset, ~±5$ روی XAUUSD=2650)
#:   val_mae achieved : 0.001754 (±4.65$)
#:
#:   delta=0.005 → δ/val_mae=2.85 → MSE mode برای اکثر predictions ✅
#:   delta=0.001 (قبلی) → δ/val_mae=0.57 → MAE mode → gradient کند ❌
#:
#: Why Huber beats plain MAE or MSE for high/low offsets:
#:   MSE  → predictions shrink toward mean (large low_bias)
#:   MAE  → no smooth gradient near zero (slow convergence)
#:   MAPE → undefined when true ≈ 0 (5% of targets near-zero)
#:   Huber(delta=0.005) → smooth MSE zone covers most of val_mae range  ✅
_TASK_HEADS: Dict[TargetKind, Dict[str, str]] = {
    TargetKind.PRICE_RANGE: {
        "activation": "linear",
        "loss": "huber",  # Huber(delta=0.005): MSE zone covers ±0.005 → smooth convergence
        "metric": "mae",  # MAE رو به عنوان متریک نگه میداریم — قابل تفسیر
    },
    TargetKind.TRADE_SIGNAL: {
        "activation": "softmax",
        "loss": "sparse_categorical_crossentropy",
        "metric": "accuracy",
    },
}


@dataclass(frozen=True)
class ModelRole:
    """One of the two models, fully specified.

    Architecture hyperparameters (n_filters, depth_multiplier, …) are
    carried here so the dashboard, CLI and trainer always agree on the
    same defaults — no magic numbers scattered across layers.

    Signal defaults  (5M / window=100):
      n_layers_per_block=3 — RF = 1+(5-1)*(1+2+4)*2 = 57 < 100 ✅
      depth_multiplier=8   — fewer params in the wide input layer
      dropout=0.15         — stronger regularisation for 118+ features
      l2=2.5e-4
      n_filters=32

    Range defaults  (1D / window=100):
      n_layers_per_block=3 — RF=57 < 100 ✅
      depth_multiplier=6   — regression needs capacity
      dropout=0.10
      l2=2.0e-4
      n_filters=48
    """

    name: str
    target: PredictionTarget
    model_id: str
    description: str
    window_size: int = 32
    # ── WaveNet architecture knobs ─────────────────────────────────────
    n_filters: int = 32
    kernel_size: int = 5
    n_layers_per_block: int = 3  # RF=57 — window=100 compatible
    n_blocks: int = 2
    depth_multiplier: int = 8
    l2: float = 2.5e-4
    dropout: float = 0.10
    seq2seq: bool = False  # Phase 55: seq2seq output for range model
    #: فاز ۹۹: افق برچسب trend_signal (تعداد کندل جلوتر برای مانع‌ها)
    label_horizon: int = 288

    def __post_init__(self) -> None:
        if self.window_size < 2:
            raise ValidationError("window_size must be >= 2")

    @property
    def output_units(self) -> int:
        return self.target.output_units

    @property
    def output_activation(self) -> str:
        return _TASK_HEADS[self.target.kind]["activation"]

    @property
    def loss(self) -> str:
        return _TASK_HEADS[self.target.kind]["loss"]

    @property
    def metric(self) -> str:
        return _TASK_HEADS[self.target.kind]["metric"]

    @property
    def timeframe(self) -> str:
        return self.target.timeframe

    @property
    def horizon(self) -> int:
        return self.target.horizon

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "model_id": self.model_id,
            "timeframe": self.timeframe,
            "horizon": self.horizon,
            "window_size": self.window_size,
            "output_units": self.output_units,
            "activation": self.output_activation,
            "loss": self.loss,
            "target": self.target.to_dict(),
            # architecture
            "n_filters": self.n_filters,
            "kernel_size": self.kernel_size,
            "n_layers_per_block": self.n_layers_per_block,
            "n_blocks": self.n_blocks,
            "depth_multiplier": self.depth_multiplier,
            "l2": self.l2,
            "dropout": self.dropout,
        }


#: Timeframes that have their own trained models (Phase 39).
#: 1D was added alongside 1H so the platform can forecast a daily range,
#: which is a different question from an hourly one and deserves its own
#: weights rather than a rescaled reuse of the hourly model.
MODEL_TIMEFRAMES: tuple[str, ...] = ("5M", "1H", "1D")


def range_model_id(timeframe: str) -> str:
    """The model id for the range model of one timeframe.

    Each timeframe gets its OWN id. Sharing ``gold_range`` between 1H and
    1D would make the second training run overwrite the first, and the
    artifact store would hand back whichever was written last with no way
    to tell them apart.
    """
    return f"gold_range_{timeframe.strip().lower()}"


def trend_model_id(timeframe: str) -> str:
    """The model id for the trend (candle-color) model of one timeframe.

    Like range: per-timeframe ids keep trained artifacts from colliding
    (``gold_trend_4h`` vs ``gold_trend_1d``).
    """
    return f"gold_trend_{timeframe.strip().lower()}"


def trend_model_role(
    timeframe: str = "1D",
    horizon: int = 1,
    window_size: int = 150,
    n_layers_per_block: int | None = None,
    n_blocks: int | None = None,
) -> ModelRole:
    """The trend model — binary GREEN/RED of the next candle (فاز ۹۸).

    فاز ۹۸ (درخواست اپراتور): «کندل بعدی قرمزه یا سبز؟» به‌عنوان
    فیلتر جهت ورود. طبقه‌بندی دودسته‌ای روی کندل بعدیِ **هر تایم‌فریمی**
    (پیش‌فرض 1D؛ مثل range برای هر TF یک مدل):
      GREEN = close[t+1] >= close[t]
      RED   = close[t+1] <  close[t]
    احتمال کالیبرهٔ خروجی، گیت جهت ورود (مجوز ۵) می‌شود — براکت TP/SL
    همچنان از مدل رنج می‌آید.

    REUSE هوشمند: نقش «signal» دوباره‌استفاده می‌شود (TargetKind
    TRADE_SIGNAL، softmax، cross-entropy، Predictor مشترک) — فقط
    model_id/timeframe/window فرق دارد. برچسب‌ها از close-to-close
    ساخته می‌شوند (نه first-passage) — به trainer از طریق
    ``label_style="color"`` اعلام می‌شود.
    """
    return ModelRole(
        name="signal",  # نقش طبقه‌بندی دودسته‌ای (REUSE) — id متمایز است
        target=PredictionTarget(
            kind=TargetKind.TRADE_SIGNAL,
            horizon=horizon,
            timeframe=timeframe,
            threshold=0.0,  # first-passage نیست — برچسب رنگ است
        ),
        model_id=trend_model_id(timeframe),
        description=(
            f"Predicts the color (GREEN/RED) of the next {timeframe} candle "
            f"as probabilities, from {window_size} past candles."
        ),
        window_size=window_size,
        n_filters=32,
        n_layers_per_block=n_layers_per_block or 3,
        n_blocks=n_blocks or 2,
        depth_multiplier=8,
        dropout=0.15,
        l2=2.5e-4,
    )


def trend_signal_model_role(
    timeframe: str = "5M",
    threshold: float = 0.5,
    window_size: int = 288,
    label_horizon: int = 288,
    n_layers_per_block: int | None = None,
    n_blocks: int | None = None,
) -> ModelRole:
    """مدل «سیگنال ترند» (فاز ۹۹) — سه‌کلاسه BUY/HOLD/SELL.

    پنجره = 288 کندل (یک روز 5M) rolling؛ برچسب = اولین عبور
    ±threshold×ATR14 در label_horizon کندل بعدی، وگرنه HOLD.
    خروجی softmax سه‌کلاسه (num_classes=3).
    """
    return ModelRole(
        name="signal",  # reuse: softmax/cross-entropy/accuracy
        target=PredictionTarget(
            kind=TargetKind.TRADE_SIGNAL,
            horizon=1,
            timeframe=timeframe,
            threshold=threshold,  # X برحسب ATR14 — نه درصد
            num_classes=3,
        ),
        model_id=f"gold_trend_signal_{timeframe.strip().lower()}",
        description=(
            f"Trend signal: over the next {label_horizon} {timeframe} candles, "
            f"the first {threshold}xATR14 move from close decides "
            f"BUY/SELL; no barrier hit means HOLD."
        ),
        window_size=window_size,
        n_filters=32,
        n_layers_per_block=n_layers_per_block or 3,
        n_blocks=n_blocks or 2,
        depth_multiplier=8,
        dropout=0.15,
        l2=2.5e-4,
        label_horizon=label_horizon,
    )


def receptive_field(n_layers_per_block: int, n_blocks: int, kernel_size: int = 5) -> int:
    """Total causal receptive field of the dilated stack (فاز ۶۱).

    Each block stacks ``n_layers_per_block`` dilated convs with dilations
    1, 2, 4, … so one block reaches ``1 + (kernel-1) * (2**layers - 1)``
    bars back; ``n_blocks`` of them add up. The convention checked by the
    role docstrings is RF < window (coverage ~80%+), e.g. 5×2 → 249 for
    window=300 and 4×2 → 121 for window=150.
    """
    if n_layers_per_block < 1 or n_blocks < 1 or kernel_size < 2:
        raise ValidationError("n_layers_per_block/n_blocks >= 1 and kernel_size >= 2 required")
    return 1 + n_blocks * (kernel_size - 1) * (2**n_layers_per_block - 1)


def range_model_role(
    timeframe: str = "1D",
    horizon: int = 1,
    window_size: int = 150,
    n_layers_per_block: int | None = None,
    n_blocks: int | None = None,
) -> ModelRole:
    """The price-extremes model.

    فاز ۵۵: horizon=1 (فردا) بجای 5
      - دقت بالاتر: پیش‌بینی یک روز جلوتر
      - target واضح: high[t+1] و low[t+1]
      - no accumulation error

    timeframe=1D:
      150 روز = ~7 ماه context
      هر کندل = یک روز معاملاتی کامل
    Architecture:
      n_layers_per_block=4 -> RF=121 -> 81% of window=150
      n_filters=48, depth_multiplier=6, dropout=0.10, l2=2.0e-4
    """
    return ModelRole(
        name="range",
        target=PredictionTarget(
            kind=TargetKind.PRICE_RANGE,
            horizon=horizon,
            timeframe=timeframe,
        ),
        model_id=range_model_id(timeframe),
        description=(
            f"Predicts the highest high and lowest low over the next "
            f"{horizon} {timeframe} candles, as offsets from the current close."
        ),
        window_size=window_size,
        # Architecture knobs — range-specific
        n_filters=48,
        # فاز ۶۱: 4×2 (RF=121, 81% of 150) پیش‌فرض می‌ماند ولی override شدنی است
        n_layers_per_block=n_layers_per_block or 4,
        n_blocks=n_blocks or 2,
        depth_multiplier=6,
        dropout=0.10,
        l2=2.0e-4,
        seq2seq=True,  # Phase 55: gradient dense, no collapse
    )


def signal_model_role(
    timeframe: str = "5M",
    horizon: int = 0,
    threshold: float = 0.0008,
    window_size: int = 300,
    n_layers_per_block: int | None = None,
    n_blocks: int | None = None,
) -> ModelRole:
    """The binary direction model. Defaults to 5M bars and unbounded first-passage labels.

    فاز ۵۸: window=300, n_layers=5, n_blocks=2
      window=300: 300 × 5M = 25 ساعت ≈ یه روز کامل context
      n_layers=5, n_blocks=2: RF=249 = 20.8h = 83% coverage از window

    فاز ۶۱: ``n_layers_per_block``/``n_blocks`` قابل override هستند —
    مثلاً window=150 با 4×2 (RF=121، 81%) هماهنگ می‌شود. RF > window
    یعنی لایه‌های بیرونی فقط پارامتر اضافه‌اند (بیشترِ پنجره را pad صفر
    می‌بینند) — برای مدلی که همین حالا بیش‌برازش می‌شود، هدررفت است.
    """
    if threshold < 0:
        raise ValidationError("threshold must not be negative")
    return ModelRole(
        name="signal",
        target=PredictionTarget(
            kind=TargetKind.TRADE_SIGNAL,
            horizon=horizon,
            timeframe=timeframe,
            threshold=threshold,
        ),
        model_id=f"gold_signal_{timeframe.strip().lower()}",
        description=(
            f"Predicts sell / buy with probabilities over the next "
            f"{timeframe} candles until the first {threshold:.4%} "
            "price move is reached; no HOLD output class."
        ),
        window_size=window_size,
        # Architecture — پیش‌فرض فاز ۵۸، override فاز ۶۱
        n_filters=32,
        n_layers_per_block=n_layers_per_block or 5,  # RF=249 با n_blocks=2
        n_blocks=n_blocks or 2,
        depth_multiplier=8,
        dropout=0.15,
        l2=2.5e-4,
    )


def default_roles() -> Dict[str, ModelRole]:
    """Both roles, keyed by name."""
    return {"range": range_model_role(), "signal": signal_model_role()}
