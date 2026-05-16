# bitget_notifier

Polls **Bitget USDT-M futures open orders** once a minute via the v2 REST API
and sends a **Telegram bot** message whenever the list of open orders changes
(new order, cancel, fill, modification).

Designed single-user / single-account today, but every dependency is wired
behind an interface (state store, notifier, HTTP client) so it scales out to
multi-account, multi-tenant, container-based deployments without a rewrite.

## Quick start

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env
# fill in BITGET_* and TELEGRAM_* values in .env

uv run python -m bitget_notifier
```

On the first poll the current open-order list is just snapshotted — no
Telegram message is sent. Subsequent polls emit one message per change.

## Configuration

All settings come from environment variables (12-factor); a local `.env` is
loaded automatically.

| Variable | Default | Notes |
|---|---|---|
| `BITGET_API_KEY` | _required_ | Read-only API key is sufficient |
| `BITGET_API_SECRET` | _required_ | |
| `BITGET_API_PASSPHRASE` | _required_ | The passphrase set when creating the key |
| `BITGET_PRODUCT_TYPE` | `USDT-FUTURES` | Also accepts `COIN-FUTURES`, `USDC-FUTURES` |
| `BITGET_BASE_URL` | `https://api.bitget.com` | |
| `TELEGRAM_BOT_TOKEN` | _required_ | From @BotFather |
| `TELEGRAM_CHAT_ID` | _required_ | Your user/chat id (talk to @userinfobot) |
| `POLL_INTERVAL_SECONDS` | `60` | Minimum 5 |
| `STATE_BACKEND` | `json` | `redis` is reserved for the scale-up |
| `STATE_FILE_PATH` | `./data/state.json` | Atomic file writes |
| `LOG_LEVEL` | `INFO` | |
| `LOG_FORMAT` | `console` | `json` for prod |

## Tests & lint

```bash
uv run pytest -q
uv run ruff check .
```

The differ, the request signer, and the HTTP client are covered by unit
tests (the last via `respx` so no real Bitget calls are made).

## Docker

```bash
docker compose build
docker compose up
```

`./data` is mounted into the container so the state snapshot survives
restarts.

## Architecture

```
__main__.py ──► PollLoop ──► BitgetClient ──► api.bitget.com
                  │
                  ├─► diff_orders(prev, curr)
                  │
                  ├─► TelegramNotifier ──► api.telegram.org
                  │
                  └─► JsonFileStore (./data/state.json)
```

Every collaborator is either a Protocol (`Notifier`, `OrderStateStore`) or
takes its dependencies via constructor injection — so the scale-up paths
below land as drop-in replacements.

## Scaling beyond single-user

The seams are already in place:

1. **Multi-account** — construct one `BitgetClient` per credential set; share
   one `Notifier`.
2. **Multi-tenant** — flip `STATE_BACKEND=redis`, implement `RedisStore`
   (stub already present), key snapshots by `user_id`.
3. **Horizontal workers** — the loop is stateless apart from the store;
   shard accounts across replicas by hash.
4. **WebSocket instead of polling** — Bitget's private order channel can
   replace `BitgetClient.get_pending_futures_orders()` behind the same
   interface; the differ, store, and notifier stay unchanged.
5. **Container-ready** — the provided `Dockerfile` is a multi-stage build
   running as a non-root user, ready for k8s.
