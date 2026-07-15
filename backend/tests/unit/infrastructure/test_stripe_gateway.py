import hashlib
import hmac
import json
import time

import pytest

from src.infrastructure.payments.stripe_gateway import StripePaymentGateway

_WEBHOOK_SECRET = "whsec_test_secret_for_replay_fixtures"


def _sign(payload: bytes, secret: str = _WEBHOOK_SECRET, timestamp: int | None = None) -> str:
    """Reproduces Stripe's own signing scheme (see Stripe's webhook signing
    docs) locally — no network call, so this is a pure crypto/unit-level
    check even though it lives in the integration tier alongside the other
    webhook tests."""
    ts = timestamp if timestamp is not None else int(time.time())
    signed_payload = f"{ts}.{payload.decode()}"
    signature = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={signature}"


# A recorded (replayed) Stripe checkout.session.completed payload shape.
_CHECKOUT_COMPLETED_FIXTURE = {
    "id": "evt_1NxReplayFixture",
    "type": "checkout.session.completed",
    "data": {
        "object": {
            "id": "cs_test_replay",
            "customer": None,
            "metadata": {
                "tenant_id": "11111111-1111-1111-1111-111111111111",
                "order_id": "22222222-2222-2222-2222-222222222222",
                "kind": "order_payment",
            },
        }
    },
}


@pytest.fixture(autouse=True)
def _configure_webhook_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.core.config as config_module

    monkeypatch.setattr(config_module.settings, "stripe_webhook_secret", _WEBHOOK_SECRET)
    import src.infrastructure.payments.stripe_gateway as gateway_module

    monkeypatch.setattr(gateway_module.settings, "stripe_webhook_secret", _WEBHOOK_SECRET)


def test_valid_signature_over_replayed_fixture_is_accepted() -> None:
    payload = json.dumps(_CHECKOUT_COMPLETED_FIXTURE).encode()
    signature_header = _sign(payload)
    gateway = StripePaymentGateway()

    event = gateway.verify_webhook_signature(payload, signature_header)

    assert event.id == "evt_1NxReplayFixture"
    assert event.type == "checkout.session.completed"
    assert event.data["metadata"]["order_id"] == "22222222-2222-2222-2222-222222222222"


def test_signature_with_wrong_secret_is_rejected() -> None:
    payload = json.dumps(_CHECKOUT_COMPLETED_FIXTURE).encode()
    forged_signature = _sign(payload, secret="whsec_attacker_does_not_know_the_real_secret")
    gateway = StripePaymentGateway()

    with pytest.raises(ValueError):
        gateway.verify_webhook_signature(payload, forged_signature)


def test_signature_over_tampered_payload_is_rejected() -> None:
    original_payload = json.dumps(_CHECKOUT_COMPLETED_FIXTURE).encode()
    signature_header = _sign(original_payload)
    gateway = StripePaymentGateway()

    tampered = _CHECKOUT_COMPLETED_FIXTURE.copy()
    tampered["data"] = {
        "object": {**_CHECKOUT_COMPLETED_FIXTURE["data"]["object"], "id": "cs_attacker_substituted"}
    }
    tampered_payload = json.dumps(tampered).encode()

    with pytest.raises(ValueError):
        gateway.verify_webhook_signature(tampered_payload, signature_header)


def test_expired_timestamp_signature_still_parses_but_stripe_sdk_tolerance_applies() -> None:
    # Stripe's SDK enforces a default 5-minute tolerance window; a signature
    # from far in the past should be rejected.
    payload = json.dumps(_CHECKOUT_COMPLETED_FIXTURE).encode()
    old_timestamp = int(time.time()) - 60 * 60  # 1 hour ago
    signature_header = _sign(payload, timestamp=old_timestamp)
    gateway = StripePaymentGateway()

    with pytest.raises(ValueError):
        gateway.verify_webhook_signature(payload, signature_header)
