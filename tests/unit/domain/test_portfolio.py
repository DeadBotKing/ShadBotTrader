"""Tests for the portfolio domain."""

from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.portfolio.account import Account
from ShadBotTrader.domain.portfolio.balance import Balance


def test_account_deposit_and_withdraw():
    account = Account(Balance("100", "USD"))
    account.deposit(Balance("50", "USD"))
    assert account.balance.amount == Decimal("150")
    account.withdraw(Balance("30", "USD"))
    assert account.balance.amount == Decimal("120")


def test_withdraw_more_than_balance_raises():
    account = Account(Balance("100", "USD"))
    with pytest.raises(ValidationError):
        account.withdraw(Balance("101", "USD"))


def test_currency_mismatch_raises():
    account = Account(Balance("100", "USD"))
    with pytest.raises(ValidationError):
        account.deposit(Balance("50", "EUR"))
