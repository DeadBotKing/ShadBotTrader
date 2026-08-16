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

    TensorFlow dropped native Windows support after 2.10, so the exact
    fix depends on the platform (see README). This keeps the failure
    clear instead of a bare ``ModuleNotFoundError``.
    """
    try:
        import tensorflow as tf  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "TensorFlow is required for the Wavenet model but is not "
            "installed. On Windows install tensorflow==2.10.1 with "
            "Python 3.9/3.10 (or use WSL2). On Linux/macOS: "
            "pip install tensorflow. Every other AI Platform feature "
            "works without TensorFlow."
        ) from exc
    return tf


def gated_activation_layer(activation: str = "tanh") -> Any:
    """Return a gated-activation Keras layer (lazy TF import).

    Splits the input along the last axis into two halves; the first half
    passes through ``activation`` and the second half through sigmoid,
    and the two are multiplied (WaveNet gated activation).
    """
    tf: Any = _require_tensorflow()

    class _GatedActivationUnit(tf.keras.layers.Layer):  # type: ignore[name-defined]
        def __init__(self, activation_name: str = "tanh", **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.activation_name = activation_name

        def call(self, inputs: Any) -> Any:
            n_filters = inputs.shape[-1] // 2
            linear_output = tf.keras.activations.get(self.activation_name)(inputs[..., :n_filters])
            gate = tf.keras.activations.sigmoid(inputs[..., n_filters:])
            return linear_output * gate

        def get_config(self) -> Dict[str, Any]:
            config = super().get_config()
            config.update({"activation_name": self.activation_name})
            return config

    return _GatedActivationUnit(activation_name=activation)


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
