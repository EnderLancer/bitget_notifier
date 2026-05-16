from __future__ import annotations

import asyncio
from typing import Protocol, runtime_checkable

import httpx

from bitget_notifier.logging_setup import get_logger

log = get_logger(__name__)

TELEGRAM_MESSAGE_LIMIT = 4096


@runtime_checkable
class Notifier(Protocol):
    async def send(self, text: str) -> None: ...


class TelegramNotifier:
    """Minimal Telegram Bot API wrapper around ``sendMessage``.

    Direct httpx calls keep dependencies light. The interface is narrow on
    purpose — if a richer client is needed later (commands, inline keyboards,
    multiple chats) the Notifier protocol can be re-implemented over
    ``python-telegram-bot`` without touching the poll loop.
    """

    BASE_URL = "https://api.telegram.org"

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        *,
        timeout: float = 10.0,
        max_retries: int = 3,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token = bot_token
        self._chat_id = chat_id
        self._max_retries = max_retries
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=timeout,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def send(self, text: str) -> None:
        for chunk in _split_for_telegram(text):
            await self._send_one(chunk)

    async def _send_one(self, text: str) -> None:
        url = f"/bot{self._token}/sendMessage"
        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                response = await self._http.post(url, json=payload)
            except httpx.HTTPError as exc:
                last_exc = exc
                log.warning("telegram_request_error", attempt=attempt + 1, error=str(exc))
                await asyncio.sleep(2**attempt)
                continue

            if response.status_code == 429 or response.status_code >= 500:
                last_exc = httpx.HTTPStatusError(
                    f"{response.status_code}", request=response.request, response=response
                )
                log.warning(
                    "telegram_http_retry", attempt=attempt + 1, status=response.status_code
                )
                await asyncio.sleep(2**attempt)
                continue

            response.raise_for_status()
            return

        assert last_exc is not None
        raise last_exc


def _split_for_telegram(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Split a message at line boundaries so each chunk fits Telegram's limit."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for line in text.splitlines(keepends=True):
        if size + len(line) > limit and buf:
            chunks.append("".join(buf))
            buf, size = [], 0
        if len(line) > limit:
            # single huge line — hard-split
            if buf:
                chunks.append("".join(buf))
                buf, size = [], 0
            for i in range(0, len(line), limit):
                chunks.append(line[i : i + limit])
            continue
        buf.append(line)
        size += len(line)
    if buf:
        chunks.append("".join(buf))
    return chunks
