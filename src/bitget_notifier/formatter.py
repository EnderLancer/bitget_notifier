from __future__ import annotations

from html import escape

from bitget_notifier.bitget.models import Order
from bitget_notifier.differ import ChangeKind, OrderChange

_KIND_PREFIX = {
    ChangeKind.ADDED: "\U0001f7e2 <b>New order</b>",
    ChangeKind.REMOVED: "\U0001f534 <b>Order closed</b>",
    ChangeKind.MODIFIED: "✏️ <b>Order modified</b>",
}


def format_changes(changes: list[OrderChange]) -> str:
    return "\n\n".join(_format_change(c) for c in changes)


def _format_change(change: OrderChange) -> str:
    header = _KIND_PREFIX[change.kind]
    body = _format_order(change.order)
    if change.kind is ChangeKind.MODIFIED and change.previous is not None:
        body += "\n" + _format_diff(change.previous, change.order)
    return f"{header}\n{body}"


def _format_order(o: Order) -> str:
    lines = [
        f"<b>{escape(o.symbol)}</b> {escape(o.side.upper())} {escape(o.order_type)}",
        f"size: <code>{o.size}</code>  price: <code>{o.price}</code>",
        f"status: <code>{escape(o.status)}</code>",
        f"id: <code>{escape(o.order_id)}</code>",
    ]
    return "\n".join(lines)


def _format_diff(prev: Order, curr: Order) -> str:
    deltas = []
    if prev.status != curr.status:
        deltas.append(f"status: <code>{escape(prev.status)}</code> → <code>{escape(curr.status)}</code>")
    if prev.size != curr.size:
        deltas.append(f"size: <code>{prev.size}</code> → <code>{curr.size}</code>")
    if prev.price != curr.price:
        deltas.append(f"price: <code>{prev.price}</code> → <code>{curr.price}</code>")
    return "changes: " + ", ".join(deltas) if deltas else ""
