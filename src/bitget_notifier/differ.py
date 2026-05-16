from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bitget_notifier.bitget.models import Order


class ChangeKind(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


@dataclass(frozen=True)
class OrderChange:
    kind: ChangeKind
    order: Order
    previous: Order | None = None


def diff_orders(prev: list[Order] | None, curr: list[Order]) -> list[OrderChange]:
    """Compare two snapshots of open orders keyed by ``order_id``.

    Returns an empty list on the very first run (``prev is None``) so the user
    is not spammed with the entire backlog at startup.
    """
    if prev is None:
        return []

    prev_by_id = {o.order_id: o for o in prev}
    curr_by_id = {o.order_id: o for o in curr}

    changes: list[OrderChange] = []

    for order_id, order in curr_by_id.items():
        if order_id not in prev_by_id:
            changes.append(OrderChange(ChangeKind.ADDED, order))
        else:
            previous = prev_by_id[order_id]
            if previous.fingerprint() != order.fingerprint():
                changes.append(OrderChange(ChangeKind.MODIFIED, order, previous=previous))

    for order_id, previous in prev_by_id.items():
        if order_id not in curr_by_id:
            changes.append(OrderChange(ChangeKind.REMOVED, previous))

    return changes
