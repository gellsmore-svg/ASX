"""Normative rejection codes.

Check order is the precedence. A failed earlier check is the result that
implementations report; they do not continue and pick a later code.
"""

from __future__ import annotations

# Halting codes, earliest first. Outcome codes are not in this tuple:
# they describe a successful decision's losers or an idempotent replay.
PRECEDENCE: tuple[str, ...] = (
    "unsupported-version",
    "malformed-transcript",
    "malformed-certificate",
    "noncanonical-identity",
    "noncanonical-proposal",
    "duplicate-identity",
    "commitment-collision",
    "commitment-mismatch",
    "ineligible-operation",
    "priority-untrusted",
    "policy-invalid",
    "policy-stale",
    "fairness-violation",
    "closed-set-mismatch",
    "extension-invalid",
    "extension-critical-unknown",
    "admission-unauthenticated",
    "duplicate-submission",
    "admission-closed",
    "sequencer-unavailable",
    "arbiter-unavailable",
    "empty-closed-set",
    "tie-collision",
    "certificate-mismatch",
    "unauthorized",
    "stale-parent",
    "commit-rejected",
)

OUTCOME_CODES: tuple[str, ...] = (
    "lower-priority",
    "higher-tie-digest",
    "replay-receipt",
    "committed",
)

CODES = frozenset(PRECEDENCE) | frozenset(OUTCOME_CODES)


class Rejection(Exception):
    """A normative, externally observable refusal. State must not change."""

    def __init__(self, code: str, message: str):
        if code not in PRECEDENCE:
            raise ValueError(f"unknown halting rejection code {code}")
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def precedence_first(codes: list[str]) -> str:
    """Return the earliest code. Used when several faults are already known."""
    if not codes:
        raise ValueError("no rejection codes")
    return min(codes, key=PRECEDENCE.index)
