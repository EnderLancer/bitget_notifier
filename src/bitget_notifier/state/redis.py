from __future__ import annotations

from bitget_notifier.bitget.models import Order


class RedisStore:
    """Reserved seam for multi-tenant / horizontally-scaled deployments.

    The poll loop already depends on the :class:`OrderStateStore` protocol, so
    swapping :class:`JsonFileStore` for a real Redis implementation is a
    drop-in change. Implement :py:meth:`load` and :py:meth:`save` against a
    redis-py asyncio client and key snapshots by ``user_id`` /
    ``account_id`` when the multi-tenant feature lands.
    """

    def __init__(self, *_: object, **__: object) -> None:
        raise NotImplementedError(
            "RedisStore is reserved for the multi-tenant scale-up; "
            "use STATE_BACKEND=json today."
        )

    async def load(self) -> list[Order] | None:  # pragma: no cover - stub
        raise NotImplementedError

    async def save(self, orders: list[Order]) -> None:  # pragma: no cover - stub
        raise NotImplementedError
