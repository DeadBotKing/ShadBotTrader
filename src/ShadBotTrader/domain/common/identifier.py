"""A unique identifier value object."""

from __future__ import annotations

from uuid import UUID, uuid4

from ShadBotTrader.domain.common.value_object import ValueObject


class Identifier(ValueObject):
    """A universally unique identifier used as an entity identity."""

    def __init__(self, value: UUID | None = None) -> None:
        self._uuid = value or uuid4()

    @property
    def value(self) -> UUID:
        """The underlying UUID."""
        return self._uuid

    def _value(self) -> tuple[UUID]:
        return (self._uuid,)

    def __str__(self) -> str:
        return str(self._uuid)
