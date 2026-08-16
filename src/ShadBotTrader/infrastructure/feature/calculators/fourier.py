"""Fourier resonance features: sin/cos of the dominant price cycle.

The resonance period is fitted on the whole input series (batch fit), so
these features are declared ``NON_CAUSAL`` and must not enter live
trading (Phase 12, section 29).
"""

from __future__ import annotations

import numpy as np

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeaturePoint, FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import derived_frame


def dominant_period(values: np.ndarray) -> float:
    """Return the dominant period (in bars) via the FFT magnitude peak.

    Skips the zero-frequency (DC) component.
    """
    clean = values[~np.isnan(values)]
    if len(clean) < 4:
        return 1.0
    detrended = clean - np.mean(clean)
    spectrum = np.abs(np.fft.rfft(detrended))
    spectrum[0] = 0.0
    if np.all(spectrum == 0):
        return 1.0
    peak_bin = int(np.argmax(spectrum))
    if peak_bin == 0:
        return 1.0
    return len(clean) / peak_bin


class FourierCalculator(FeatureCalculator):
    """Emits ``sin_{n}_{column}`` or ``cos_{n}_{column}`` of a price cycle.

    ``freq`` is the resonance period (in bars) estimated from the series;
    ``function`` selects sine or cosine.
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        column = str(definition.parameters["column"])
        function = str(definition.parameters["function"])
        frame = derived_frame(context)

        series = frame[column].astype(float)
        period = dominant_period(series.to_numpy())
        phase = 2.0 * np.pi / period * np.arange(len(series), dtype=float)

        if function == "cos":
            values = np.cos(phase)
        else:
            values = np.sin(phase)

        points = [
            FeaturePoint(timestamp=candle.open_time, value=float(value))
            for candle, value in zip(context.candles, values, strict=False)
        ]
        return FeatureResult(feature_id=definition.feature_id.value, points=points, warmup=0)
