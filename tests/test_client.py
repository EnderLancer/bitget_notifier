from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
import respx

from bitget_notifier.bitget.auth import BitgetCredentials
from bitget_notifier.bitget.client import (
    PENDING_ORDERS_PATH,
    BitgetAPIError,
    BitgetClient,
)


def _creds() -> BitgetCredentials:
    return BitgetCredentials(api_key="k", api_secret="s", passphrase="p")


@pytest.fixture
def sample_payload() -> dict:
    return {
        "code": "00000",
        "msg": "success",
        "data": {
            "entrustedList": [
                {
                    "orderId": "1001",
                    "clientOid": "cid-1",
                    "symbol": "BTCUSDT",
                    "side": "buy",
                    "orderType": "limit",
                    "size": "0.01",
                    "price": "60000",
                    "status": "live",
                    "leverage": "10",
                    "marginMode": "crossed",
                    "uTime": 1700000000000,
                }
            ]
        },
    }


@respx.mock
async def test_get_pending_futures_orders_parses_payload(sample_payload: dict) -> None:
    respx.get(f"https://api.bitget.com{PENDING_ORDERS_PATH}").mock(
        return_value=httpx.Response(200, json=sample_payload)
    )

    async with BitgetClient(_creds()) as client:
        orders = await client.get_pending_futures_orders()

    assert len(orders) == 1
    o = orders[0]
    assert o.order_id == "1001"
    assert o.symbol == "BTCUSDT"
    assert o.size == Decimal("0.01")
    assert o.price == Decimal("60000")
    assert o.status == "live"


@respx.mock
async def test_get_pending_futures_orders_returns_empty_on_no_data() -> None:
    respx.get(f"https://api.bitget.com{PENDING_ORDERS_PATH}").mock(
        return_value=httpx.Response(200, json={"code": "00000", "msg": "ok", "data": None})
    )

    async with BitgetClient(_creds()) as client:
        orders = await client.get_pending_futures_orders()

    assert orders == []


@respx.mock
async def test_non_zero_api_code_raises() -> None:
    respx.get(f"https://api.bitget.com{PENDING_ORDERS_PATH}").mock(
        return_value=httpx.Response(200, json={"code": "40001", "msg": "bad", "data": None})
    )

    async with BitgetClient(_creds()) as client:
        with pytest.raises(BitgetAPIError) as exc_info:
            await client.get_pending_futures_orders()

    assert exc_info.value.code == "40001"


@respx.mock
async def test_retries_on_5xx_then_succeeds(sample_payload: dict) -> None:
    route = respx.get(f"https://api.bitget.com{PENDING_ORDERS_PATH}")
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(200, json=sample_payload),
    ]

    async with BitgetClient(_creds(), max_retries=3) as client:
        orders = await client.get_pending_futures_orders()

    assert len(orders) == 1
    assert route.call_count == 2


@respx.mock
async def test_request_path_includes_query_string_for_signing() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["sign"] = request.headers.get("ACCESS-SIGN")
        captured["ts"] = request.headers.get("ACCESS-TIMESTAMP")
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"code": "00000", "msg": "ok", "data": {"entrustedList": []}})

    respx.get(f"https://api.bitget.com{PENDING_ORDERS_PATH}").mock(side_effect=handler)

    async with BitgetClient(_creds()) as client:
        await client.get_pending_futures_orders()

    assert "productType=USDT-FUTURES" in captured["url"]
    assert captured["sign"]
