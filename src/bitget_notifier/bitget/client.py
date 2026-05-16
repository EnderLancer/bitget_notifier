from __future__ import annotations

import asyncio
from typing import Any

import httpx

from bitget_notifier.bitget.auth import BitgetCredentials, build_headers
from bitget_notifier.bitget.models import Order
from bitget_notifier.logging_setup import get_logger

log = get_logger(__name__)

PENDING_ORDERS_PATH = "/api/v2/mix/order/orders-pending"


class BitgetAPIError(RuntimeError):
    """Raised when Bitget returns a non-success code in the response body."""

    def __init__(self, code: str, message: str, request_path: str) -> None:
        super().__init__(f"Bitget API error code={code} msg={message!r} path={request_path}")
        self.code = code
        self.message = message
        self.request_path = request_path


class BitgetClient:
    """Async Bitget v2 REST client. Scoped to the endpoints we currently need."""

    def __init__(
        self,
        credentials: BitgetCredentials,
        base_url: str = "https://api.bitget.com",
        *,
        timeout: float = 10.0,
        max_retries: int = 3,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._credentials = credentials
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
        )

    async def __aenter__(self) -> BitgetClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def get_pending_futures_orders(self, product_type: str = "USDT-FUTURES") -> list[Order]:
        params = {"productType": product_type}
        payload = await self._signed_get(PENDING_ORDERS_PATH, params=params)
        raw_orders = _extract_order_list(payload)
        return [Order.model_validate(item) for item in raw_orders]

    async def _signed_get(self, path: str, *, params: dict[str, str]) -> dict[str, Any]:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        request_path = f"{path}?{query}" if query else path

        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            headers = build_headers(self._credentials, "GET", request_path, body="")
            try:
                response = await self._http.get(path, params=params, headers=headers)
            except httpx.HTTPError as exc:
                last_exc = exc
                log.warning("bitget_request_error", attempt=attempt + 1, error=str(exc))
                await asyncio.sleep(2**attempt)
                continue

            if response.status_code >= 500:
                last_exc = httpx.HTTPStatusError(
                    f"{response.status_code}", request=response.request, response=response
                )
                log.warning(
                    "bitget_http_5xx", attempt=attempt + 1, status=response.status_code
                )
                await asyncio.sleep(2**attempt)
                continue

            response.raise_for_status()
            body = response.json()
            code = str(body.get("code", ""))
            if code != "00000":
                raise BitgetAPIError(
                    code=code, message=str(body.get("msg", "")), request_path=request_path
                )
            return body

        assert last_exc is not None
        raise last_exc


def _extract_order_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") or {}
    if isinstance(data, list):
        return data
    entrusted = data.get("entrustedList")
    if entrusted is None:
        return []
    return list(entrusted)
