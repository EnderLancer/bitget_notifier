from __future__ import annotations

from typing import Protocol, runtime_checkable

from bitget_notifier.bitget.models import Order


@runtime_checkable
class OrderStateStore(Protocol):
    """Persists the most recent snapshot of open orders for diffing.

    Implementations should return ``None`` from :meth:`load` when no snapshot
    has ever been saved, so the differ can recognise the first-run case and
    avoid spamming the user.
    """

    async def load(self) -> list[Order] | None: ...

    async def save(self, orders: list[Order]) -> None: ...
