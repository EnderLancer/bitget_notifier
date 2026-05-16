from __future__ import annotations

import asyncio
import random
import signal
from contextlib import suppress

from bitget_notifier.bitget import BitgetClient
from bitget_notifier.bitget.auth import BitgetCredentials
from bitget_notifier.config import Settings
from bitget_notifier.differ import diff_orders
from bitget_notifier.formatter import format_changes
from bitget_notifier.logging_setup import get_logger
from bitget_notifier.state import JsonFileStore, OrderStateStore
from bitget_notifier.telegram import Notifier, TelegramNotifier

log = get_logger(__name__)


class PollLoop:
    def __init__(
        self,
        client: BitgetClient,
        notifier: Notifier,
        store: OrderStateStore,
        *,
        product_type: str,
        interval_seconds: int,
    ) -> None:
        self._client = client
        self._notifier = notifier
        self._store = store
        self._product_type = product_type
        self._interval = interval_seconds
        self._stop = asyncio.Event()

    def request_stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        log.info("poll_loop_started", interval=self._interval, product=self._product_type)
        while not self._stop.is_set():
            await self._poll_once()
            await self._sleep_or_stop()
        log.info("poll_loop_stopped")

    async def _poll_once(self) -> None:
        try:
            curr = await self._client.get_pending_futures_orders(self._product_type)
            prev = await self._store.load()
            changes = diff_orders(prev, curr)
            if changes:
                message = format_changes(changes)
                await self._notifier.send(message)
                log.info("changes_notified", count=len(changes))
            await self._store.save(curr)
            log.info("poll_ok", orders=len(curr), changes=len(changes))
        except Exception:
            log.exception("poll_failed")

    async def _sleep_or_stop(self) -> None:
        jitter = random.uniform(0, min(2.0, self._interval * 0.05))
        with suppress(TimeoutError):
            await asyncio.wait_for(self._stop.wait(), timeout=self._interval + jitter)


async def run_from_settings(settings: Settings) -> None:
    if settings.state_backend != "json":
        raise NotImplementedError(
            f"state_backend={settings.state_backend!r} not implemented yet; use 'json'."
        )

    credentials = BitgetCredentials(
        api_key=settings.bitget_api_key.get_secret_value(),
        api_secret=settings.bitget_api_secret.get_secret_value(),
        passphrase=settings.bitget_api_passphrase.get_secret_value(),
    )
    client = BitgetClient(credentials, base_url=settings.bitget_base_url)
    notifier = TelegramNotifier(
        bot_token=settings.telegram_bot_token.get_secret_value(),
        chat_id=settings.telegram_chat_id,
    )
    store = JsonFileStore(settings.state_file_path)

    loop = PollLoop(
        client=client,
        notifier=notifier,
        store=store,
        product_type=settings.bitget_product_type,
        interval_seconds=settings.poll_interval_seconds,
    )

    _install_signal_handlers(loop)

    try:
        await loop.run()
    finally:
        await client.aclose()
        await notifier.aclose()


def _install_signal_handlers(loop: PollLoop) -> None:
    running_loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):  # not supported on Windows
            running_loop.add_signal_handler(sig, loop.request_stop)
