"""باگ ۴۷/۴۸ — هندسهٔ targetهای seq2seq و متریک per-bound رنج.

ریشه: ``WindowedSample.target_index`` باید «سطر پایان پنجره در series»
باشد، ولی هر سه سازنده آن را با «شمارهٔ ستون target» (مثلاً 182) پر
می‌کردند. ``WavenetTrainer._build_seq2seq_targets`` آن را به‌عنوان اندیس
سطر می‌خواند → y همهٔ ۴٬۳۳۱ نمونه از سطرهای ۳۳..۱۸۲ ساخته می‌شد (یکسان!)
→ آموزش range seq2seq روی برچسب ثابت collapse می‌شد و ``_Seq2SeqMAE``
عدد جعلیِ نزدیک صفر (مثلاً val_mae 0.000081 ≈ ±$0.16) گزارش می‌کرد.

این تست‌ها قفل می‌کنند:
1. ``make_multi_target_windows`` → target_index = سطر پایان پنجره
2. ``build_samples_at`` و ``make_windows`` → همان قرارداد
3. y هر نمونه از سطر خودش می‌آید نه یک سطر ثابت
"""

from __future__ import annotations

from ShadBotTrader.infrastructure.ai.data_windowing import (
    build_samples_at,
    make_multi_target_windows,
    make_windows,
)


def _series(rows: int = 40, width: int = 5):
    return [
        [float(r) + c / 10.0 for c in range(width - 2)] + [100.0 + r, 90.0 + r] for r in range(rows)
    ]


def test_multi_target_windows_end_index_points_at_its_own_row():
    series = _series()
    samples = make_multi_target_windows(series, window_size=5, target_columns=[3, 4])

    assert len(samples) == len(series) - 4
    for position, sample in enumerate(samples):
        expected_end = 4 + position
        assert (
            sample.target_index == expected_end
        ), "target_index must be the window's own last row, not the column id"
        # targets از سطر end+horizon (horizon=0 → همان سطر آخر)
        assert sample.targets == [series[expected_end][3], series[expected_end][4]]


def test_two_samples_get_distinct_seq2seq_label_rows():
    """با باگ، هر دو نمونه y سطرهای ۳۳..۱۸۲ را می‌گرفتند — یکسان."""
    series = _series()
    a, b = make_multi_target_windows(series, window_size=5, target_columns=[3, 4])[:2]
    assert a.target_index != b.target_index


def test_build_samples_at_carries_row_index():
    series = _series()
    ends = [10, 20, 30]
    samples = build_samples_at(series, window_size=5, target_column=3, sample_ends=ends)
    assert [s.target_index for s in samples] == ends
    assert [s.target for s in samples] == [series[e][3] for e in ends]


def test_make_windows_carries_row_index():
    series = _series()
    samples = make_windows(series, window_size=5, target_column=3)
    assert [s.target_index for s in samples[:3]] == [4, 5, 6]
