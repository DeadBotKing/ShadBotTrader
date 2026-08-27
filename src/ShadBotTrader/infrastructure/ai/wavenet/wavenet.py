"""WaveNet architecture builder (TensorFlow, causal, gated).

Head بدون Flatten:
  classification: skip_sum -> ReLU -> Conv1x1 -> LastTimestep -> Dense(softmax)
  regression:     skip_sum -> ReLU -> Conv1x1 -> concat(last+avg) -> MLP -> Dense(linear)

Lambda layer جایش LastTimestep custom layer (serialize میشه).

Range head بهبودیافته:
  concat(LastTimestep, GlobalAvgPool) → Dense(32, relu) → Dropout → Dense(2, linear)
  - LastTimestep: اطلاعات آخرین روز (مهم‌ترین)
  - GlobalAvgPool: خلاصه کل دوره
  - MLP: رابطه غیرخطی بین دو اطلاعات
"""

from __future__ import annotations

from typing import Any, Dict, List


def _require_tensorflow() -> Any:
    try:
        import tensorflow as tf  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "TensorFlow is required for the Wavenet model but is not "
            "installed. Install it with 'pip install tensorflow-cpu' on "
            "Windows (CPU-only; use WSL2 if you need GPU) or "
            "'pip install tensorflow' on Linux/macOS. Every other AI "
            "Platform feature works without TensorFlow."
        ) from exc
    return tf


# --------------------------------------------------------------------------
# Custom layers — must be at module scope and registered
# --------------------------------------------------------------------------

_GATED_ACTIVATION_UNIT: Any = None
_LAST_TIMESTEP_LAYER: Any = None


def _gated_activation_unit_class() -> Any:
    global _GATED_ACTIVATION_UNIT
    if _GATED_ACTIVATION_UNIT is not None:
        return _GATED_ACTIVATION_UNIT

    tf: Any = _require_tensorflow()

    try:
        import keras as _keras
        _register = _keras.saving.register_keras_serializable
    except (ImportError, AttributeError):
        _register = tf.keras.utils.register_keras_serializable

    @_register(package="ShadBotTrader")
    class GatedActivationUnit(tf.keras.layers.Layer):  # type: ignore[name-defined,misc]
        """WaveNet gated activation: tanh(x[:h]) * sigmoid(x[h:])."""

        def __init__(self, activation_name: str = "tanh", **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.activation_name = activation_name

        def call(self, inputs: Any) -> Any:
            n_filters = inputs.shape[-1] // 2
            linear_output = tf.keras.activations.get(self.activation_name)(inputs[..., :n_filters])
            gate = tf.keras.activations.sigmoid(inputs[..., n_filters:])
            return linear_output * gate

        def compute_output_shape(self, input_shape: Any) -> Any:
            shape = list(input_shape)
            if shape[-1] is not None:
                shape[-1] = shape[-1] // 2
            return tuple(shape)

        def get_config(self) -> Dict[str, Any]:
            config = super().get_config()
            config.update({"activation_name": self.activation_name})
            return config

    _GATED_ACTIVATION_UNIT = GatedActivationUnit
    return GatedActivationUnit


def _last_timestep_layer_class() -> Any:
    """Custom layer: آخرین timestep از sequence.

    جایگزین Lambda(lambda x: x[:, -1, :]) که در Keras safe_mode
    serialize نمیشه و خطای 'Python lambda disallowed' میده.
    """
    global _LAST_TIMESTEP_LAYER
    if _LAST_TIMESTEP_LAYER is not None:
        return _LAST_TIMESTEP_LAYER

    tf: Any = _require_tensorflow()

    try:
        import keras as _keras
        _register = _keras.saving.register_keras_serializable
    except (ImportError, AttributeError):
        _register = tf.keras.utils.register_keras_serializable

    @_register(package="ShadBotTrader")
    class LastTimestep(tf.keras.layers.Layer):  # type: ignore[name-defined,misc]
        """(batch, time, features) -> (batch, features) — آخرین timestep.

        در WaveNet causal، t=-1 حاوی خلاصه کل تاریخچه است.
        """

        def call(self, inputs: Any) -> Any:
            return inputs[:, -1, :]

        def compute_output_shape(self, input_shape: Any) -> Any:
            return (input_shape[0], input_shape[2])

    _LAST_TIMESTEP_LAYER = LastTimestep
    return LastTimestep


def gated_activation_layer(activation: str = "tanh") -> Any:
    return _gated_activation_unit_class()(activation_name=activation)


def custom_objects() -> Dict[str, Any]:
    """Custom Keras objects for deserializing a saved WaveNet.

    فاز ۷۰ (باگ ۵۱): کلاس‌های رنج (RangeLoss/_RangeLoss، Seq2SeqMAE/
    _Seq2SeqMAE) حالا ماژول‌سطح در wavenet_trainer هستند و همیشه در
    دسترس — قبلاً local class بودند و load هر مدل رنج با
    «Could not locate class '_RangeLoss'» می‌شکست.
    """
    gau = _gated_activation_unit_class()
    lt = _last_timestep_layer_class()

    from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
        range_custom_objects,
    )

    return {
        "GatedActivationUnit":               gau,
        "ShadBotTrader>GatedActivationUnit": gau,
        "_GatedActivationUnit":              gau,   # backwards compat
        "LastTimestep":                      lt,
        "ShadBotTrader>LastTimestep":        lt,
        **range_custom_objects(),
    }


# --------------------------------------------------------------------------
# Causal convolutions
# --------------------------------------------------------------------------

def causal_conv1d(
    inputs: Any,
    filters: int,
    kernel_size: int,
    dilation_rate: int,
    l2: float,
    **kwargs: Any,
) -> Any:
    tf = _require_tensorflow()
    pad = (kernel_size - 1) * dilation_rate
    padded = tf.keras.layers.ZeroPadding1D((pad, 0))(inputs)
    return tf.keras.layers.Conv1D(
        filters=filters,
        kernel_size=kernel_size,
        padding="valid",
        dilation_rate=dilation_rate,
        kernel_regularizer=tf.keras.regularizers.L2(l2),
        activity_regularizer=tf.keras.regularizers.L2(l2),
        **kwargs,
    )(padded)


def causal_separable_conv1d(
    inputs: Any,
    filters: int,
    kernel_size: int,
    l2: float,
    depth_multiplier: int,
    **kwargs: Any,
) -> Any:
    tf = _require_tensorflow()
    pad = kernel_size - 1
    padded = tf.keras.layers.ZeroPadding1D((pad, 0))(inputs)
    return tf.keras.layers.SeparableConv1D(
        filters=filters,
        kernel_size=kernel_size,
        padding="valid",
        depth_multiplier=depth_multiplier,
        depthwise_regularizer=tf.keras.regularizers.L2(l2),
        pointwise_regularizer=tf.keras.regularizers.L2(l2),
        activity_regularizer=tf.keras.regularizers.L2(l2),
        **kwargs,
    )(padded)


def wavenet_residual_block(
    inputs: Any,
    n_filters: int,
    dilation_rate: int,
    kernel_size: int,
    l2: float,
    dropout: float,
) -> tuple[Any, Any]:
    import tensorflow as tf

    z = causal_conv1d(
        inputs,
        filters=n_filters * 2,
        kernel_size=kernel_size,
        dilation_rate=dilation_rate,
        l2=l2,
    )
    z = gated_activation_layer()(z)
    z = tf.keras.layers.Conv1D(
        filters=n_filters,
        kernel_size=1,
        kernel_regularizer=tf.keras.regularizers.L2(l2),
        activity_regularizer=tf.keras.regularizers.L2(l2),
    )(z)
    z = tf.keras.layers.Dropout(dropout)(z)
    return tf.keras.layers.Add()([z, inputs]), z


# --------------------------------------------------------------------------
# Main build
# --------------------------------------------------------------------------

def build_wavenet(
    window_size: int,
    n_features: int,
    n_filters: int = 32,
    kernel_size: int = 5,
    n_layers_per_block: int = 3,
    n_blocks: int = 2,
    output_units: int = 2,
    output_activation: str = "sigmoid",
    depth_multiplier: int = 8,
    l2: float = 2.5e-4,
    dropout: float = 0.10,
    is_regression: bool = False,
    seq2seq: bool = False,
    horizon: int = 5,
) -> Any:
    """Build WaveNet with sequence-aware head (no Flatten).

    Signal (classification):
      ...residual blocks... -> Conv1x1 -> LastTimestep -> Dense(softmax)
      آخرین timestep در causal conv = خلاصه کل تاریخچه

    Range Scalar (is_regression=True, seq2seq=False):
      ...residual blocks... -> Conv1x1 -> concat(last+avg) -> MLP -> Dense(2, linear)

    Range Seq2Seq (is_regression=True, seq2seq=True):  [فاز ۵۵]
      ...residual blocks... -> Conv1x1 -> SeparableConv1D(horizon*2, causal)
      -> output[batch, window, horizon*2]
      برای هر timestep t: [high_1..high_H, low_1..low_H]
      Loss فقط روی آخرین H timestep اعمال میشه
      gradient به همه لایه‌های WaveNet مستقیم میرسه
    """
    tf = _require_tensorflow()

    inputs = tf.keras.layers.Input(shape=[window_size, n_features])

    # Input projection
    z = causal_separable_conv1d(
        inputs,
        filters=n_filters,
        kernel_size=min(10, window_size),
        l2=l2,
        depth_multiplier=depth_multiplier,
    )
    z = tf.keras.layers.Dropout(dropout)(z)

    # Dilated causal residual blocks
    skip_outputs: List[Any] = []
    dilation_stack: List[int] = []
    for _ in range(n_blocks):
        dilation_stack.extend(2**i for i in range(n_layers_per_block))

    for dilation_rate in dilation_stack:
        z, skip = wavenet_residual_block(z, n_filters, dilation_rate, kernel_size, l2, dropout)
        skip_outputs.append(skip)

    z = tf.keras.activations.relu(tf.keras.layers.Add()(skip_outputs))

    # Post-processing separable conv
    z = causal_separable_conv1d(
        z,
        filters=n_filters,
        kernel_size=min(5, window_size),
        l2=l2,
        depth_multiplier=depth_multiplier,
        activation="relu",
    )

    # 1x1 conv on full sequence
    z = tf.keras.layers.Conv1D(
        filters=n_filters,
        kernel_size=1,
        activation="relu",
        kernel_regularizer=tf.keras.regularizers.L2(l2),
        name="head_conv1x1",
    )(z)

    if is_regression and seq2seq:
        # ── Range Seq2Seq head [فاز ۵۵] ──────────────────────────────────
        # خروجی: [batch, window, horizon*2]
        # channel layout: [high_1, low_1, high_2, low_2, ..., high_H, low_H]
        #
        # SeparableConv1D causal: هر timestep t فقط از t' <= t اطلاع داره
        # gradient مستقیم به همه لایه‌های WaveNet میرسه (150× signal)
        n_out = horizon * 2   # برای هر step: high + low
        z = causal_separable_conv1d(
            z,
            filters=max(n_filters // 2, n_out),
            kernel_size=3,
            l2=l2,
            depth_multiplier=4,
            activation="relu",
            name="seq2seq_pre",
        )
        output = causal_separable_conv1d(
            z,
            filters=n_out,
            kernel_size=1,
            l2=l2,
            depth_multiplier=1,
            activation="linear",
            name="seq2seq_out",
        )

    elif is_regression:
        # ── Range Scalar head (قدیمی) ─────────────────────────────────────
        last = _last_timestep_layer_class()(name="last_timestep")(z)
        avg  = tf.keras.layers.GlobalAveragePooling1D(name="global_avg_pool")(z)
        z = tf.keras.layers.Concatenate(name="last_avg_concat")([last, avg])
        z = tf.keras.layers.Dense(
            units=32,
            activation="relu",
            kernel_regularizer=tf.keras.regularizers.L2(l2),
            name="mlp_hidden",
        )(z)
        z = tf.keras.layers.Dropout(dropout, name="mlp_dropout")(z)
        output = tf.keras.layers.Dense(
            units=output_units,
            activation=output_activation,
            kernel_regularizer=tf.keras.regularizers.L2(l2),
            name="output",
        )(z)

    else:
        # ── Signal head: آخرین timestep → softmax ─────────────────────────
        z = _last_timestep_layer_class()(name="last_timestep")(z)
        output = tf.keras.layers.Dense(
            units=output_units,
            activation=output_activation,
            kernel_regularizer=tf.keras.regularizers.L2(l2),
            name="output",
        )(z)

    return tf.keras.Model(inputs=[inputs], outputs=[output], name="wavenet")
