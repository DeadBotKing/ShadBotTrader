"""Tests for the Result type."""

import pytest

from ShadBotTrader.core.result import Result


def test_ok_result_holds_value():
    result = Result.ok(42)
    assert result.is_ok is True
    assert result.is_failure is False
    assert result.unwrap() == 42


def test_fail_result_raises_underlying_error():
    error = RuntimeError("boom")
    result = Result.fail(error)
    assert result.is_failure is True
    with pytest.raises(RuntimeError, match="boom"):
        result.unwrap()


def test_unwrap_or_falls_back_on_failure():
    assert Result.fail(RuntimeError()).unwrap_or(7) == 7
    assert Result.ok(3).unwrap_or(7) == 3


def test_both_value_and_error_rejected():
    with pytest.raises(ValueError):
        Result(value=1, error=RuntimeError())


def test_ok_with_none_value_is_a_valid_success():
    result = Result.ok(None)
    assert result.is_ok is True
    assert result.unwrap() is None
