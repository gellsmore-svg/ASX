"""Second in-repository computation of the version-1 arbitration bytes.

This file must not import the ``asx`` package. It exists so the reference
library can be checked against a separate encoding of the rules in
``docs/arbitration.md``. It was written in the same repository session as
the reference and is not an externally developed implementation.

The derived challenge is reproducible. It is not grinding resistance.
"""

from __future__ import annotations

import hashlib
import re

PROTOCOL_VERSION = 1
MAX_ENTRIES = 1024
MAX_CONTENT = 1_048_576
MAX_EXTENSIONS = 16
MAX_EXTENSION_PAYLOAD = 4096

DOMAIN_SEMANTIC = b"ASX/semantic-proposal/v1\x00"
DOMAIN_PROPOSAL = b"ASX/proposal/v1\x00"
DOMAIN_CLOSED = b"ASX/closed-set/v1\x00"
DOMAIN_CHALLENGE = b"ASX/challenge/v1\x00"
DOMAIN_TIE = b"ASX/tie/v1\x00"
DOMAIN_POLICY = b"ASX/policy/v1\x00"

_IDENTITY = re.compile(rb"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_REF = re.compile(rb"[A-Za-z0-9][A-Za-z0-9._:@+/-]{0,255}")
_OP = re.compile(rb"[A-Za-z0-9_-]{1,128}")
_FAIRNESS = re.compile(rb"max-wins:(0|[1-9][0-9]{0,6})")
_EXT_ID = re.compile(r"[a-z][a-z0-9.-]{0,127}")
_MAHALATH = re.compile(rb"mpl:[A-Za-z0-9][A-Za-z0-9._-]{0,63}@[A-Za-z0-9._-]{1,64}#[0-9a-f]{64}")
_KETURAH = re.compile(rb"product:[A-Za-z0-9_-]{1,64} capability:[A-Za-z0-9_-]{1,128}")
_DEBORAH = re.compile(rb"process:[A-Za-z][A-Za-z0-9_-]{0,127}")
_MILCAH = re.compile(
    rb"mode:(coherence|research) terminal:"
    rb"(converged|max_iterations|no_objections|insufficient_evidence|blocked) "
    rb"ref:[0-9a-f]{64}"
)
_HANDLERS = {
    "org.gellsmore.mahalath.semantic-ref": _MAHALATH,
    "org.gellsmore.keturah.capability": _KETURAH,
    "org.gellsmore.deborah.process-ref": _DEBORAH,
    "org.gellsmore.milcah.coherence": _MILCAH,
}
_PROFILES = {name: 1 for name in _HANDLERS}


class Halt(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _sha(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _u32(value: int) -> bytes:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 0xFFFFFFFF:
        raise Halt("malformed-transcript", "bad u32")
    return value.to_bytes(4, "big")


def _i64(value: int) -> bytes:
    if isinstance(value, bool) or not isinstance(value, int) or value < -2**63 or value > 2**63 - 1:
        raise Halt("malformed-transcript", "bad i64")
    return value.to_bytes(8, "big", signed=True)


def _lp(data: bytes) -> bytes:
    return _u32(len(data)) + data


def _take(buf: bytes, index: int, size: int) -> tuple[bytes, int]:
    if size < 0 or index < 0 or index + size > len(buf):
        raise Halt("malformed-transcript", "truncated")
    return buf[index : index + size], index + size


def _take_u32(buf: bytes, index: int) -> tuple[int, int]:
    raw, index = _take(buf, index, 4)
    return int.from_bytes(raw, "big"), index


def _take_i64(buf: bytes, index: int) -> tuple[int, int]:
    raw, index = _take(buf, index, 8)
    return int.from_bytes(raw, "big", signed=True), index


def _take_lp(buf: bytes, index: int, limit: int) -> tuple[bytes, int]:
    size, index = _take_u32(buf, index)
    if size > limit:
        raise Halt("malformed-transcript", "over limit")
    return _take(buf, index, size)


def _hex(value: object, code: str) -> bytes:
    if not isinstance(value, str) or len(value) % 2:
        raise Halt(code, "bad hex")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise Halt(code, "bad hex") from exc


def _hex32(value: object, code: str) -> bytes:
    raw = _hex(value, code)
    if len(raw) != 32:
        raise Halt(code, "not 32 bytes")
    return raw


def _token(value: object, pattern: re.Pattern[bytes], code: str) -> bytes:
    if isinstance(value, str):
        raw = value.encode("utf-8")
    elif isinstance(value, bytes):
        raw = value
    else:
        raise Halt(code, "not text")
    if pattern.fullmatch(raw) is None:
        raise Halt(code, "not canonical")
    return raw


def _content(entry: dict) -> bytes:
    if "content_hex" in entry:
        raw = _hex(entry["content_hex"], "noncanonical-proposal")
    elif isinstance(entry.get("content"), bytes):
        raw = entry["content"]
    else:
        raise Halt("noncanonical-proposal", "content missing")
    if len(raw) > MAX_CONTENT:
        raise Halt("malformed-transcript", "content too large")
    return raw


def encode_semantic(ref: object, operation: object, content: bytes, successor: bytes) -> bytes:
    if len(successor) != 32:
        raise Halt("noncanonical-proposal", "bad successor")
    return (
        DOMAIN_SEMANTIC
        + _lp(_token(ref, _REF, "noncanonical-proposal"))
        + _lp(_token(operation, _OP, "noncanonical-proposal"))
        + _lp(content)
        + successor
    )


def commitment_of(semantic: bytes) -> bytes:
    if not semantic.startswith(DOMAIN_SEMANTIC):
        raise Halt("noncanonical-proposal", "bad semantic")
    return _sha(DOMAIN_PROPOSAL + _lp(semantic))


def operation_of(semantic: bytes) -> bytes:
    index = len(DOMAIN_SEMANTIC)
    _ref, index = _take_lp(semantic, index, 256)
    operation, _index = _take_lp(semantic, index, 128)
    return operation


def encode_policy(revision: object, rules: list[dict], fairness: object) -> bytes:
    rev = _token(revision, _IDENTITY, "policy-invalid")
    if isinstance(fairness, str):
        fair = fairness.encode("utf-8")
    elif isinstance(fairness, bytes):
        fair = fairness
    elif fairness is None:
        fair = b""
    else:
        raise Halt("policy-invalid", "bad fairness")
    if fair and (len(fair) > 64 or _FAIRNESS.fullmatch(fair) is None):
        raise Halt("policy-invalid", "bad fairness")
    encoded = []
    for rule in rules:
        if not isinstance(rule, dict):
            raise Halt("policy-invalid", "bad rule")
        priority = rule.get("priority")
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise Halt("policy-invalid", "bad priority")
        try:
            operation = _token(rule.get("operation"), _OP, "policy-invalid")
        except Halt as exc:
            raise Halt("policy-invalid", exc.message) from exc
        encoded.append((operation, priority))
    encoded.sort(key=lambda item: item[0])
    seen: set[bytes] = set()
    body = bytearray()
    for operation, priority in encoded:
        if operation in seen:
            raise Halt("policy-invalid", "duplicate rule")
        seen.add(operation)
        body.extend(_lp(operation) + _i64(priority))
    return DOMAIN_POLICY + _lp(rev) + _u32(len(encoded)) + bytes(body) + _lp(fair)


def encode_closed(entries: list[tuple[bytes, bytes, int]]) -> bytes:
    if len(entries) > MAX_ENTRIES:
        raise Halt("malformed-transcript", "too many")
    ordered = sorted(entries, key=lambda item: item[0])
    if len({item[0] for item in ordered}) != len(ordered):
        raise Halt("duplicate-identity", "duplicate identity")
    body = bytearray()
    for identity, commitment, priority in ordered:
        body.extend(_lp(identity) + commitment + _i64(priority))
    return DOMAIN_CLOSED + _u32(len(ordered)) + bytes(body)


def decode_closed(buf: bytes) -> list[tuple[bytes, bytes, int]]:
    if not isinstance(buf, bytes) or not buf.startswith(DOMAIN_CLOSED):
        raise Halt("malformed-transcript", "bad domain")
    index = len(DOMAIN_CLOSED)
    count, index = _take_u32(buf, index)
    if count > MAX_ENTRIES:
        raise Halt("malformed-transcript", "count")
    parsed = []
    for _ in range(count):
        identity, index = _take_lp(buf, index, 128)
        commitment, index = _take(buf, index, 32)
        priority, index = _take_i64(buf, index)
        parsed.append((identity, commitment, priority))
    if index != len(buf):
        raise Halt("malformed-transcript", "trailing")
    for identity, _, _ in parsed:
        if _IDENTITY.fullmatch(identity) is None:
            raise Halt("noncanonical-identity", "identity")
    if len({item[0] for item in parsed}) != len(parsed):
        raise Halt("duplicate-identity", "duplicate identity")
    return parsed


def tie_digest(challenge: bytes, commitment: bytes) -> bytes:
    return _sha(DOMAIN_TIE + challenge + commitment)


def screen(extensions: object, enabled: object) -> None:
    if extensions is None:
        extensions = []
    if not isinstance(extensions, list) or len(extensions) > MAX_EXTENSIONS:
        raise Halt("malformed-transcript", "extensions")
    if not isinstance(enabled, (list, tuple, set, frozenset)):
        raise Halt("malformed-transcript", "handlers")
    enabled_set = set(enabled)
    for item in extensions:
        if not isinstance(item, dict):
            raise Halt("malformed-transcript", "extension")
        extension_id = item.get("id")
        version = item.get("version")
        critical = item.get("critical")
        payload = item.get("payload", b"")
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        if (
            not isinstance(extension_id, str)
            or _EXT_ID.fullmatch(extension_id) is None
            or isinstance(version, bool)
            or not isinstance(version, int)
            or not 1 <= version <= 0xFFFFFFFF
            or not isinstance(critical, bool)
            or not isinstance(payload, bytes)
            or len(payload) > MAX_EXTENSION_PAYLOAD
        ):
            raise Halt("malformed-transcript", "extension envelope")
        if critical and extension_id not in enabled_set:
            raise Halt("extension-critical-unknown", extension_id)
        if extension_id not in enabled_set:
            continue
        pattern = _HANDLERS.get(extension_id)
        if pattern is None or version != _PROFILES.get(extension_id):
            raise Halt("extension-critical-unknown", "handler")
        if pattern.fullmatch(payload) is None:
            raise Halt("extension-invalid", extension_id)


def evaluate(record: dict) -> dict:
    try:
        return {"ok": True, **_evaluate(record)}
    except Halt as exc:
        return {"ok": False, "code": exc.code, "message": exc.message}


def _evaluate(record: dict) -> dict:
    if not isinstance(record, dict):
        raise Halt("malformed-transcript", "record")
    version = record.get("canonicalisation_version", 1)
    if isinstance(version, bool) or version != 1:
        raise Halt("unsupported-version", "version")
    try:
        round_id = _token(record["round_id"], _IDENTITY, "malformed-transcript")
        parent = _hex32(record["parent_hash"], "malformed-transcript")
    except KeyError as exc:
        raise Halt("malformed-transcript", "missing") from exc
    policy = record.get("policy")
    if not isinstance(policy, dict) or not isinstance(policy.get("rules"), list):
        raise Halt("policy-invalid", "policy")
    policy_bytes = encode_policy(policy["revision"], policy["rules"], policy.get("fairness", ""))
    digest = _sha(policy_bytes)
    if "policy_digest" in record and _hex32(record["policy_digest"], "policy-stale") != digest:
        raise Halt("policy-stale", "digest")
    extensions = record.get("extensions") or []
    enabled = record.get("enabled_handlers") or []
    screen(extensions, enabled)
    entries = record.get("entries")
    if not isinstance(entries, list):
        raise Halt("malformed-transcript", "entries")
    if not entries:
        raise Halt("empty-closed-set", "empty")
    parsed = [_entry(entry, policy_bytes) for entry in entries]
    seen: dict[bytes, bytes] = {}
    for item in parsed:
        previous = seen.get(item["commitment"])
        if previous is not None and previous != item["semantic"]:
            raise Halt("commitment-collision", "alias")
        seen[item["commitment"]] = item["semantic"]
    _keturah(extensions, enabled, parsed)
    _fairness(record, policy_bytes, parsed)
    triples = [(item["identity"], item["commitment"], item["priority"]) for item in parsed]
    transcript = encode_closed(triples)
    digest_s = _sha(transcript)
    challenge = _sha(DOMAIN_CHALLENGE + _lp(round_id) + parent + digest + digest_s)
    for item in parsed:
        item["tie"] = tie_digest(challenge, item["commitment"])
    ranked = sorted(parsed, key=lambda item: (-item["priority"], item["tie"], item["identity"]))
    winner = ranked[0]
    winning = [item for item in ranked if item["priority"] == winner["priority"] and item["tie"] == winner["tie"]]
    if len(winning) != 1:
        raise Halt("tie-collision", "collision")
    rejections = []
    for item in sorted(ranked, key=lambda item: item["identity"]):
        if item["identity"] == winner["identity"]:
            continue
        code = "lower-priority" if item["priority"] < winner["priority"] else "higher-tie-digest"
        rejections.append({"identity": item["identity"].decode("ascii"), "code": code})
    return {
        "canonicalisation_version": 1,
        "round_id": round_id.decode("ascii"),
        "transcript_hex": transcript.hex(),
        "closed_set_digest_hex": digest_s.hex(),
        "challenge_hex": challenge.hex(),
        "policy_digest_hex": digest.hex(),
        "transcript_identity_order": [
            identity.decode("ascii") for identity, _, _ in sorted(triples, key=lambda item: item[0])
        ],
        "ranking": [_public(item) for item in ranked],
        "winner": _public(winner),
        "rejections": rejections,
        "audit": [
            {"identity": item["identity"].decode("ascii"), "admission_seq": item["admission_seq"]}
            for item in sorted(parsed, key=lambda item: item["identity"])
        ],
        "grinding_resistance": "unproven",
    }


def _entry(entry: dict, policy_bytes: bytes) -> dict:
    if not isinstance(entry, dict):
        raise Halt("malformed-transcript", "entry")
    try:
        identity = _token(entry["identity"], _IDENTITY, "noncanonical-identity")
        successor = _hex32(entry["successor_hex"], "noncanonical-proposal")
        content = _content(entry)
        semantic = encode_semantic(entry["semantic_ref"], entry["operation"], content, successor)
    except KeyError as exc:
        raise Halt("malformed-transcript", "missing entry field") from exc
    commitment = commitment_of(semantic)
    claimed = entry.get("claimed_commitment_hex")
    if claimed is not None and _hex32(claimed, "commitment-mismatch") != commitment:
        raise Halt("commitment-mismatch", "claimed")
    operation = operation_of(semantic)
    priority = _priority(policy_bytes, operation)
    if "asserted_priority" in entry:
        asserted = entry["asserted_priority"]
        if isinstance(asserted, bool) or asserted != priority:
            raise Halt("priority-untrusted", "asserted")
    sequence = entry.get("admission_seq")
    if sequence is not None and (
        isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1 or sequence > 2**64 - 1
    ):
        raise Halt("malformed-transcript", "sequence")
    return {
        "identity": identity,
        "commitment": commitment,
        "priority": priority,
        "semantic": semantic,
        "operation": operation,
        "admission_seq": sequence,
        "successor": successor,
    }


def _priority(policy_bytes: bytes, operation: bytes) -> int:
    if not policy_bytes.startswith(DOMAIN_POLICY):
        raise Halt("policy-invalid", "domain")
    index = len(DOMAIN_POLICY)
    _revision, index = _take_lp(policy_bytes, index, 128)
    count, index = _take_u32(policy_bytes, index)
    found = None
    for _ in range(count):
        name, index = _take_lp(policy_bytes, index, 128)
        priority, index = _take_i64(policy_bytes, index)
        if name == operation:
            found = priority
    if found is None:
        raise Halt("ineligible-operation", "operation")
    return found


def _fairness_limit(policy_bytes: bytes) -> int | None:
    index = len(DOMAIN_POLICY)
    _revision, index = _take_lp(policy_bytes, index, 128)
    count, index = _take_u32(policy_bytes, index)
    for _ in range(count):
        _name, index = _take_lp(policy_bytes, index, 128)
        _priority, index = _take_i64(policy_bytes, index)
    fair, index = _take_lp(policy_bytes, index, 64)
    if not fair:
        return None
    return int(fair.split(b":", 1)[1])


def _fairness(record: dict, policy_bytes: bytes, parsed: list[dict]) -> None:
    limit = _fairness_limit(policy_bytes)
    if limit is None:
        return
    prior = record.get("prior_wins")
    if not isinstance(prior, dict):
        raise Halt("policy-invalid", "prior wins")
    for item in parsed:
        name = item["identity"].decode("ascii")
        wins = prior.get(name, 0)
        if isinstance(wins, bool) or not isinstance(wins, int) or wins < 0:
            raise Halt("policy-invalid", "wins")
        if wins >= limit:
            raise Halt("fairness-violation", name)


def _keturah(extensions: list, enabled: list, parsed: list[dict]) -> None:
    if "org.gellsmore.keturah.capability" not in set(enabled):
        return
    payloads = []
    for item in extensions:
        if item.get("id") == "org.gellsmore.keturah.capability":
            payload = item.get("payload", b"")
            payloads.append(payload.encode("utf-8") if isinstance(payload, str) else payload)
    if not payloads:
        return
    named = payloads[0].split(b" capability:", 1)[1]
    for item in parsed:
        if named != item["operation"]:
            raise Halt("extension-invalid", "capability")


def _public(item: dict) -> dict:
    return {
        "identity": item["identity"].decode("ascii"),
        "priority": item["priority"],
        "tie_hex": item["tie"].hex(),
        "commitment_hex": item["commitment"].hex(),
        "successor_hex": item["successor"].hex(),
    }
