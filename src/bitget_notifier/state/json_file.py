from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path

from bitget_notifier.bitget.models import Order


class JsonFileStore:
    """File-backed order snapshot. Atomic writes via tmp + rename."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    async def load(self) -> list[Order] | None:
        return await asyncio.to_thread(self._load_sync)

    async def save(self, orders: list[Order]) -> None:
        await asyncio.to_thread(self._save_sync, orders)

    def _load_sync(self) -> list[Order] | None:
        if not self._path.exists():
            return None
        with self._path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        return [Order.model_validate(item) for item in raw]

    def _save_sync(self, orders: list[Order]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        serialised = [o.model_dump(mode="json", by_alias=True) for o in orders]

        fd, tmp_path = tempfile.mkstemp(
            prefix=self._path.name + ".",
            suffix=".tmp",
            dir=self._path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(serialised, fh, indent=2, sort_keys=True)
            os.replace(tmp_path, self._path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
