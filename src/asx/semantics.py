"""Authoritative semantic references.

Equality is equality of the canonical reference bytes. It establishes that
both sides named the same published reference. It does not establish that
two models interpreted that reference the same way.
"""

from __future__ import annotations

from asx.canonical import canonical_semantic_ref
from asx.errors import Rejection


def semantic_reference(authority: str, identifier: str, frame: str, revision: str) -> bytes:
    """Build `authority:identifier@frame+revision` and reject anything else."""
    for label, value in (
        ("authority", authority),
        ("identifier", identifier),
        ("frame", frame),
        ("revision", revision),
    ):
        if not isinstance(value, str) or not value.isascii():
            raise Rejection("noncanonical-proposal", f"semantic {label} is not canonical")
    token = f"{authority}:{identifier}@{frame}+{revision}"
    return canonical_semantic_ref(token)


def references_match(left: object, right: object) -> bool:
    return canonical_semantic_ref(left) == canonical_semantic_ref(right)
