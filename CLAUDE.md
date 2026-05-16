# CLAUDE.md

Bitget USDT-M futures order poller → Telegram notifier. Python 3.11+, async, uv-managed.

## Commands

```bash
uv sync                          # install deps (includes dev group)
uv run pytest -q                 # 15 unit tests, respx-mocked HTTP
uv run ruff check .              # lint (rules in pyproject.toml)
uv run python -m bitget_notifier # start the poll loop (needs .env)
docker compose build && docker compose up
```

## Architecture

```
__main__ → app.PollLoop ──► BitgetClient ──► Bitget v2 REST
                         ├─► diff_orders(prev, curr)
                         ├─► TelegramNotifier ──► api.telegram.org
                         └─► JsonFileStore (./data/state.json)
```

Every collaborator is injected. `Notifier` and `OrderStateStore` are `Protocol`s — swap implementations without touching the loop.

## File map

- `src/bitget_notifier/app.py` — `PollLoop` (try/except around each poll so it never crashes), `run_from_settings`, signal handlers.
- `src/bitget_notifier/__main__.py` — entrypoint; wires config + logging then `asyncio.run`.
- `src/bitget_notifier/config.py` — `pydantic-settings`, `.env` auto-loaded. Add new env vars here.
- `src/bitget_notifier/bitget/auth.py` — `sign()` = base64(HMAC-SHA256(secret, ts+method+requestPath+body)). `requestPath` MUST include `?query`.
- `src/bitget_notifier/bitget/client.py` — `BitgetClient.get_pending_futures_orders()`, retries 3× on 5xx/network with backoff 1s/2s/4s, raises `BitgetAPIError` when `code != "00000"`.
- `src/bitget_notifier/bitget/models.py` — `Order` (pydantic, aliases match Bitget JSON). `fingerprint()` = `(status, size, price)`, the modify-detection key.
- `src/bitget_notifier/differ.py` — pure `diff_orders(prev, curr)`. **`prev is None` ⇒ returns `[]`** (first run is silent on purpose; don't change without a reason).
- `src/bitget_notifier/state/json_file.py` — atomic write via tmp + `os.replace`.
- `src/bitget_notifier/state/redis.py` — stub for multi-tenant scale-up (raises `NotImplementedError`).
- `src/bitget_notifier/telegram/notifier.py` — direct `sendMessage` calls, HTML parse mode, splits on line boundaries at the 4096-char limit.
- `src/bitget_notifier/formatter.py` — HTML message rendering; escape all dynamic values.

## Conventions / gotchas

- **Secrets are `SecretStr`** in `Settings`; call `.get_secret_value()` only at the boundary where you build the credential/token.
- **Don't log secrets.** Logger is `structlog`; structured fields go via `log.info("event", k=v)` — never f-string a token into the event name.
- **Bitget signing**: any new endpoint must build `requestPath` as `path + "?" + query` BEFORE signing. Use `BitgetClient._signed_get` rather than calling `httpx` directly.
- **Decimals everywhere** for `size` and `price` — never floats. The differ relies on `Decimal` equality.
- **First-run silence** is a feature: if you add new change kinds, keep the `prev is None → []` short-circuit.
- **Loop must not raise**: anything thrown inside `_poll_once` is caught and logged. Don't move work above the `try`.
- **Adding a new env var**: add it to `config.Settings`, `.env.example`, and the README config table.
- **Scaling seams**: `Notifier` and `OrderStateStore` are the only abstractions worth keeping. Don't add more until a second concrete impl actually exists.

## Test patterns

- `respx` mocks httpx at the transport layer — see `tests/test_client.py` for the canonical pattern, including how to assert the signed URL contains the query string.
- Async tests run under `asyncio_mode = "auto"` (no `@pytest.mark.asyncio` needed).
- The differ is pure — test it with plain `Order.model_validate({...})` fixtures, no mocks.

## Branch / push

- Default working branch for Claude sessions: `claude/<task-slug>` off `main`.
- Never force-push, never skip hooks.
