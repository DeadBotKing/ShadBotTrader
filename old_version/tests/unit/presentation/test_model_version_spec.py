"""فاز ۹۶ — انتخاب نسخهٔ مدل در فرم بکتست («id:vN»).

بدون نسخهٔ صریح، ``latest_version`` (بزرگ‌ترین شماره) لود می‌شد و مدل
قدیمیِ قبل از فاز ۹۵ روی بکتست می‌رفت (ران واقعی اپراتور: v2 قدیمی به
جای v1 جدیدِ ATR).
"""

from ShadBotTrader.presentation.commands.handlers import _split_model_spec


class TestSplitModelSpec:
    def test_empty_falls_back_to_default_and_latest(self):
        assert _split_model_spec("", "gold_range_1d") == ("gold_range_1d", None)
        assert _split_model_spec("   ", "gold_signal_5m") == ("gold_signal_5m", None)

    def test_bare_id_selects_latest(self):
        assert _split_model_spec("gold_range_1d", "x") == ("gold_range_1d", None)

    def test_id_with_version(self):
        assert _split_model_spec("gold_range_1d:v1", "x") == ("gold_range_1d", 1)
        assert _split_model_spec("gold_signal_5m:v3", "x") == ("gold_signal_5m", 3)

    def test_id_only_with_colon_keeps_default_version(self):
        assert _split_model_spec("gold_range_1d:", "x") == ("gold_range_1d", None)

    def test_non_numeric_version_is_ignored(self):
        assert _split_model_spec("gold_range_1d:abc", "x") == ("gold_range_1d", None)

    def test_whitespace_tolerant(self):
        assert _split_model_spec(" gold_range_1d : 2 ", "x") == ("gold_range_1d", 2)
