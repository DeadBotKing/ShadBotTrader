"""Wavelet noise filter (geometric mean of haar/db6/dmey), ported from legacy."""

from __future__ import annotations

import numpy as np
import pywt

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import (
    derived_frame,
    result_from_series,
)

_WAVELETS = ("haar", "db6", "dmey")
_SCALES = {"haar": 0.00008, "db6": 0.00008, "dmey": 0.00128}


def _writable_float64(series: np.ndarray) -> np.ndarray:
    """Return a guaranteed writable, C-contiguous float64 copy.

    ``np.ascontiguousarray`` only copies when necessary, so a read-only
    pandas-backed view can pass through untouched. PyWavelets (and other
    C extensions) reject read-only buffers, so we force a real copy here
    — this is what keeps the code working across pandas/numpy versions
    and platforms (Windows included).
    """
    return np.array(series, dtype=np.float64, copy=True)


class NoiseFilterCalculator(FeatureCalculator):
    """Denoises one price column with three wavelets (geometric mean).

    Mirrors the legacy ``NoiseCanceller.NoiseWavelet``: soft-threshold the
    detail coefficients of haar, db6 and dmey and combine the three
    reconstructions by geometric mean.
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        column = str(definition.parameters["column"])
        frame = derived_frame(context)
        series = frame[column].astype(float)

        clean = _writable_float64(series.dropna().to_numpy())
        if clean.size == 0:
            return result_from_series(
                feature_id=definition.feature_id.value,
                context=context,
                values=series,
                warmup=0,
            )

        reconstructions = []
        for wavelet in _WAVELETS:
            coefficients = pywt.wavedec(clean, wavelet, mode="periodization")
            threshold = _SCALES[wavelet] * float(np.mean(clean))
            coefficients[1:] = [
                pywt.threshold(coef, value=threshold, mode="soft") for coef in coefficients[1:]
            ]
            reconstructed = pywt.waverec(coefficients, wavelet, mode="periodization")
            reconstructions.append(reconstructed[: clean.size])

        combined = (reconstructions[0] * reconstructions[1] * reconstructions[2]) ** (1.0 / 3.0)

        values = series.copy()
        values.loc[series.notna()] = combined

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=0,
        )
