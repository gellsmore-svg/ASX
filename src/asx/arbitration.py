"""Deterministic arbitration.

Ranking inputs are the pinned policy, the canonical closed set, and the
derived challenge. Admission sequence, transport order, and extension
payloads are not ranking inputs.

The derived challenge is reproducible. It is not independent randomness
and it does not resist offline grinding of semantic content.
"""

from __future__ import annotations

from asx.canonical import (
    canonical_identity,
    canonical_round_id,
    closed_set_digest,
    decode_closed_set,
    derived_challenge,
    encode_closed_set,
    encode_semantic_proposal,
    parse_hex,
    parse_hex32,
    proposal_commitment,
    tie_digest,
)
from asx.errors import Rejection
from asx.extensions import keturah_operation_matches, screen_extensions
from asx.policy import build_policy, digest_of, fairness_limit, priority_for


def evaluate(record: dict) -> dict:
    """Return a JSON-ready decision or a halting rejection. No I/O."""
    try:
        return {"ok": True, **_evaluate(record)}
    except Rejection as exc:
        return {"ok": False, "code": exc.code, "message": exc.message}


def check_closed_set(transcript: bytes, authoritative: bytes) -> None:
    if closed_set_digest(transcript) != authoritative:
        raise Rejection("closed-set-mismatch", "local closed set does not match the authoritative digest")


def _evaluate(record: dict) -> dict:
    if not isinstance(record, dict):
        raise Rejection("malformed-transcript", "round record must be an object")
    version = record.get("canonicalisation_version", 1)
    if isinstance(version, bool) or version != 1:
        raise Rejection("unsupported-version", "only canonicalisation version 1 is defined")
    try:
        round_id = canonical_round_id(record["round_id"])
        parent = parse_hex32(record["parent_hash"])
    except KeyError as exc:
        raise Rejection("malformed-transcript", "round record is missing a field") from exc
    except Rejection:
        raise
    policy = record.get("policy")
    if not isinstance(policy, dict) or "revision" not in policy or "rules" not in policy:
        raise Rejection("policy-invalid", "pinned policy is missing")
    if not isinstance(policy["rules"], list):
        raise Rejection("policy-invalid", "priority rules must be a list")
    policy_bytes = build_policy(policy["revision"], policy["rules"], policy.get("fairness", ""))
    digest = digest_of(policy_bytes)
    if "policy_digest" in record and parse_hex32(record["policy_digest"], "policy-stale") != digest:
        raise Rejection("policy-stale", "pinned policy digest does not match the policy bytes")
    extensions = record.get("extensions") or []
    enabled = record.get("enabled_handlers") or []
    screen_extensions(extensions, enabled)
    entries = record.get("entries")
    if not isinstance(entries, list):
        raise Rejection("malformed-transcript", "entries must be a list")
    if not entries:
        raise Rejection("empty-closed-set", "the closed set has no eligible proposals")
    parsed = [_parse_entry(entry, policy_bytes) for entry in entries]
    _reject_commitment_aliases(parsed)
    _check_keturah(extensions, enabled, parsed)
    _check_fairness(record, policy_bytes, parsed)
    triples = [(item["identity"], item["commitment"], item["priority"]) for item in parsed]
    transcript = encode_closed_set(triples)
    # Decode the bytes we just encoded so a builder/decoder disagreement fails closed.
    if decode_closed_set(transcript) != sorted(triples, key=lambda item: item[0]):
        raise Rejection("malformed-transcript", "closed-set transcript did not round-trip")
    digest_s = closed_set_digest(transcript)
    challenge = derived_challenge(round_id, parent, digest, digest_s)
    ranked = []
    for item in parsed:
        item = dict(item)
        item["tie"] = tie_digest(challenge, item["commitment"])
        ranked.append(item)
    ranked.sort(key=lambda item: (-item["priority"], item["tie"], item["identity"]))
    winner = ranked[0]
    winning = [
        item
        for item in ranked
        if item["priority"] == winner["priority"] and item["tie"] == winner["tie"]
    ]
    if len(winning) != 1:
        raise Rejection("tie-collision", "equal tie digests; refusing to use arrival order")
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
        "ranking": [_public_rank(item) for item in ranked],
        "winner": _public_rank(winner),
        "rejections": rejections,
        "audit": [
            {"identity": item["identity"].decode("ascii"), "admission_seq": item["admission_seq"]}
            for item in sorted(parsed, key=lambda item: item["identity"])
        ],
        "grinding_resistance": "unproven",
    }


def _parse_entry(entry: dict, policy_bytes: bytes) -> dict:
    if not isinstance(entry, dict):
        raise Rejection("malformed-transcript", "entry must be an object")
    try:
        identity = canonical_identity(entry["identity"])
        successor = parse_hex32(entry["successor_hex"], "noncanonical-proposal")
        if "content_hex" in entry:
            content = parse_hex(entry["content_hex"], "noncanonical-proposal")
        elif isinstance(entry.get("content"), bytes):
            content = entry["content"]
        else:
            raise Rejection("noncanonical-proposal", "content is missing")
        semantic = encode_semantic_proposal(entry["semantic_ref"], entry["operation"], content, successor)
    except KeyError as exc:
        raise Rejection("malformed-transcript", "entry is missing a field") from exc
    commitment = proposal_commitment(semantic)
    claimed = entry.get("claimed_commitment_hex")
    if claimed is not None and parse_hex32(claimed, "commitment-mismatch") != commitment:
        raise Rejection("commitment-mismatch", "claimed proposal commitment does not match the semantic bytes")
    operation = semantic_operation(semantic)
    priority = priority_for(policy_bytes, operation)
    if "asserted_priority" in entry:
        asserted = entry["asserted_priority"]
        if isinstance(asserted, bool) or asserted != priority:
            raise Rejection("priority-untrusted", "asserted priority does not match the pinned policy")
    sequence = entry.get("admission_seq")
    if sequence is not None and (
        isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1 or sequence > 2**64 - 1
    ):
        raise Rejection("malformed-transcript", "admission sequence is not a valid audit integer")
    return {
        "identity": identity,
        "commitment": commitment,
        "priority": priority,
        "semantic": semantic,
        "operation": operation,
        "admission_seq": sequence,
        "successor": successor,
    }


def semantic_operation(semantic: bytes) -> bytes:
    """Read the operation field back from a version-1 semantic proposal."""
    from asx.canonical import DOMAIN_SEMANTIC, read_lp

    if not semantic.startswith(DOMAIN_SEMANTIC):
        raise Rejection("noncanonical-proposal", "semantic proposal is not version 1")
    index = len(DOMAIN_SEMANTIC)
    _ref, index = read_lp(semantic, index, 256)
    operation, _index = read_lp(semantic, index, 128)
    return operation


def _reject_commitment_aliases(parsed: list[dict]) -> None:
    seen: dict[bytes, bytes] = {}
    for item in parsed:
        previous = seen.get(item["commitment"])
        if previous is not None and previous != item["semantic"]:
            raise Rejection("commitment-collision", "different semantic bytes produced one commitment")
        seen[item["commitment"]] = item["semantic"]


def _check_keturah(extensions: list, enabled: list, parsed: list[dict]) -> None:
    if "org.gellsmore.keturah.capability" not in set(enabled):
        return
    payloads = []
    for item in extensions:
        if item.get("id") == "org.gellsmore.keturah.capability":
            payload = item.get("payload", b"")
            payloads.append(payload.encode("utf-8") if isinstance(payload, str) else payload)
    if not payloads:
        return
    for item in parsed:
        if not keturah_operation_matches(payloads[0], item["operation"]):
            raise Rejection("extension-invalid", "operation does not match the Keturah capability")


def _check_fairness(record: dict, policy_bytes: bytes, parsed: list[dict]) -> None:
    limit = fairness_limit(policy_bytes)
    if limit is None:
        return
    prior = record.get("prior_wins")
    if not isinstance(prior, dict):
        raise Rejection("policy-invalid", "max-wins requires an explicit prior-win map")
    for item in parsed:
        name = item["identity"].decode("ascii")
        wins = prior.get(name, 0)
        if isinstance(wins, bool) or not isinstance(wins, int) or wins < 0:
            raise Rejection("policy-invalid", "prior win count is not a non-negative integer")
        if wins >= limit:
            raise Rejection("fairness-violation", f"{name} is over the declared win cap")


def _public_rank(item: dict) -> dict[str, object]:
    return {
        "identity": item["identity"].decode("ascii"),
        "priority": item["priority"],
        "tie_hex": item["tie"].hex(),
        "commitment_hex": item["commitment"].hex(),
        "successor_hex": item["successor"].hex(),
    }
