"""Signed decision records.

The byte layout is normative. The HMAC helper is illustrative and is not
a claim that HMAC is the production signature algorithm.
"""

from __future__ import annotations

from asx.canonical import decode_decision, encode_decision
from asx.errors import Rejection
from asx.identity import IllustrativeHmacKey


def decision_bytes(fields: dict) -> bytes:
    return encode_decision(fields)


def sign_decision(fields: dict, key: IllustrativeHmacKey) -> dict[str, object]:
    payload = encode_decision(fields)
    return {
        "algorithm": "illustrative-hmac-sha256",
        "payload": payload,
        "signature": key.sign(payload),
    }


def verify_decision(payload: bytes, signature: bytes, key: IllustrativeHmacKey) -> dict[str, object]:
    if not key.verify(payload, signature):
        raise Rejection("certificate-mismatch", "decision signature did not verify")
    decoded = decode_decision(payload)
    return decoded
