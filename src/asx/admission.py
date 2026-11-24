"""Proposal admission.

Each governed identity has at most one eligible proposal in a round.
The first committed admission is authoritative. An identical retry returns
that receipt. A later distinct submission is rejected.

These ledgers assign sequence numbers for audit. Sequence numbers are not
ranking inputs. Neither class is a distributed linearizable sequencer:
the memory ledger dies with the process, and the file ledger is one node.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path

from asx.canonical import (
    canonical_identity,
    canonical_round_id,
    encode_admission,
    encode_semantic_proposal,
    proposal_commitment,
    submission_binding,
)
from asx.errors import Rejection
from asx.identity import IllustrativeAgentKeys, IllustrativeHmacKey


@dataclass(frozen=True)
class Submission:
    round_id: bytes
    identity: bytes
    semantic_ref: bytes
    operation: bytes
    content: bytes
    successor: bytes
    parent_hash: bytes
    policy_digest: bytes
    proof: bytes


@dataclass(frozen=True)
class AdmissionReceipt:
    sequence: int
    identity: bytes
    commitment: bytes
    semantic_ref: bytes
    operation: bytes
    content: bytes
    successor: bytes
    parent_hash: bytes
    policy_digest: bytes
    round_id: bytes
    payload: bytes
    signature: bytes

    def audit(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "identity": self.identity.decode("ascii"),
            "commitment_hex": self.commitment.hex(),
            "payload_hex": self.payload.hex(),
            "signature_hex": self.signature.hex(),
        }


def _prepare(sub: Submission) -> tuple[bytes, bytes, bytes]:
    round_id = canonical_round_id(sub.round_id)
    identity = canonical_identity(sub.identity)
    if len(sub.parent_hash) != 32 or len(sub.policy_digest) != 32:
        raise Rejection("malformed-transcript", "admission hash is not 32 bytes")
    semantic = encode_semantic_proposal(sub.semantic_ref, sub.operation, sub.content, sub.successor)
    commitment = proposal_commitment(semantic)
    binding = submission_binding(round_id, identity, commitment, sub.parent_hash, sub.policy_digest)
    return binding, commitment, semantic


class _AdmissionCore:
    def __init__(self, agents: IllustrativeAgentKeys, sequencer: IllustrativeHmacKey):
        self.agents = agents
        self.sequencer = sequencer
        self.available = True
        self._seq = 0
        self._closed: set[bytes] = set()
        self._by_identity: dict[tuple[bytes, bytes], AdmissionReceipt] = {}
        self.deferred: list[dict[str, str]] = []

    def close(self, round_id: bytes) -> None:
        self._closed.add(canonical_round_id(round_id))

    def admit(self, sub: Submission) -> AdmissionReceipt:
        if not self.available:
            raise Rejection("sequencer-unavailable", "admission sequencer is unavailable")
        binding, commitment, _semantic = _prepare(sub)
        round_id = canonical_round_id(sub.round_id)
        identity = canonical_identity(sub.identity)
        if round_id in self._closed:
            self.deferred.append(
                {
                    "round_id": round_id.decode("ascii"),
                    "identity": identity.decode("ascii"),
                    "code": "admission-closed",
                }
            )
            raise Rejection("admission-closed", "admission for this round is closed")
        if not self.agents.verify(identity, binding, sub.proof):
            raise Rejection("admission-unauthenticated", "identity proof did not verify")
        key = (round_id, identity)
        existing = self._by_identity.get(key)
        if existing is not None:
            same = (
                existing.commitment == commitment
                and existing.parent_hash == sub.parent_hash
                and existing.policy_digest == sub.policy_digest
            )
            if same:
                return existing
            raise Rejection("duplicate-submission", "this identity already has a different admission")
        self._seq += 1
        payload = encode_admission(round_id, identity, commitment, sub.parent_hash, sub.policy_digest, self._seq)
        receipt = AdmissionReceipt(
            sequence=self._seq,
            identity=identity,
            commitment=commitment,
            semantic_ref=sub.semantic_ref if isinstance(sub.semantic_ref, bytes) else sub.semantic_ref.encode("ascii"),
            operation=sub.operation if isinstance(sub.operation, bytes) else sub.operation.encode("ascii"),
            content=sub.content,
            successor=sub.successor,
            parent_hash=sub.parent_hash,
            policy_digest=sub.policy_digest,
            round_id=round_id,
            payload=payload,
            signature=self.sequencer.sign(payload),
        )
        self._by_identity[key] = receipt
        return receipt

    def receipts(self, round_id: bytes) -> list[AdmissionReceipt]:
        raw = canonical_round_id(round_id)
        found = [item for (item_round, _), item in self._by_identity.items() if item_round == raw]
        return sorted(found, key=lambda item: item.sequence)

    def verify_stored(self, receipt: AdmissionReceipt) -> None:
        if not self.sequencer.verify(receipt.payload, receipt.signature):
            raise Rejection("certificate-mismatch", "admission receipt signature did not verify")


class IllustrativeMemoryAdmission(_AdmissionCore):
    """In-process admission table. Lost on restart. Not linearizable across processes."""

    def __init__(self, agents: IllustrativeAgentKeys, sequencer: IllustrativeHmacKey):
        super().__init__(agents, sequencer)
        self._lock = threading.Lock()

    def close(self, round_id: bytes) -> None:
        with self._lock:
            super().close(round_id)

    def admit(self, sub: Submission) -> AdmissionReceipt:
        with self._lock:
            return super().admit(sub)

    def receipts(self, round_id: bytes) -> list[AdmissionReceipt]:
        with self._lock:
            return super().receipts(round_id)


class IllustrativeFileAdmission(_AdmissionCore):
    """One-node JSON ledger using atomic replace.

    A second process writing the same file is not supported. Restart in the
    same process lineage reloads committed receipts. This is not a distributed
    sequencer and it is not safe under concurrent processes.
    """

    def __init__(self, path: Path, agents: IllustrativeAgentKeys, sequencer: IllustrativeHmacKey):
        super().__init__(agents, sequencer)
        self.path = Path(path)
        self._lock = threading.Lock()
        if self.path.exists():
            self._load()

    def close(self, round_id: bytes) -> None:
        with self._lock:
            super().close(round_id)
            self._save()

    def admit(self, sub: Submission) -> AdmissionReceipt:
        with self._lock:
            try:
                receipt = super().admit(sub)
            except Rejection:
                self._save()
                raise
            self._save()
            return receipt

    def _save(self) -> None:
        payload = {
            "next_seq": self._seq,
            "closed": sorted(item.decode("ascii") for item in self._closed),
            "receipts": [_dump_receipt(item) for item in self._by_identity.values()],
            "deferred": list(self.deferred),
        }
        _atomic_json(self.path, payload)

    def _load(self) -> None:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self._seq = int(data["next_seq"])
        self._closed = {item.encode("ascii") for item in data["closed"]}
        self.deferred = list(data.get("deferred", []))
        for item in data["receipts"]:
            receipt = _load_receipt(item)
            self._by_identity[(receipt.round_id, receipt.identity)] = receipt


def _dump_receipt(receipt: AdmissionReceipt) -> dict[str, object]:
    return {
        "sequence": receipt.sequence,
        "identity": receipt.identity.decode("ascii"),
        "commitment": receipt.commitment.hex(),
        "semantic_ref": receipt.semantic_ref.decode("ascii"),
        "operation": receipt.operation.decode("ascii"),
        "content": receipt.content.hex(),
        "successor": receipt.successor.hex(),
        "parent_hash": receipt.parent_hash.hex(),
        "policy_digest": receipt.policy_digest.hex(),
        "round_id": receipt.round_id.decode("ascii"),
        "payload": receipt.payload.hex(),
        "signature": receipt.signature.hex(),
    }


def _load_receipt(item: dict[str, object]) -> AdmissionReceipt:
    return AdmissionReceipt(
        sequence=int(item["sequence"]),
        identity=str(item["identity"]).encode("ascii"),
        commitment=bytes.fromhex(str(item["commitment"])),
        semantic_ref=str(item["semantic_ref"]).encode("ascii"),
        operation=str(item["operation"]).encode("ascii"),
        content=bytes.fromhex(str(item["content"])),
        successor=bytes.fromhex(str(item["successor"])),
        parent_hash=bytes.fromhex(str(item["parent_hash"])),
        policy_digest=bytes.fromhex(str(item["policy_digest"])),
        round_id=str(item["round_id"]).encode("ascii"),
        payload=bytes.fromhex(str(item["payload"])),
        signature=bytes.fromhex(str(item["signature"])),
    )


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
