"""Principal-component features via SVD (batch fit, non-causal)."""

from __future__ import annotations

import numpy as np

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import (
    derived_frame,
    result_from_series,
)

_PCA_COLUMNS = (
    "open",
    "close",
    "low",
    "high",
    "HL/2",
    "HLC/3",
    "HLCC/4",
    "OHLC/4",
    "volume",
)


class PcaCalculator(FeatureCalculator):
    """Computes one principal component (``pca_{component}``).

    The component scores come from an SVD of the standardized OHLCV
    matrix. The fit is over the whole input series, so this family is
    declared ``NON_CAUSAL`` (research only).
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        component = int(definition.parameters["component"])
        frame = derived_frame(context)
        matrix = frame[list(_PCA_COLUMNS)].to_numpy(dtype=np.float64)

        centered = matrix - matrix.mean(axis=0, keepdims=True)
        std = centered.std(axis=0)
        std[std == 0.0] = 1.0
        standardized = centered / std

        u_matrix, singular, _ = np.linalg.svd(standardized, full_matrices=False)
        scores = u_matrix * singular  # n x k
        if component >= scores.shape[1]:
            values = np.zeros(len(frame))
        else:
            values = scores[:, component]

        series = result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=pd_series(values, frame),
            warmup=0,
        )
        return series


def pd_series(values, frame):
    import pandas as pd

    return pd.Series(values, index=frame.index)
