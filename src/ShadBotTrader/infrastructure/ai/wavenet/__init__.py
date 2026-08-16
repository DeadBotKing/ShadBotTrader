"""WaveNet model and trainer (TensorFlow adapter, lazy import).

The WaveNet architecture is ported from the legacy
``TimeSeriesSignalPredictor`` and uses causal convolutions with gated
activations and skip connections — inherently roll-forward safe because
every layer only sees past values. Importing this package requires
TensorFlow; the rest of the AI Platform works without it.
"""
