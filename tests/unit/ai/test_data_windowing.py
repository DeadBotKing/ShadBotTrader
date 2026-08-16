"""Tests for the windowing helper."""

from ShadBotTrader.infrastructure.ai.data_windowing import (
    build_samples,
    make_windows,
    minmax_scale_window,
)


def test_make_windows_aligns_target():
    series = [
        [1.0, 10.0],
        [2.0, 11.0],
        [3.0, 12.0],
        [4.0, 13.0],
    ]
    windows = make_windows(series, window_size=2, target_column=1)
    # windows end at index 1, 2, 3 -> 3 windows
    assert len(windows) == 3
    assert windows[0].features == [[1.0, 10.0], [2.0, 11.0]]
    assert windows[0].target == 11.0  # last row, target column


def test_make_windows_horizon_shifts_label():
    series = [
        [1.0, 10.0],
        [2.0, 11.0],
        [3.0, 12.0],
        [4.0, 13.0],
    ]
    windows = make_windows(series, window_size=2, target_column=1, horizon=1)
    # label = value at end+1
    assert windows[0].target == 12.0


def test_minmax_scale_bounds():
    window = [[0.0, 5.0], [10.0, 15.0]]
    scaled = minmax_scale_window(window)
    # first column scaled from 0..10 -> -2..2
    assert scaled[0][0] == -2.0
    assert scaled[1][0] == 2.0
    assert scaled[0][1] == -2.0
    assert scaled[1][1] == 2.0


def test_build_samples_scales():
    series = [[0.0], [5.0], [10.0], [15.0], [20.0]]
    samples = build_samples(series, window_size=3, target_column=0, scale=True)
    assert samples[0].features[0][0] == -2.0  # min of window scaled
