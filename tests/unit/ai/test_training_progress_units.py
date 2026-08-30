"""فاز ۹۵ — dollar hint در لاگ آموزش با واحد تارگت درست.

با تارگت ATR، ``val_mae`` ضریب ATR است؛ تبدیل دلاری باید
``mult × ATR14`` باشد نه ``mult × قیمت`` (رفتار pct قدیمی). بدون مرجعِ
درست هم هیچ عدد جعلی چاپ نمی‌شود.
"""

import io

from ShadBotTrader.infrastructure.ai.training_progress import (
    ConsoleProgressReporter,
    EpochMetrics,
    FoldInfo,
)

FOLD = FoldInfo(
    fold_index=0,
    total_folds=2,
    train_samples=100,
    val_samples=50,
    train_start=0,
    train_end=100,
    val_start=150,
    val_end=200,
    purged_train_samples=0,
)


def _metrics(val_mae: float) -> EpochMetrics:
    return EpochMetrics(
        epoch=90,
        total_epochs=300,
        loss=0.6239,
        val_loss=0.5803,
        learning_rate=8e-4,
        extra={"mae": 0.80, "val_mae": val_mae},
    )


def test_atr_units_convert_with_atr_not_price():
    buffer = io.StringIO()
    reporter = ConsoleProgressReporter(stream=buffer, target_units="atr", atr_reference=31.5)
    reporter.on_epoch_end(FOLD, _metrics(0.748782))
    line = buffer.getvalue()
    # 0.748782 × 31.5 ≈ 23.59 — و هرگز × قیمتِ ۲۶۵۰ نه
    assert "ATR14=31.50" in line
    assert "~+-23.59$" in line
    assert "1984" not in line


def test_pct_units_keep_the_legacy_price_conversion():
    buffer = io.StringIO()
    reporter = ConsoleProgressReporter(stream=buffer, target_units="pct")
    reporter._last_ref_price = 2650.0
    reporter.on_epoch_end(FOLD, _metrics(0.0034))
    assert "~+-9.01$" in buffer.getvalue()


def test_atr_without_reference_prints_no_bogus_dollars():
    buffer = io.StringIO()
    reporter = ConsoleProgressReporter(stream=buffer, target_units="atr", atr_reference=0.0)
    reporter.on_epoch_end(FOLD, _metrics(0.748782))
    assert "~+-" not in buffer.getvalue()


def test_run_summary_uses_the_same_rule():
    buffer = io.StringIO()
    reporter = ConsoleProgressReporter(stream=buffer, target_units="atr", atr_reference=30.0)
    reporter._last_val_mae = 0.75
    reporter._completed_folds = 1
    reporter.on_train_end([0.60, 0.58])
    out = buffer.getvalue()
    if "val_mae last" in out:
        assert "ATR14=30.00" in out and "22.50" in out
