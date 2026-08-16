"""WaveNet architecture builder (TensorFlow, causal, gated).

Ported cleanly from the legacy implementation and made compatible with
Keras 3 (TF >= 2.16), which removed the ``padding="causal"`` shorthand:
causality is now enforced explicitly with left-padding
(``ZeroPadding1D``) followed by a ``valid`` convolution. Every layer
only sees past values, so the model is roll-forward safe by
construction. TensorFlow is imported lazily so the rest of the AI
Platform works without it.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _require_tensorflow() -> Any:
    """Import TensorFlow or fail with an actionable message.

    On native Windows TensorFlow is CPU-only from 2.11 onwards (GPU
    requires WSL2), but installation itself works fine on Python
    3.10-3.13. This keeps the failure clear instead of a bare
    ``ModuleNotFoundError``.
    """
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
# Gated activation unit
#
# NOTE: this layer MUST be defined at module scope (not inside a factory
# function) and registered with Keras' serialization registry. A class
# created inside a function gets a fresh identity on every call, so Keras
# cannot resolve it when deserializing a saved model, which made
# ``keras.models.load_model`` fail with:
#     Could not locate class '_GatedActivationUnit'
# --------------------------------------------------------------------------

_GATED_ACTIVATION_UNIT: Any = None


def _gated_activation_unit_class() -> Any:
    """Build (once) and return the registered gated-activation layer class."""
    global _GATED_ACTIVATION_UNIT
    if _GATED_ACTIVATION_UNIT is not None:
        return _GATED_ACTIVATION_UNIT

    tf: Any = _require_tensorflow()

    # Use the top-level ``keras`` package when available: the ``tf.keras``
    # shim in TF >= 2.16 does not expose ``keras.saving``.
    try:
        import keras as _keras  # type: ignore[import-not-found]

        _register = _keras.saving.register_keras_serializable
    except (ImportError, AttributeError):  # pragma: no cover - legacy TF
        _register = tf.keras.utils.register_keras_serializable

    @_register(package="ShadBotTrader")
    class GatedActivationUnit(tf.keras.layers.Layer):  # type: ignore[name-defined,misc]
        """WaveNet gated activation: ``activation(x[:h]) * sigmoid(x[h:])``."""

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


def gated_activation_layer(activation: str = "tanh") -> Any:
    """Return a gated-activation Keras layer instance (lazy TF import).

    Splits the input along the last axis into two halves; the first half
    passes through ``activation`` and the second half through sigmoid,
    and the two are multiplied (WaveNet gated activation).
    """
    return _gated_activation_unit_class()(activation_name=activation)


def custom_objects() -> Dict[str, Any]:
    """Custom Keras objects required to deserialize a saved WaveNet.

    Pass to ``keras.models.load_model(..., custom_objects=...)`` as a
    belt-and-braces measure alongside the serialization registry.
    """
    cls = _gated_activation_unit_class()
    return {
        "GatedActivationUnit": cls,
        "ShadBotTrader>GatedActivationUnit": cls,
        # Backwards compatibility with models saved before the layer was
        # moved to module scope and renamed.
        "_GatedActivationUnit": cls,
    }


def causal_conv1d(
    inputs: Any,
    filters: int,
    kernel_size: int,
    dilation_rate: int,
    l2: float,
    **kwargs: Any,
) -> Any:
    """A causal 1D convolution (left padding + valid convolution)."""
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
    """A causal separable 1D convolution."""
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
    """One WaveNet residual block (returns the residual + skip tensors)."""
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


def build_wavenet(
    window_size: int,
    n_features: int,
    n_filters: int = 32,
    kernel_size: int = 5,
    n_layers_per_block: int = 4,
    n_blocks: int = 2,
    output_units: int = 2,
    output_activation: str = "sigmoid",
    depth_multiplier: int = 20,
    l2: float = 1.5e-4,
    dropout: float = 0.05,
) -> Any:
    """Build the WaveNet classification model.

    Args:
        window_size: length of the input window (time steps).
        n_features: number of input feature columns.
        n_filters: filters per convolution.
        kernel_size: kernel size of the causal convolutions.
        n_layers_per_block: dilations per block are ``2**i`` for i in range.
        n_blocks: number of dilation blocks.
        output_units: number of output classes.
        output_activation: activation of the output layer.
        depth_multiplier: depth multiplier of the separable convolutions.
        l2: L2 regularization strength.
        dropout: dropout rate.

    Returns:
        An uncompiled ``tf.keras.Model``.
    """
    tf = _require_tensorflow()

    inputs = tf.keras.layers.Input(shape=[window_size, n_features])

    z = causal_separable_conv1d(
        inputs,
        filters=n_filters,
        kernel_size=min(10, window_size),
        l2=l2,
        depth_multiplier=depth_multiplier,
    )
    z = tf.keras.layers.Dropout(dropout)(z)

    skip_outputs: List[Any] = []
    dilation_stack: List[int] = []
    for _ in range(n_blocks):
        dilation_stack.extend(2**i for i in range(n_layers_per_block))

    for dilation_rate in dilation_stack:
        z, skip = wavenet_residual_block(z, n_filters, dilation_rate, kernel_size, l2, dropout)
        skip_outputs.append(skip)

    z = tf.keras.activations.relu(tf.keras.layers.Add()(skip_outputs))

    z = causal_separable_conv1d(
        z,
        filters=n_filters,
        kernel_size=min(5, window_size),
        l2=l2,
        depth_multiplier=depth_multiplier,
        activation="relu",
    )

    flattened = tf.keras.layers.Flatten()(z)
    output = tf.keras.layers.Dense(
        units=output_units,
        activation=output_activation,
        kernel_regularizer=tf.keras.regularizers.L2(l2),
        activity_regularizer=tf.keras.regularizers.L2(l2),
    )(flattened)

    return tf.keras.Model(inputs=[inputs], outputs=[output], name="wavenet")
