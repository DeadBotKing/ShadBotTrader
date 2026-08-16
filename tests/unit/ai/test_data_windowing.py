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


def test_make_windows_can_drop_target_column():
    """The target column must be removable from the feature rows.

    Regression guard: with ``horizon=0`` the label lives in the last row
    of its own window, so leaving the target column in the features
    leaks the answer straight into the model input.
    """
    series = [
        [1.0, 10.0, 100.0],
        [2.0, 11.0, 200.0],
        [3.0, 12.0, 300.0],
    ]
    windows = make_windows(series, window_size=2, target_column=1, drop_target_column=True)

    assert windows[0].features == [[1.0, 100.0], [2.0, 200.0]]
    assert windows[0].target == 11.0
    # every row lost exactly the target column
    assert all(len(row) == 2 for w in windows for row in w.features)


def test_build_samples_drop_target_column_matches_width():
    series = [[float(i), float(i * 2), float(i % 2)] for i in range(6)]
    kept = build_samples(series, window_size=3, target_column=2, scale=False)
    dropped = build_samples(
        series, window_size=3, target_column=2, scale=False, drop_target_column=True
    )

    assert len(kept[0].features[0]) == 3
    assert len(dropped[0].features[0]) == 2
    assert kept[0].target == dropped[0].target
