from __future__ import annotations

import base64
import hmac
import time
from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class BitgetCredentials:
    api_key: str
    api_secret: str
    passphrase: str


def now_ms() -> str:
    return str(int(time.time() * 1000))


def sign(secret: str, timestamp: str, method: str, request_path: str, body: str = "") -> str:
    """Build the Bitget v2 ACCESS-SIGN header value.

    sign = base64( HMAC_SHA256(secret, timestamp + method + requestPath + body) )

    `request_path` MUST include the query string (e.g. "/api/v2/...?foo=bar").
    `body` MUST be the raw request body string, "" for GET.
    """
    payload = f"{timestamp}{method.upper()}{request_path}{body}".encode()
    digest = hmac.new(secret.encode(), payload, sha256).digest()
    return base64.b64encode(digest).decode()


def build_headers(
    creds: BitgetCredentials,
    method: str,
    request_path: str,
    body: str = "",
    timestamp: str | None = None,
) -> dict[str, str]:
    ts = timestamp or now_ms()
    return {
        "ACCESS-KEY": creds.api_key,
        "ACCESS-SIGN": sign(creds.api_secret, ts, method, request_path, body),
        "ACCESS-TIMESTAMP": ts,
        "ACCESS-PASSPHRASE": creds.passphrase,
        "Content-Type": "application/json",
        "locale": "en-US",
    }
