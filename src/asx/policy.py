"""Pinned priority policy.

Priority is a function of the policy bytes and the operation. A proposer
does not get to declare it. An empty fairness directive means no extra
schedule. An unrecognised directive is invalid: it is not ignored.
"""

from __future__ import annotations

from asx.canonical import canonical_operation, decode_policy, encode_policy, policy_digest
from asx.errors import Rejection


def build_policy(revision: object, rules: list[dict[str, object]], fairness: object = "") -> bytes:
    encoded_rules: list[tuple[bytes, int]] = []
    for rule in rules:
        if not isinstance(rule, dict) or "operation" not in rule or "priority" not in rule:
            raise Rejection("policy-invalid", "priority rule is incomplete")
        priority = rule["priority"]
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise Rejection("policy-invalid", "priority is not an integer")
        try:
            operation = canonical_operation(rule["operation"])
        except Rejection as exc:
            raise Rejection("policy-invalid", exc.message) from exc
        encoded_rules.append((operation, priority))
    return encode_policy(revision, encoded_rules, fairness)


def priority_for(policy_bytes: bytes, operation: bytes) -> int:
    _revision, rules, _fairness = decode_policy(policy_bytes)
    matches = [priority for name, priority in rules if name == operation]
    if not matches:
        raise Rejection("ineligible-operation", "operation has no pinned priority")
    if len(matches) != 1:
        raise Rejection("policy-invalid", "duplicate priority rule")
    return matches[0]


def fairness_limit(policy_bytes: bytes) -> int | None:
    """Return the max-wins cap, or None when the policy declares no schedule."""
    _revision, _rules, fairness = decode_policy(policy_bytes)
    if not fairness:
        return None
    return int(fairness.split(b":", 1)[1])


def digest_of(policy_bytes: bytes) -> bytes:
    return policy_digest(policy_bytes)
