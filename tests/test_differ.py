from __future__ import annotations

from decimal import Decimal

from bitget_notifier.bitget.models import Order
from bitget_notifier.differ import ChangeKind, diff_orders


def _order(order_id: str, **overrides: object) -> Order:
    defaults = {
        "orderId": order_id,
        "symbol": "BTCUSDT",
        "side": "buy",
        "orderType": "limit",
        "size": Decimal("0.01"),
        "price": Decimal("60000"),
        "status": "live",
    }
    defaults.update(overrides)
    return Order.model_validate(defaults)


def test_first_run_returns_empty() -> None:
    curr = [_order("1"), _order("2")]
    assert diff_orders(None, curr) == []


def test_detects_added_order() -> None:
    prev = [_order("1")]
    curr = [_order("1"), _order("2")]
    changes = diff_orders(prev, curr)
    assert len(changes) == 1
    assert changes[0].kind is ChangeKind.ADDED
    assert changes[0].order.order_id == "2"


def test_detects_removed_order() -> None:
    prev = [_order("1"), _order("2")]
    curr = [_order("1")]
    changes = diff_orders(prev, curr)
    assert len(changes) == 1
    assert changes[0].kind is ChangeKind.REMOVED
    assert changes[0].order.order_id == "2"


def test_detects_modified_order_on_status_change() -> None:
    prev = [_order("1", status="live")]
    curr = [_order("1", status="partially_filled")]
    changes = diff_orders(prev, curr)
    assert len(changes) == 1
    assert changes[0].kind is ChangeKind.MODIFIED
    assert changes[0].previous is not None
    assert changes[0].previous.status == "live"
    assert changes[0].order.status == "partially_filled"


def test_detects_modified_order_on_price_change() -> None:
    prev = [_order("1", price=Decimal("60000"))]
    curr = [_order("1", price=Decimal("61000"))]
    changes = diff_orders(prev, curr)
    assert len(changes) == 1
    assert changes[0].kind is ChangeKind.MODIFIED


def test_no_changes_when_snapshots_match() -> None:
    snapshot = [_order("1"), _order("2")]
    assert diff_orders(snapshot, snapshot) == []


def test_mix_of_changes() -> None:
    prev = [_order("1"), _order("2"), _order("3", size=Decimal("0.01"))]
    curr = [_order("2"), _order("3", size=Decimal("0.02")), _order("4")]
    changes = diff_orders(prev, curr)
    kinds = {(c.kind, c.order.order_id) for c in changes}
    assert kinds == {
        (ChangeKind.REMOVED, "1"),
        (ChangeKind.MODIFIED, "3"),
        (ChangeKind.ADDED, "4"),
    }
