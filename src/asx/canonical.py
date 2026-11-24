"""Canonical binary encoding for ASX protocol version 1.

Textual fields are ASCII subsets. This module does not Unicode-normalize.
A value outside the grammar is rejected, so two encoders cannot fold
different byte strings into one accepted form.

Domain separators are the ASCII tag plus one NUL byte.
"""

from __future__ import annotations

import hashlib
import re

from asx.errors import Rejection

PROTOCOL_VERSION = 1

DOMAIN_SEMANTIC = b"ASX/semantic-proposal/v1\x00"
DOMAIN_PROPOSAL = b"ASX/proposal/v1\x00"
DOMAIN_CLOSED = b"ASX/closed-set/v1\x00"
DOMAIN_CHALLENGE = b"ASX/challenge/v1\x00"
DOMAIN_TIE = b"ASX/tie/v1\x00"
DOMAIN_POLICY = b"ASX/policy/v1\x00"
DOMAIN_DECISION = b"ASX/decision/v1\x00"
DOMAIN_ADMISSION = b"ASX/admission/v1\x00"
DOMAIN_SUBMIT = b"ASX/submit/v1\x00"
DOMAIN_REPLAY = b"ASX/replay/v1\x00"
DOMAIN_SUCCESSOR = b"ASX/successor/v1\x00"

MAX_ENTRIES = 1024
MAX_CONTENT = 1_048_576
MAX_EXTENSIONS = 16
MAX_EXTENSION_PAYLOAD = 4096
MAX_IDENTITY = 128
MAX_SEMANTIC_REF = 256
MAX_OPERATION = 128
MAX_FAIRNESS = 64

_IDENTITY = re.compile(rb"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_SEMANTIC_REF = re.compile(rb"[A-Za-z0-9][A-Za-z0-9._:@+/-]{0,255}")
_OPERATION = re.compile(rb"[A-Za-z0-9_-]{1,128}")
_FAIRNESS = re.compile(rb"max-wins:(0|[1-9][0-9]{0,6})")


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def u32be(value: int) -> bytes:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 0xFFFFFFFF:
        raise Rejection("malformed-transcript", "unsigned 32-bit integer is out of range")
    return value.to_bytes(4, "big")


def i64be(value: int) -> bytes:
    if isinstance(value, bool) or not isinstance(value, int) or value < -2**63 or value > 2**63 - 1:
        raise Rejection("malformed-transcript", "signed 64-bit integer is out of range")
    return value.to_bytes(8, "big", signed=True)


def lp(data: bytes) -> bytes:
    if not isinstance(data, bytes):
        raise Rejection("malformed-transcript", "length prefix requires bytes")
    return u32be(len(data)) + data


def read_exact(buf: bytes, index: int, size: int) -> tuple[bytes, int]:
    if size < 0 or index < 0 or index + size > len(buf):
        raise Rejection("malformed-transcript", "truncated field")
    return buf[index : index + size], index + size


def read_u32(buf: bytes, index: int) -> tuple[int, int]:
    raw, index = read_exact(buf, index, 4)
    return int.from_bytes(raw, "big"), index


def read_i64(buf: bytes, index: int) -> tuple[int, int]:
    raw, index = read_exact(buf, index, 8)
    return int.from_bytes(raw, "big", signed=True), index


def read_lp(buf: bytes, index: int, limit: int) -> tuple[bytes, int]:
    size, index = read_u32(buf, index)
    if size > limit:
        raise Rejection("malformed-transcript", "length exceeds the version-1 limit")
    return read_exact(buf, index, size)


def parse_hex(value: object, code: str = "malformed-transcript") -> bytes:
    if not isinstance(value, str) or len(value) % 2:
        raise Rejection(code, "expected even-length hex")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise Rejection(code, "expected hex") from exc


def parse_hex32(value: object, code: str = "malformed-transcript") -> bytes:
    raw = parse_hex(value, code)
    if len(raw) != 32:
        raise Rejection(code, "expected 32 bytes")
    return raw


def _ascii(value: object, pattern: re.Pattern[bytes], code: str, label: str) -> bytes:
    if isinstance(value, str):
        try:
            raw = value.encode("utf-8")
        except UnicodeError as exc:
            raise Rejection(code, f"{label} is not UTF-8") from exc
    elif isinstance(value, bytes):
        raw = value
    else:
        raise Rejection(code, f"{label} must be text or bytes")
    if pattern.fullmatch(raw) is None:
        raise Rejection(code, f"{label} is not canonical")
    return raw


def canonical_identity(value: object) -> bytes:
    return _ascii(value, _IDENTITY, "noncanonical-identity", "identity")


def canonical_round_id(value: object) -> bytes:
    return _ascii(value, _IDENTITY, "malformed-transcript", "round id")


def canonical_revision(value: object) -> bytes:
    return _ascii(value, _IDENTITY, "policy-invalid", "policy revision")


def canonical_semantic_ref(value: object) -> bytes:
    return _ascii(value, _SEMANTIC_REF, "noncanonical-proposal", "semantic reference")


def canonical_operation(value: object) -> bytes:
    return _ascii(value, _OPERATION, "noncanonical-proposal", "operation")


def canonical_content(value: object) -> bytes:
    if isinstance(value, str):
        value = parse_hex(value, "noncanonical-proposal")
    if not isinstance(value, bytes):
        raise Rejection("noncanonical-proposal", "content must be bytes")
    if len(value) > MAX_CONTENT:
        raise Rejection("malformed-transcript", "content exceeds the version-1 limit")
    return value


def canonical_fairness(value: object) -> bytes:
    if value is None:
        return b""
    if isinstance(value, str):
        try:
            raw = value.encode("utf-8")
        except UnicodeError as exc:
            raise Rejection("policy-invalid", "fairness text is not UTF-8") from exc
    elif isinstance(value, bytes):
        raw = value
    else:
        raise Rejection("policy-invalid", "fairness text is not canonical")
    if raw == b"":
        return b""
    if len(raw) > MAX_FAIRNESS or _FAIRNESS.fullmatch(raw) is None:
        raise Rejection("policy-invalid", "fairness directive is not canonical")
    return raw


def encode_semantic_proposal(
    semantic_ref: object,
    operation: object,
    content: object,
    successor: bytes,
) -> bytes:
    if not isinstance(successor, bytes) or len(successor) != 32:
        raise Rejection("noncanonical-proposal", "successor hash must be 32 bytes")
    return (
        DOMAIN_SEMANTIC
        + lp(canonical_semantic_ref(semantic_ref))
        + lp(canonical_operation(operation))
        + lp(canonical_content(content))
        + successor
    )


def proposal_commitment(semantic_bytes: bytes) -> bytes:
    if not isinstance(semantic_bytes, bytes) or not semantic_bytes.startswith(DOMAIN_SEMANTIC):
        raise Rejection("noncanonical-proposal", "semantic proposal is not version 1")
    return sha256(DOMAIN_PROPOSAL + lp(semantic_bytes))


def encode_entry(identity: bytes, commitment: bytes, priority: int) -> bytes:
    if len(commitment) != 32:
        raise Rejection("noncanonical-proposal", "proposal commitment must be 32 bytes")
    return lp(identity) + commitment + i64be(priority)


def encode_closed_set(entries: list[tuple[bytes, bytes, int]]) -> bytes:
    """Sort by identity bytes and encode the normative closed-set transcript."""
    if len(entries) > MAX_ENTRIES:
        raise Rejection("malformed-transcript", "too many eligible entries")
    ordered = sorted(entries, key=lambda item: item[0])
    seen: set[bytes] = set()
    body = bytearray()
    for identity, commitment, priority in ordered:
        if identity in seen:
            raise Rejection("duplicate-identity", "an identity appears more than once")
        seen.add(identity)
        body.extend(encode_entry(identity, commitment, priority))
    return DOMAIN_CLOSED + u32be(len(ordered)) + bytes(body)


def decode_closed_set(buf: bytes) -> list[tuple[bytes, bytes, int]]:
    """Decode a transcript. Structural faults beat identity grammar and duplicates."""
    if not isinstance(buf, bytes) or not buf.startswith(DOMAIN_CLOSED):
        raise Rejection("malformed-transcript", "closed-set domain is absent")
    index = len(DOMAIN_CLOSED)
    count, index = read_u32(buf, index)
    if count > MAX_ENTRIES:
        raise Rejection("malformed-transcript", "entry count exceeds the version-1 limit")
    parsed: list[tuple[bytes, bytes, int]] = []
    for _ in range(count):
        identity, index = read_lp(buf, index, MAX_IDENTITY)
        commitment, index = read_exact(buf, index, 32)
        priority, index = read_i64(buf, index)
        parsed.append((identity, commitment, priority))
    if index != len(buf):
        raise Rejection("malformed-transcript", "trailing bytes after the closed set")
    for identity, _, _ in parsed:
        if _IDENTITY.fullmatch(identity) is None:
            raise Rejection("noncanonical-identity", "identity is not canonical")
    identities = [identity for identity, _, _ in parsed]
    if len(set(identities)) != len(identities):
        raise Rejection("duplicate-identity", "an identity appears more than once")
    return parsed


def closed_set_digest(transcript: bytes) -> bytes:
    if not transcript.startswith(DOMAIN_CLOSED):
        raise Rejection("malformed-transcript", "closed-set domain is absent")
    return sha256(transcript)


def derived_challenge(
    round_id: bytes,
    parent_hash: bytes,
    policy_digest: bytes,
    closed_digest: bytes,
) -> bytes:
    if len(parent_hash) != 32 or len(policy_digest) != 32 or len(closed_digest) != 32:
        raise Rejection("malformed-transcript", "hash field is not 32 bytes")
    canonical_round_id(round_id)
    body = DOMAIN_CHALLENGE + lp(round_id) + parent_hash + policy_digest + closed_digest
    return sha256(body)


def tie_digest(challenge: bytes, commitment: bytes) -> bytes:
    if len(challenge) != 32 or len(commitment) != 32:
        raise Rejection("malformed-transcript", "tie input is not 32 bytes")
    return sha256(DOMAIN_TIE + challenge + commitment)


def encode_policy(revision: object, rules: list[tuple[bytes, int]], fairness: object) -> bytes:
    revision_bytes = canonical_revision(revision)
    fairness_bytes = canonical_fairness(fairness)
    if len(rules) > MAX_ENTRIES:
        raise Rejection("policy-invalid", "too many priority rules")
    ordered = sorted(rules, key=lambda item: item[0])
    seen: set[bytes] = set()
    body = bytearray()
    for operation, priority in ordered:
        operation = canonical_operation(operation)
        if operation in seen:
            raise Rejection("policy-invalid", "duplicate priority rule")
        seen.add(operation)
        body.extend(lp(operation) + i64be(priority))
    return DOMAIN_POLICY + lp(revision_bytes) + u32be(len(ordered)) + bytes(body) + lp(fairness_bytes)


def policy_digest(policy_bytes: bytes) -> bytes:
    if not isinstance(policy_bytes, bytes) or not policy_bytes.startswith(DOMAIN_POLICY):
        raise Rejection("policy-invalid", "policy encoding is not version 1")
    return sha256(policy_bytes)


def decode_policy(buf: bytes) -> tuple[bytes, list[tuple[bytes, int]], bytes]:
    if not isinstance(buf, bytes) or not buf.startswith(DOMAIN_POLICY):
        raise Rejection("policy-invalid", "policy domain is absent")
    index = len(DOMAIN_POLICY)
    try:
        revision, index = read_lp(buf, index, MAX_IDENTITY)
        count, index = read_u32(buf, index)
    except Rejection as exc:
        raise Rejection("policy-invalid", exc.message) from exc
    if count > MAX_ENTRIES:
        raise Rejection("policy-invalid", "too many priority rules")
    rules: list[tuple[bytes, int]] = []
    for _ in range(count):
        try:
            operation, index = read_lp(buf, index, MAX_OPERATION)
            priority, index = read_i64(buf, index)
        except Rejection as exc:
            raise Rejection("policy-invalid", exc.message) from exc
        rules.append((operation, priority))
    try:
        fairness, index = read_lp(buf, index, MAX_FAIRNESS)
    except Rejection as exc:
        raise Rejection("policy-invalid", exc.message) from exc
    if index != len(buf):
        raise Rejection("policy-invalid", "trailing policy bytes")
    if _IDENTITY.fullmatch(revision) is None:
        raise Rejection("policy-invalid", "policy revision is not canonical")
    previous = b""
    for operation, _ in rules:
        if _OPERATION.fullmatch(operation) is None:
            raise Rejection("policy-invalid", "operation is not canonical")
        if operation <= previous:
            raise Rejection("policy-invalid", "priority rules are not strictly sorted")
        previous = operation
    if fairness and _FAIRNESS.fullmatch(fairness) is None:
        raise Rejection("policy-invalid", "fairness directive is not canonical")
    return revision, rules, fairness


def encode_decision(fields: dict[str, bytes | int | list[tuple[bytes, bytes]]]) -> bytes:
    """Canonical decision bytes. The signature is not part of this encoding."""
    round_id = fields["round_id"]
    parent = fields["parent_hash"]
    policy = fields["policy_digest"]
    closed = fields["closed_set_digest"]
    challenge = fields["challenge"]
    winner = fields["winner_identity"]
    commitment = fields["winner_commitment"]
    priority = fields["winner_priority"]
    tie = fields["winner_tie"]
    rejections = fields["rejections"]
    if (
        not isinstance(round_id, bytes)
        or not isinstance(parent, bytes)
        or not isinstance(policy, bytes)
        or not isinstance(closed, bytes)
        or not isinstance(challenge, bytes)
        or not isinstance(winner, bytes)
        or not isinstance(commitment, bytes)
        or not isinstance(tie, bytes)
        or not isinstance(priority, int)
        or isinstance(priority, bool)
        or not isinstance(rejections, list)
    ):
        raise Rejection("malformed-certificate", "decision fields are incomplete")
    for item in (parent, policy, closed, challenge, commitment, tie):
        if len(item) != 32:
            raise Rejection("malformed-certificate", "decision hash is not 32 bytes")
    ordered = sorted(rejections, key=lambda item: item[0])
    body = bytearray()
    for identity, code in ordered:
        if not isinstance(identity, bytes) or not isinstance(code, bytes):
            raise Rejection("malformed-certificate", "rejection record is not bytes")
        body.extend(lp(identity) + lp(code))
    return (
        DOMAIN_DECISION
        + lp(round_id)
        + parent
        + policy
        + closed
        + challenge
        + lp(winner)
        + commitment
        + i64be(priority)
        + tie
        + u32be(len(ordered))
        + bytes(body)
    )


def decode_decision(buf: bytes) -> dict[str, object]:
    if not isinstance(buf, bytes) or not buf.startswith(DOMAIN_DECISION):
        raise Rejection("malformed-certificate", "decision domain is absent")
    index = len(DOMAIN_DECISION)
    try:
        round_id, index = read_lp(buf, index, MAX_IDENTITY)
        parent, index = read_exact(buf, index, 32)
        policy, index = read_exact(buf, index, 32)
        closed, index = read_exact(buf, index, 32)
        challenge, index = read_exact(buf, index, 32)
        winner, index = read_lp(buf, index, MAX_IDENTITY)
        commitment, index = read_exact(buf, index, 32)
        priority, index = read_i64(buf, index)
        tie, index = read_exact(buf, index, 32)
        count, index = read_u32(buf, index)
    except Rejection as exc:
        raise Rejection("malformed-certificate", exc.message) from exc
    if count > MAX_ENTRIES:
        raise Rejection("malformed-certificate", "too many rejections")
    rejections = []
    for _ in range(count):
        try:
            identity, index = read_lp(buf, index, MAX_IDENTITY)
            code, index = read_lp(buf, index, 64)
        except Rejection as exc:
            raise Rejection("malformed-certificate", exc.message) from exc
        rejections.append((identity, code))
    if index != len(buf):
        raise Rejection("malformed-certificate", "trailing decision bytes")
    return {
        "round_id": round_id,
        "parent_hash": parent,
        "policy_digest": policy,
        "closed_set_digest": closed,
        "challenge": challenge,
        "winner_identity": winner,
        "winner_commitment": commitment,
        "winner_priority": priority,
        "winner_tie": tie,
        "rejections": rejections,
    }


def encode_admission(
    round_id: bytes,
    identity: bytes,
    commitment: bytes,
    parent_hash: bytes,
    policy_digest: bytes,
    sequence: int,
) -> bytes:
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1 or sequence > 2**64 - 1:
        raise Rejection("malformed-transcript", "admission sequence is out of range")
    if len(commitment) != 32 or len(parent_hash) != 32 or len(policy_digest) != 32:
        raise Rejection("malformed-transcript", "admission hash is not 32 bytes")
    return (
        DOMAIN_ADMISSION
        + lp(round_id)
        + lp(identity)
        + commitment
        + parent_hash
        + policy_digest
        + sequence.to_bytes(8, "big")
    )


def submission_binding(
    round_id: bytes,
    identity: bytes,
    commitment: bytes,
    parent_hash: bytes,
    policy_digest: bytes,
) -> bytes:
    if len(commitment) != 32 or len(parent_hash) != 32 or len(policy_digest) != 32:
        raise Rejection("malformed-transcript", "submission hash is not 32 bytes")
    return DOMAIN_SUBMIT + lp(round_id) + lp(identity) + commitment + parent_hash + policy_digest


def replay_key(round_id: bytes, identity: bytes, commitment: bytes, parent_hash: bytes) -> bytes:
    if len(commitment) != 32 or len(parent_hash) != 32:
        raise Rejection("malformed-transcript", "replay hash is not 32 bytes")
    return sha256(DOMAIN_REPLAY + lp(round_id) + lp(identity) + commitment + parent_hash)


def successor_digest(predecessor: bytes, commitment: bytes) -> bytes:
    """Optional helper for a declared successor. Callers may supply their own 32 bytes."""
    if len(predecessor) != 32 or len(commitment) != 32:
        raise Rejection("noncanonical-proposal", "successor input is not 32 bytes")
    return sha256(DOMAIN_SUCCESSOR + predecessor + commitment)
