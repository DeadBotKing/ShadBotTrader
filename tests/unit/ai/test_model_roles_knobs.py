"""فاز ۶۱ — پیچ‌های معماری (n_layers/n_blocks) در نقش‌های مدل.

پیش‌فرض فاز ۵۸ برای سیگنال ۵×۲ است (RF=249 برای window=300). اگر اپراتور
``--window 150`` بدهد بدون کاهش لایه‌ها، RF=249 > 150 می‌شود: لایه‌های
بیرونی فقط پارامتر هدررفته‌اند. این تست‌ها قفل می‌کنند که:

1. پیش‌فرض‌ها بدون override دست‌نخورده‌اند (سیگنال ۵×۲ · رنج ۴×۲)
2. override از CLI/factory درست عبور می‌کند
3. ``receptive_field`` فرمول درست دارد (249 / 121 / 125)
4. ورودی نامعتبر (صفر/منفی) رد می‌شود
"""

from __future__ import annotations

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.infrastructure.ai.model_roles import (
    range_model_role,
    receptive_field,
    signal_model_role,
)


def test_signal_defaults_unchanged():
    role = signal_model_role()
    assert role.n_layers_per_block == 5
    assert role.n_blocks == 2
    assert role.window_size == 300
    assert receptive_field(role.n_layers_per_block, role.n_blocks) == 249


def test_range_defaults_unchanged():
    role = range_model_role()
    assert role.n_layers_per_block == 4
    assert role.n_blocks == 2
    assert role.window_size == 150
    assert receptive_field(role.n_layers_per_block, role.n_blocks) == 121


def test_window_150_pairing_override():
    """--window 150 --n-layers 4 --n-blocks 2 → RF=121 = 81% پوشش."""
    role = signal_model_role(window_size=150, n_layers_per_block=4, n_blocks=2)
    assert role.window_size == 150
    assert role.n_layers_per_block == 4
    assert role.n_blocks == 2
    rf = receptive_field(role.n_layers_per_block, role.n_blocks)
    assert rf == 121
    assert rf < role.window_size


def test_receptive_field_formula():
    assert receptive_field(5, 2) == 249  # فاز ۵۸ سیگنال
    assert receptive_field(4, 2) == 121  # رنج / جفت‌شدن window=150
    assert receptive_field(5, 1) == 125  # یک بلاک
    assert receptive_field(3, 2) == 57  # پیش‌فرض قدیمی فاز ۲۹


def test_receptive_field_rejects_invalid():
    with pytest.raises(ValidationError):
        receptive_field(0, 2)
    with pytest.raises(ValidationError):
        receptive_field(5, 0)
    with pytest.raises(ValidationError):
        receptive_field(5, 2, kernel_size=1)


def test_factory_rejects_invalid_layers():
    with pytest.raises(ValidationError):
        receptive_field(-1, 2)
