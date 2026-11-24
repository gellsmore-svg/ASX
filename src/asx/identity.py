"""Governed identity proofs.

`IllustrativeHmacKey` is a test authenticator. It is not a production
signature scheme, and a self-asserted identity string is not a proof.
"""

from __future__ import annotations

import hashlib
import hmac

from asx.canonical import canonical_identity
from asx.errors import Rejection


class IllustrativeHmacKey:
    """HMAC-SHA256 with a caller-supplied secret. Single-process test tool."""

    def __init__(self, secret: bytes):
        if not isinstance(secret, bytes) or len(secret) < 16:
            raise ValueError("illustrative HMAC secret must be at least 16 bytes")
        self._secret = secret

    def sign(self, payload: bytes) -> bytes:
        if not isinstance(payload, bytes):
            raise Rejection("malformed-transcript", "signed payload must be bytes")
        return hmac.new(self._secret, payload, hashlib.sha256).digest()

    def verify(self, payload: bytes, proof: bytes) -> bool:
        if not isinstance(payload, bytes) or not isinstance(proof, bytes) or len(proof) != 32:
            return False
        return hmac.compare_digest(self.sign(payload), proof)


class IllustrativeAgentKeys:
    """Map of governed identity to an illustrative HMAC key."""

    def __init__(self, secrets: dict[bytes, bytes]):
        self._keys = {
            canonical_identity(identity): IllustrativeHmacKey(secret)
            for identity, secret in secrets.items()
        }

    def sign(self, identity: object, payload: bytes) -> bytes:
        key = self._keys.get(canonical_identity(identity))
        if key is None:
            raise Rejection("admission-unauthenticated", "identity has no registered key")
        return key.sign(payload)

    def verify(self, identity: object, payload: bytes, proof: bytes) -> bool:
        try:
            raw = canonical_identity(identity)
        except Rejection:
            return False
        key = self._keys.get(raw)
        if key is None:
            return False
        return key.verify(payload, proof)
