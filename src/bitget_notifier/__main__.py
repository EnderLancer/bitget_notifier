from __future__ import annotations

import asyncio

from bitget_notifier.app import run_from_settings
from bitget_notifier.config import load_settings
from bitget_notifier.logging_setup import configure_logging, get_logger


def main() -> None:
    settings = load_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)
    log = get_logger(__name__)
    log.info(
        "starting",
        product=settings.bitget_product_type,
        interval=settings.poll_interval_seconds,
        backend=settings.state_backend,
    )
    asyncio.run(run_from_settings(settings))


if __name__ == "__main__":
    main()
