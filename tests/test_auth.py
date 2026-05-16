from __future__ import annotations

import base64
import hmac
from hashlib import sha256

from bitget_notifier.bitget.auth import BitgetCredentials, build_headers, sign


def test_sign_matches_manual_hmac() -> None:
    secret = "topsecret"
    timestamp = "1700000000000"
    method = "GET"
    request_path = "/api/v2/mix/order/orders-pending?productType=USDT-FUTURES"

    expected = base64.b64encode(
        hmac.new(
            secret.encode(),
            f"{timestamp}{method}{request_path}".encode(),
            sha256,
        ).digest()
    ).decode()

    assert sign(secret, timestamp, method, request_path) == expected


def test_sign_includes_body_for_non_get() -> None:
    body = '{"foo":"bar"}'
    sig_with_body = sign("s", "1", "POST", "/x", body)
    sig_without_body = sign("s", "1", "POST", "/x", "")
    assert sig_with_body != sig_without_body


def test_build_headers_contains_required_fields() -> None:
    creds = BitgetCredentials(api_key="k", api_secret="s", passphrase="p")
    headers = build_headers(creds, "GET", "/x", timestamp="123")
    assert headers["ACCESS-KEY"] == "k"
    assert headers["ACCESS-PASSPHRASE"] == "p"
    assert headers["ACCESS-TIMESTAMP"] == "123"
    assert headers["Content-Type"] == "application/json"
    assert headers["locale"] == "en-US"
    assert headers["ACCESS-SIGN"] == sign("s", "123", "GET", "/x", "")
